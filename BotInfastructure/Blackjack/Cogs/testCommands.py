import os
devServerID = int(os.getenv("DEV_SERVER_ID"))

import discord
from discord.ext import commands
from discord import app_commands

from BotInfastructure.Blackjack._InnerModules import *
from GlobalModules.CardDeck import *

class testCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="example-embed", description="Displays a basic example embed of the game display")
    @app_commands.guilds(discord.Object(id=devServerID))
    async def exampleEmbed(self, interaction: discord.Interaction):
        embed = EmbedTemplates().embed1()
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="get-card-image", description="Returns the appropriate card image based on input code")
    @app_commands.guilds(discord.Object(id=devServerID))
    @app_commands.describe(file_code="Name of the Card (suit) (value: 1-10/King/Queen/Jack)")
    async def getCardImage(self, interaction: discord.Interaction, file_code: str):
        fileExists, output = getCardImageHelper(file_code)
        if fileExists:
            await interaction.response.send_message(file=output)
        else:
            await interaction.response.send_message(output)

    @app_commands.command(name="card-hand", description="Returns the stitched image of 2 cards")
    @app_commands.guilds(discord.Object(id=devServerID))
    @app_commands.describe(
        file_code1="Name of the first Card (suit) (value: 1-10/King/Queen/Jack)",
        file_code2="Name of the second Card (suit) (value: 1-10/King/Queen/Jack)",
        rgb11="Red value of color 1",
        rgb12="Green value of color 1",
        rgb13="Blue value of color 1",
        rgb21="Red value of color 2",
        rgb22="Green value of color 2",
        rgb23="Blue value of color 2"
    )
    async def cardHandStitcher(self, interaction: discord.Interaction, file_code1: str, file_code2: str, rgb11: int, rgb12: int, rgb13: int, rgb21:int, rgb22: int, rgb23: int):
        fileExists1, output1 = getCardImageHelper(file_code1)
        fileExists2, output2 = getCardImageHelper(file_code2)
        if fileExists1 or fileExists2:
            await interaction.response.send_message(file=cardImageStitcher(output1, output2, 60,(rgb11,rgb12,rgb13,255),(rgb21,rgb22,rgb23,255)))
        else:
            await interaction.response.send_message("Invalid file name input")

async def setup(bot: commands.Bot):
    await bot.add_cog(testCommands(bot))
