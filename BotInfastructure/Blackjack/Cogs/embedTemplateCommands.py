import os
devServerID = int(os.getenv("DEV_SERVER_ID"))

import discord
from discord.ext import commands
from discord import app_commands

from .._InnerModules.embedTemplates import EmbedTemplates

class embedTemplateCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="example-embed", description="Displays a basic example embed of the game display")
    @app_commands.guilds(discord.Object(id=devServerID))
    async def exampleEmbed(self, interaction: discord.Interaction):
        embed = EmbedTemplates().embed1()
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(embedTemplateCommands(bot))
