import sys, os


import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

sys.dont_write_bytecode = True

# Dev server ID: 1368691043066707968

load_dotenv()

clientToken = os.getenv("BOT_TOKEN")

bot = commands.Bot(command_prefix='/', intents=discord.Intents.all())

devServerID = discord.Object(id=1368691043066707968)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    try:
        await cogLoader()
        print(f"Syncing commands")
        synced = await bot.tree.sync(guild=devServerID)
        print(f'Synced {len(synced)} commands to guild {devServerID.id}')

        syncedCommands = "Synced Commands: "
        for commands in synced:
            syncedCommands += f"/{commands.name} "
        print(syncedCommands)
    except Exception as e:
        print(f'Sync error: {e}')

async def cogLoader():
    infastructurePath = os.path.join(os.path.dirname(__file__), "BotInfastructure")

    for folderName in os.listdir(infastructurePath):

        moduleName = os.path.join(infastructurePath, folderName)

        for innerFolderName in os.listdir(moduleName):

            if not innerFolderName.startswith('_'):

                innerFilePath = os.path.join(moduleName, "Cogs")

                for innerFileName in os.listdir(innerFilePath):

                    cogName = f"{moduleName}.cogs.{innerFileName[:-3]}"

                    try:

                        await bot.load_extension(cogName)
                        print(f"-> Loaded Cog: {cogName}")

                    except Exception as e:

                        print(f"-> Failed to load Cog {cogName}\n{e}")

bot.run(clientToken)