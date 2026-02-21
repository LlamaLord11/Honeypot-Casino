"""
finance.py — Casino bot finance module
Handles all balance operations via a single asyncio queue worker to prevent race conditions.

Database schema:
    accounts(
        discord_id   INTEGER PRIMARY KEY,
        username     TEXT NOT NULL DEFAULT 'Unknown',
        balance      REAL NOT NULL DEFAULT 0.0,
        promo        REAL NOT NULL DEFAULT 0.0,
        reserved_real  REAL NOT NULL DEFAULT 0.0,
        reserved_promo REAL NOT NULL DEFAULT 0.0
    )

The HOUSE_ID constant is the discord ID of the admin/house account.
All forfeited (lost) funds are transferred there for accounting purposes.
"""

from __future__ import annotations

import asyncio
import aiosqlite
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Coroutine, Protocol


class DiscordClient(Protocol):
    """Structural interface for the discord.Client we need — avoids importing discord."""
    async def fetch_user(self, user_id: int) -> Any: ...


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HOUSE_ID: int = 0  # Replace with your actual house/admin Discord user ID
DB_PATH: str = "casino.db"


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

class Status(Enum):
    OK             = auto()
    ACCOUNT_EXISTS = auto()
    NO_ACCOUNT     = auto()
    INSUFFICIENT   = auto()
    NOT_RESERVED   = auto()
    ERROR          = auto()


