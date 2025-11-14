import discord
from discord.ext import commands
from discord import app_commands

DEV_GUILD_ID = 1368691043066707968
DEV_USER_ID = 722177380747051119
ADMIN_ROLE_ID = 1369038489210851448

class adminCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


    # Makes the cog acessible to only people with admin role
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        user = interaction.guild.get_member(interaction.user.id)
        userRoles = user.roles
        if not any(role.id == ADMIN_ROLE_ID for role in userRoles):
            print(f"non admin tried and failed to acess admin commands")
            await interaction.response.send_message("Hey loser, you cant do that. Hence the big bold (Dev Only) description", ephemeral=True)
            return False
        return True

    @app_commands.command(name="shutdown", description="Shuts the bot down (Dev Only)")
    @app_commands.guilds(discord.Object(id=DEV_GUILD_ID))
    @app_commands.default_permissions(administrator=True)
    async def shutOff(self, interaction: discord.Interaction):
        await interaction.response.send_message("Bot shutting down", ephemeral=True)
        await self.bot.close()

    @app_commands.command(name="list-commands", description="Lists currently loaded commands (Dev Only)")
    @app_commands.guilds(discord.Object(id=DEV_GUILD_ID))
    @app_commands.default_permissions(administrator=True)
    async def showLoadedCommands(self, interaction: discord.Interaction):
        cmds = self.bot.tree.get_commands(guild=discord.Object(id=DEV_GUILD_ID))
        outputText = "=== Loaded Slash Commands ===\n"

        for cmd in cmds:
            outputText += f"- /{cmd.name}: {cmd.description or 'No description'}\n"

        await interaction.response.send_message(outputText, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(adminCommands(bot))