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

async def setup(bot: commands.Bot):
    await bot.add_cog(testCommands(bot))
