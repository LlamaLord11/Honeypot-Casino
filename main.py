import sys, os

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from GlobalModules.FinanceModule import *

sys.dont_write_bytecode = True
load_dotenv()

CLIENT_TOKEN = os.getenv("BOT_TOKEN")
DEV_SERVER_ID = discord.Object(id=int(os.getenv("DEV_SERVER_ID")))
HOUSE_ID = int(os.getenv("HOUSE_ID"))  # Add this to your .env


class CasinoBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="/", intents=discord.Intents.all())
        self.fm: FinanceManager = None

    async def setup_hook(self):
        # Start finance manager
        databasePath = os.path.join(os.path.dirname(__file__), "Database", "casino.db")
        self.fm = FinanceManager(db_path=databasePath, house_id=HOUSE_ID)
        await self.fm.start()

        # Recover any reservations left over from a crash
        recovered = await self.fm.recover_reservations()
        for discord_id, ret_real, ret_promo in recovered:
            try:
                user = await self.fetch_user(discord_id)
                await user.send(
                    f"Honeypot Casino restarted while you had an active bet."
                    f"Returned to your account: **${ret_real:.2f}** normal balance, **${ret_promo:.2f}** promo balance."
                )
            except Exception as e:
                print(f"Could not notify user {discord_id} of recovery: {e}")

        # Load cogs
        await self.cogLoader()

        # Sync commands to dev server
        print("Syncing commands...")
        try:
            synced = await self.tree.sync(guild=DEV_SERVER_ID)
            guild = self.get_guild(DEV_SERVER_ID.id) or await self.fetch_guild(DEV_SERVER_ID.id)
            print(f"Synced {len(synced)} commands to {guild.name} ({DEV_SERVER_ID.id})")
            print("Synced: " + " ".join(f"/{cmd.name}" for cmd in synced))
        except Exception as e:
            print(f"Sync error: {e}")

    async def close(self):
        if self.fm:
            await self.fm.stop()
        await super().close()

    async def on_ready(self):
        print(f"Logged in as {self.user}")

    async def cogLoader(self):
        infastructurePath = os.path.join(os.path.dirname(__file__), "BotInfastructure")

        for moduleName in os.listdir(infastructurePath):

            innerModuleName = os.path.join(infastructurePath, moduleName)

            for innerFolderName in os.listdir(innerModuleName):

                if not innerFolderName.startswith('_'):

                    innerFilePath = os.path.join(innerModuleName, "Cogs")

                    if not os.path.isdir(innerFilePath):
                        continue

                    for innerFileName in os.listdir(innerFilePath):

                        if not innerFileName.endswith(".py") or innerFileName == "__init__.py":
                            continue

                        cogName = f"BotInfastructure.{moduleName}.{innerFolderName}.{innerFileName[:-3]}"

                        try:
                            await self.load_extension(cogName)
                            print(f"-> Loaded Cog: {innerFileName[:-3]}")
                        except Exception as e:
                            print(f"-> Failed to load Cog {cogName}\n{e}")


bot = CasinoBot()
bot.run(CLIENT_TOKEN)