@dataclass(frozen=True)
class FinanceResult:
    status: Status
    message: str
    username: str | None = None
    balance: float | None = None
    promo: float | None = None
    reserved_real: float | None = None
    reserved_promo: float | None = None

    @property
    def ok(self) -> bool:
        return self.status == Status.OK

    def __repr__(self) -> str:
        return (
            f"FinanceResult(status={self.status.name}, message={self.message!r}, "
            f"username={self.username!r}, balance={self.balance}, promo={self.promo})"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _snapshot(row: aiosqlite.Row) -> FinanceResult:
    """Build an OK result from a DB row."""
    return FinanceResult(
        status=Status.OK,
        message="Success.",
        username=row["username"],
        balance=row["balance"],
        promo=row["promo"],
        reserved_real=row["reserved_real"],
        reserved_promo=row["reserved_promo"],
    )


# ---------------------------------------------------------------------------
# Finance manager
# ---------------------------------------------------------------------------

class FinanceManager:
    """
    All public methods enqueue a coroutine onto a single worker queue.
    This guarantees that every read-modify-write cycle is serialized,
    eliminating race conditions without needing explicit locks.

    Usage:
        fm = FinanceManager()
        await fm.start()
        ...
        await fm.stop()

    Or use it as an async context manager:
        async with FinanceManager() as fm:
            ...
    """

    def __init__(self, db_path: str = DB_PATH, house_id: int = HOUSE_ID) -> None:
        self._db_path = db_path
        self._house_id = house_id
        self._queue: asyncio.Queue[tuple[Callable, asyncio.Future]] = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None
        self._db: aiosqlite.Connection | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Open the database, create tables, and start the worker."""
        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA foreign_keys=ON")
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                discord_id     INTEGER PRIMARY KEY,
                username       TEXT    NOT NULL DEFAULT 'Unknown',
                balance        REAL    NOT NULL DEFAULT 0.0,
                promo          REAL    NOT NULL DEFAULT 0.0,
                reserved_real  REAL    NOT NULL DEFAULT 0.0,
                reserved_promo REAL    NOT NULL DEFAULT 0.0
            )
        """)
        # Migration: add username column if this is an existing database that predates it
        try:
            await self._db.execute("ALTER TABLE accounts ADD COLUMN username TEXT NOT NULL DEFAULT 'Unknown'")
            await self._db.commit()
        except Exception:
            pass  # Column already exists — expected on all runs after the first
        self._worker_task = asyncio.create_task(self._worker())

    async def stop(self) -> None:
        """Drain the queue, stop the worker, and close the database."""
        if self._queue:
            await self._queue.join()
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        if self._db:
            await self._db.close()

    async def __aenter__(self) -> "FinanceManager":
        await self.start()
        return self

    async def __aexit__(self, *_) -> None:
        await self.stop()

    # ------------------------------------------------------------------
    # Internal worker
    # ------------------------------------------------------------------

    async def _worker(self) -> None:
        while True:
            coro_fn, future = await self._queue.get()
            try:
                result = await coro_fn()
                if not future.done():
                    future.set_result(result)
            except Exception as exc:
                if not future.done():
                    future.set_exception(exc)
            finally:
                self._queue.task_done()

    async def _enqueue(self, coro_fn: Callable[[], Coroutine[Any, Any, FinanceResult]]) -> FinanceResult:
        """Put a coroutine factory on the queue and wait for its result."""
        future: asyncio.Future[FinanceResult] = asyncio.get_event_loop().create_future()
        await self._queue.put((coro_fn, future))
        return await future

    # ------------------------------------------------------------------
    # Internal DB helpers (run only inside the worker)
    # ------------------------------------------------------------------

    async def _fetch(self, discord_id: int) -> aiosqlite.Row | None:
        async with self._db.execute(
            "SELECT * FROM accounts WHERE discord_id = ?", (discord_id,)
        ) as cursor:
            return await cursor.fetchone()

    async def _require(self, discord_id: int) -> tuple[aiosqlite.Row | None, FinanceResult | None]:
        """Return (row, None) if account exists, (None, error_result) otherwise."""
        row = await self._fetch(discord_id)
        if row is None:
            return None, FinanceResult(
                status=Status.NO_ACCOUNT,
                message=f"No account found for user {discord_id}.",
            )
        return row, None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def create_account(
        self,
        discord_id: int,
        username: str,
        starting_balance: float = 0.0,
        starting_promo: float = 0.0,
    ) -> FinanceResult:
        """
        Explicitly create an account for a Discord user.
        Returns ACCOUNT_EXISTS if the account already exists.
        """
        async def _op() -> FinanceResult:
            existing = await self._fetch(discord_id)
            if existing is not None:
                return FinanceResult(
                    status=Status.ACCOUNT_EXISTS,
                    message=f"Account for {discord_id} already exists.",
                    username=existing["username"],
                    balance=existing["balance"],
                    promo=existing["promo"],
                    reserved_real=existing["reserved_real"],
                    reserved_promo=existing["reserved_promo"],
                )
            await self._db.execute(
                "INSERT INTO accounts (discord_id, username, balance, promo) VALUES (?, ?, ?, ?)",
                (discord_id, username, starting_balance, starting_promo),
            )
            # Ensure the house account exists with the ADMIN username
            await self._db.execute(
                "INSERT OR IGNORE INTO accounts (discord_id, username) VALUES (?, 'ADMIN')",
                (self._house_id,),
            )
            await self._db.commit()
            row = await self._fetch(discord_id)
            return _snapshot(row)

        return await self._enqueue(_op)

    async def get_balance(self, discord_id: int) -> FinanceResult:
        """Return current balances for a user."""
        async def _op() -> FinanceResult:
            row, err = await self._require(discord_id)
            if err:
                return err
            return _snapshot(row)

        return await self._enqueue(_op)

    async def deposit(self, discord_id: int, amount: float) -> FinanceResult:
        """Add funds to a user's main balance."""
        if amount <= 0:
            return FinanceResult(status=Status.ERROR, message="Deposit amount must be positive.")

        async def _op() -> FinanceResult:
            row, err = await self._require(discord_id)
            if err:
                return err
            new_balance = row["balance"] + amount
            await self._db.execute(
                "UPDATE accounts SET balance = ? WHERE discord_id = ?",
                (new_balance, discord_id),
            )
            await self._db.commit()
            row = await self._fetch(discord_id)
            return _snapshot(row)

        return await self._enqueue(_op)

    async def deposit_promo(self, discord_id: int, amount: float) -> FinanceResult:
        """Add funds to a user's promotional balance."""
        if amount <= 0:
            return FinanceResult(status=Status.ERROR, message="Deposit amount must be positive.")

        async def _op() -> FinanceResult:
            row, err = await self._require(discord_id)
            if err:
                return err
            new_promo = row["promo"] + amount
            await self._db.execute(
                "UPDATE accounts SET promo = ? WHERE discord_id = ?",
                (new_promo, discord_id),
            )
            await self._db.commit()
            row = await self._fetch(discord_id)
            return _snapshot(row)

        return await self._enqueue(_op)

    async def reserve(self, discord_id: int, amount: float) -> FinanceResult:
        """
        Reserve `amount` for an active bet.
        Draws from promo balance first, then real balance.
        Reserved amounts are tracked separately so recovery is precise.

        Returns INSUFFICIENT if the user cannot cover the full bet.
        """
        if amount <= 0:
            return FinanceResult(status=Status.ERROR, message="Reserve amount must be positive.")

        async def _op() -> FinanceResult:
            row, err = await self._require(discord_id)
            if err:
                return err

            total_available = row["balance"] + row["promo"]
            if total_available < amount:
                return FinanceResult(
                    status=Status.INSUFFICIENT,
                    message=(
                        f"Insufficient funds. Available: {total_available:.2f} "
                        f"(balance={row['balance']:.2f}, promo={row['promo']:.2f}), "
                        f"required: {amount:.2f}."
                    ),
                    balance=row["balance"],
                    promo=row["promo"],
                    reserved_real=row["reserved_real"],
                    reserved_promo=row["reserved_promo"],
                )

            # Draw from promo first
            promo_used = min(row["promo"], amount)
            real_used = amount - promo_used

            new_promo = row["promo"] - promo_used
            new_balance = row["balance"] - real_used
            new_reserved_promo = row["reserved_promo"] + promo_used
            new_reserved_real = row["reserved_real"] + real_used

            await self._db.execute(
                """UPDATE accounts
                   SET balance = ?, promo = ?, reserved_real = ?, reserved_promo = ?
                   WHERE discord_id = ?""",
                (new_balance, new_promo, new_reserved_real, new_reserved_promo, discord_id),
            )
            await self._db.commit()
            row = await self._fetch(discord_id)
            return _snapshot(row)

        return await self._enqueue(_op)

    async def resolve_win(
        self,
        discord_id: int,
        reserved_amount: float,
        payout: float,
    ) -> FinanceResult:
        """
        Resolve a won bet.

        `reserved_amount` — the original bet size (used to locate the reserved funds).
        `payout`          — total funds to return to the player (including original stake).

        Resolution rules:
          1. The reserved promo portion is restored to promo balance.
          2. Anything remaining from payout beyond the restored promo goes to real balance.

        Example: bet=80 (50 promo + 30 real), 2x payout=160.
          - Restore 50 to promo  → promo = 50
          - Remaining 110 → real balance
        """
        if reserved_amount <= 0 or payout < 0:
            return FinanceResult(status=Status.ERROR, message="Invalid reserved_amount or payout.")

        async def _op() -> FinanceResult:
            row, err = await self._require(discord_id)
            if err:
                return err

            # Determine how much promo and real were actually in this reservation.
            # We assume reservations were added proportionally; for a single-bet
            # bot this is straightforward — the most recently reserved split.
            # Because we track totals, we need the caller to pass the split or we
            # derive it. For simplicity and correctness we reconstruct from stored
            # totals assuming this reservation consumed reserved_promo first.
            # For multi-game support, callers should use reserve_split_resolve below.
            promo_in_reserve = min(row["reserved_promo"], reserved_amount)
            real_in_reserve = reserved_amount - promo_in_reserve

            if row["reserved_real"] < real_in_reserve or row["reserved_promo"] < promo_in_reserve:
                return FinanceResult(
                    status=Status.NOT_RESERVED,
                    message=(
                        f"Reserved funds mismatch. "
                        f"Stored reserved_real={row['reserved_real']:.2f}, "
                        f"reserved_promo={row['reserved_promo']:.2f}, "
                        f"expected real={real_in_reserve:.2f}, promo={promo_in_reserve:.2f}."
                    ),
                )

            # Refill promo to its pre-bet level, rest goes to balance
            new_promo = row["promo"] + promo_in_reserve
            winnings_for_balance = payout - promo_in_reserve
            new_balance = row["balance"] + winnings_for_balance

            new_reserved_real = row["reserved_real"] - real_in_reserve
            new_reserved_promo = row["reserved_promo"] - promo_in_reserve

            await self._db.execute(
                """UPDATE accounts
                   SET balance = ?, promo = ?, reserved_real = ?, reserved_promo = ?
                   WHERE discord_id = ?""",
                (new_balance, new_promo, new_reserved_real, new_reserved_promo, discord_id),
            )
            await self._db.commit()
            row = await self._fetch(discord_id)
            return _snapshot(row)

        return await self._enqueue(_op)

    async def resolve_loss(
        self,
        discord_id: int,
        reserved_amount: float,
    ) -> FinanceResult:
        """
        Resolve a lost bet.
        Removes the reserved funds entirely and transfers them to the house account.
        """
        if reserved_amount <= 0:
            return FinanceResult(status=Status.ERROR, message="Invalid reserved_amount.")

        async def _op() -> FinanceResult:
            row, err = await self._require(discord_id)
            if err:
                return err

            promo_in_reserve = min(row["reserved_promo"], reserved_amount)
            real_in_reserve = reserved_amount - promo_in_reserve

            if row["reserved_real"] < real_in_reserve or row["reserved_promo"] < promo_in_reserve:
                return FinanceResult(
                    status=Status.NOT_RESERVED,
                    message=(
                        f"Reserved funds mismatch. "
                        f"Stored reserved_real={row['reserved_real']:.2f}, "
                        f"reserved_promo={row['reserved_promo']:.2f}."
                    ),
                )

            new_reserved_real = row["reserved_real"] - real_in_reserve
            new_reserved_promo = row["reserved_promo"] - promo_in_reserve

            # Forfeit: deduct from user
            await self._db.execute(
                """UPDATE accounts
                   SET reserved_real = ?, reserved_promo = ?
                   WHERE discord_id = ?""",
                (new_reserved_real, new_reserved_promo, discord_id),
            )

            # Transfer to house (real value of the loss — promo is just zeroed out)
            house_row = await self._fetch(self._house_id)
            if house_row is None:
                await self._db.execute(
                    "INSERT OR IGNORE INTO accounts (discord_id) VALUES (?)",
                    (self._house_id,),
                )
                house_balance = 0.0
            else:
                house_balance = house_row["balance"]

            await self._db.execute(
                "UPDATE accounts SET balance = ? WHERE discord_id = ?",
                (house_balance + real_in_reserve, self._house_id),
            )
            await self._db.commit()
            row = await self._fetch(discord_id)
            return _snapshot(row)

        return await self._enqueue(_op)

    async def recover_reservations(self) -> list[tuple[int, float, float]]:
        """
        Called on bot startup to return all outstanding reserved funds to their owners.
        Returns a list of (discord_id, returned_real, returned_promo) for each affected user
        so the bot can notify them.

        This should be called before start() hands off to the worker, or immediately after,
        before any user commands are processed.
        """
        async def _op() -> FinanceResult:
            async with self._db.execute(
                "SELECT * FROM accounts WHERE reserved_real > 0 OR reserved_promo > 0"
            ) as cursor:
                rows = await cursor.fetchall()

            recovered = []
            for row in rows:
                if row["discord_id"] == self._house_id:
                    continue
                ret_real = row["reserved_real"]
                ret_promo = row["reserved_promo"]
                new_balance = row["balance"] + ret_real
                new_promo = row["promo"] + ret_promo
                await self._db.execute(
                    """UPDATE accounts
                       SET balance = ?, promo = ?, reserved_real = 0, reserved_promo = 0
                       WHERE discord_id = ?""",
                    (new_balance, new_promo, row["discord_id"]),
                )
                recovered.append((row["discord_id"], ret_real, ret_promo))

            await self._db.commit()
            # Piggyback the list out via a custom result — the worker still needs
            # a FinanceResult return type, so we stash the list in message as a signal.
            return FinanceResult(
                status=Status.OK,
                message="__recovery__",
                # Abuse balance field temporarily to count rows; caller reads from _recovery_data
                balance=float(len(recovered)),
            ), recovered

        # Recovery is special — bypass the normal enqueue so we can return raw data.
        future: asyncio.Future = asyncio.get_event_loop().create_future()

        async def _wrapped():
            result, data = await _op()
            future._recovery_data = data
            return result

        await self._queue.put((_wrapped, future))
        await future
        return getattr(future, "_recovery_data", [])

    async def update_all_usernames(self, client: DiscordClient) -> dict[int, str]:
        """
        Loop through every non-house account in the database and update the stored
        username to the current Discord display name.

        Requires a discord.Client (or Bot) instance to resolve user IDs.
        Returns a dict of {discord_id: new_username} for every account that was updated.

        Intended to be called from an admin command or on a scheduled basis.
        Note: this method fetches users from Discord's API one at a time — for ~1k users
        this is fine, but be mindful of rate limits if you ever scale significantly.
        """
        async def _op() -> FinanceResult:
            async with self._db.execute(
                "SELECT discord_id, username FROM accounts WHERE discord_id != ?",
                (self._house_id,),
            ) as cursor:
                rows = await cursor.fetchall()

            updated = {}
            for row in rows:
                try:
                    user = await client.fetch_user(row["discord_id"])
                    new_name = user.display_name
                except Exception:
                    # User may have deleted their account or be otherwise unreachable
                    continue

                if new_name != row["username"]:
                    await self._db.execute(
                        "UPDATE accounts SET username = ? WHERE discord_id = ?",
                        (new_name, row["discord_id"]),
                    )
                    updated[row["discord_id"]] = new_name

            if updated:
                await self._db.commit()

            # Stash updated dict for retrieval after the future resolves
            return FinanceResult(
                status=Status.OK,
                message="__username_update__",
                balance=float(len(updated)),
            ), updated

        future: asyncio.Future = asyncio.get_event_loop().create_future()

        async def _wrapped():
            result, data = await _op()
            future._update_data = data
            return result

        await self._queue.put((_wrapped, future))
        await future
        return getattr(future, "_update_data", {})

    async def admin_set_balance(
        self,
        discord_id: int,
        balance: float | None = None,
        promo: float | None = None,
    ) -> FinanceResult:
        """
        Directly set a user's balance and/or promo balance.
        Intended for admin commands only — bypasses normal validation.
        """
        async def _op() -> FinanceResult:
            row, err = await self._require(discord_id)
            if err:
                return err
            new_balance = balance if balance is not None else row["balance"]
            new_promo = promo if promo is not None else row["promo"]
            await self._db.execute(
                "UPDATE accounts SET balance = ?, promo = ? WHERE discord_id = ?",
                (new_balance, new_promo, discord_id),
            )
            await self._db.commit()
            row = await self._fetch(discord_id)
            return _snapshot(row)

        return await self._enqueue(_op)