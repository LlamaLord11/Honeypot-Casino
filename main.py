import sys, os


import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

sys.dont_write_bytecode = True

load_dotenv()

clientToken = os.getenv("BOT_TOKEN")

bot = commands.Bot(command_prefix='/', intents=discord.Intents.all())

devServer = discord.Object(id=int(os.getenv("DEV_SERVER_ID")))

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    try:
        await cogLoader()
        print(f"Syncing commands")
        synced = await bot.tree.sync(guild=devServer)

        guild = bot.get_guild(devServer.id)
        if guild is None:
            guild = await bot.fetch_guild(devServer.id)

        print(f'+ Synced {len(synced)} commands. Guild: {guild.name} | ID: {devServer.id}')

        syncedCommands = "+ Synced Commands: "
        for commands in synced:
            syncedCommands += f"/{commands.name} "
        print(syncedCommands)
    except Exception as e:
        print(f'Sync error: {e}')

async def cogLoader():
    infastructurePath = os.path.join(os.path.dirname(__file__), "BotInfastructure")

    for moduleName in os.listdir(infastructurePath):

        innerModuleName = os.path.join(infastructurePath, moduleName)

        for innerFolderName in os.listdir(innerModuleName):

            if not innerFolderName.startswith('_'):

                innerFilePath = os.path.join(innerModuleName, "Cogs")

                for innerFileName in os.listdir(innerFilePath):

                    if not innerFileName.endswith(".py") or innerFileName == "__init__.py":
                        continue

                    cogName = f"BotInfastructure.{moduleName}.{innerFolderName}.{innerFileName[:-3]}"

                    try:

                        await bot.load_extension(cogName)
                        print(f"-> Loaded Cog: {innerFileName[:-3]}")

                    except Exception as e:

                        print(f"-> Failed to load Cog {cogName}\n{e}")

bot.run(clientToken)