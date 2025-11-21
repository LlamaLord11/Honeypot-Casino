import discord
from GlobalModules.CardDeck import *
from PIL import Image
from io import BytesIO

class EmbedTemplates:
    def __init__(self):
        print("placeholder")

        self.tableMin = 0
        self.dealerHandField = "{Card Value} of {Suit} | Total: {Optimal Hand Value}"
        self.currentActivePlayer = "{Current Player}"
        self.latestAction = "{Placeholder for latest action at the table}"

    def embed1(self) -> discord.Embed:

        embed = discord.Embed(
        title="Blackjack Table {TABLE_ID}",
        description=(
            "Welcome to Honeypot Casino's Blackjack Table.\n"
            "This is a display template for demonstration purposes only.\n\n"
            "💵 Minimum Bet: {MIN_BET}\n\n"
            "🃏 Dealer Hand: {DEALER_HAND}\n\n"
            "🎯 Current Player Turn: {CURRENT_PLAYER}\n"
            "💥 Latest Player Action: {LATEST_ACTION}\n\n"
            "========================================="
        ),
        color=0xFFAE42
        )

        embed.set_thumbnail(url="https://media.discordapp.net/attachments/1369086652965978314/1369137718717845637/casino-chip-icon-gambling-vector.png?ex=691d2a5d&is=691bd8dd&hm=b37981c1d60a6c6d1328d7ea7eb8f32c876c64e448781fe0cce1f8ac1b074aa6&=&format=webp&quality=lossless")

        # --- PLAYER FIELD TEMPLATE ---
        # Repeat this block for each player in the template
        embed.add_field(
            name="Player {PLAYER_NUMBER}: {PLAYER_DISPLAY_NAME} | Standing Bet: {PLAYER_BET}",
            value=(
                "Current Hand: {PLAYER_HAND}\n"
                "Result: {PLAYER_RESULT}"
            ),
            inline=False
        )

        # Example of a second field (optional)
        embed.add_field(
            name="Player {PLAYER_NUMBER_2}: {PLAYER_DISPLAY_NAME_2} | Standing Bet: {PLAYER_BET_2}",
            value=(
                "Current Hand: {PLAYER_HAND_2}\n"
                "Result: {PLAYER_RESULT_2}"
            ),
            inline=False
        )

        return embed
    
def getCardImageHelper(cardName: str):
    fileExists, output = getCardPath(cardName)

    if fileExists:
        return True, discord.File(output)
    else:
        return False, output

def cardImageStitcher(in1: discord.File, in2:discord.File, offset):
    image1 = Image.open(in1.fp)
    image2 = Image.open(in2.fp)

    image1.paste(image2, (offset, 0))

    buffer = BytesIO()
    image1.save(buffer, format="PNG")
    buffer.seek(0)

    return discord.File(buffer, filename="combined.png")