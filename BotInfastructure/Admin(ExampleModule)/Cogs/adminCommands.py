import discord
from discord.ext import commands
from discord import app_commands

DEV_GUILD_ID = 1368691043066707968
DEV_USER_ID = 722177380747051119
ADMIN_ROLE_ID = 1369038489210851448

class adminCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="shutdown", description="Shuts the bot down (Dev Only)")
    @app_commands.guilds(discord.Object(id=DEV_GUILD_ID))
    @app_commands.default_permissions(administrator=True)
    async def shutDown(self, interaction: discord.Interaction):
        await interaction.response.send_message("Bot shutting down", ephemeral=True)
        await self.bot.close()

    @app_commands.command(name="list-commands", description="Lists currently loaded commands (Dev Only)")
    @app_commands.guilds(discord.Object(id=DEV_GUILD_ID))
    @app_commands.default_permissions(administrator=True)
    async def listCommands(self, interaction: discord.Interaction):
        cmds = self.bot.tree.get_commands(guild=discord.Object(id=DEV_GUILD_ID))
        outputText = "=== Loaded Slash Commands ===\n"

        for cmd in cmds:
            outputText += f"- /{cmd.name}: {cmd.description or 'No description'}\n"

        await interaction.response.send_message(outputText, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(adminCommands(bot))