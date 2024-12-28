import discord
import asyncio
import os
import random

from discord.ext import commands, tasks
from discord.ext.commands import Bot, Context
from dotenv import load_dotenv

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = Bot(command_prefix="/", intents=intents, help_command=None)


@bot.event
async def on_ready() -> None:
    print("----------------------------------")
    print(f"Bot [{bot.user.name}] is now online!")
    print("----------------------------------")
    status_task.start()
    await bot.tree.sync() # Must to be called for the app-commands 


@tasks.loop(minutes=1.0)
async def status_task() -> None:
    statuses = ["/p"]
    await bot.change_presence(activity=discord.Game(random.choice(statuses)))


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author == bot.user or message.author.bot:
        return
    await bot.process_commands(message)


@bot.event
async def on_command_error(context: Context, error) -> None:
    embed = discord.Embed(
        title="Error!",
        description=f"An error occurred while executing the command\n`{error}`",
        color=discord.Color.red()
    )
    return await context.send(embed=embed)


async def load_cogs() -> None:
    for file in os.listdir(f"./cogs"):
        if file.endswith(".py"):
            extension = file[:-3]
            try:
                await bot.load_extension(f"cogs.{extension}")
                print(f"Loaded cog '{extension}'")
            except Exception as e:
                exception = f"{type(e).__name__}: {e}"
                print(f"Failed to load cog {extension}\n{exception}")


asyncio.run(load_cogs())
load_dotenv()
TOKEN = os.environ.get('bot_token')
bot.run(TOKEN)
