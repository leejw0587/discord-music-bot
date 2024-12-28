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
    if isinstance(error, commands.CommandOnCooldown):
        minutes, seconds = divmod(error.retry_after, 60)
        hours, minutes = divmod(minutes, 60)
        hours = hours % 24
        embed = discord.Embed(
            title="Calm down!",
            description=f"Retry after {f'{round(hours)} hours' if round(hours) > 0 else ''} {f'{round(minutes)} minutes' if round(minutes) > 0 else ''} {f'{round(seconds)} seconds' if round(seconds) > 0 else ''}",
            color=discord.Color.yellow()
        )
        await context.send(embed=embed)
    elif isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="Error!",
            description="You don't have permission for this command: `" + ", ".join(error.missing_permissions) + "`",
            color=discord.Color.red()
        )
        await context.send(embed=embed)
    elif isinstance(error, commands.MissingRole):
        embed = discord.Embed(
            title="Error!",
            description=f"You don't have role for this command: <@&{error.missing_role}>",
            color=discord.Color.red()
        )
        await context.send(embed=embed)
    elif isinstance(error, commands.BotMissingPermissions):
        embed = discord.Embed(
            title="Error!",
            description="Bot missing permission: `" + ", ".join(error.missing_permissions) + "`",
            color=discord.Color.red()
        )
        await context.send(embed=embed)
    elif isinstance(error, commands.CommandNotFound):
        embed = discord.Embed(
            title="Error!",
            description="Unknown command!",
            color=discord.Color.red()
        )
        await context.send(embed=embed)
    else:
        embed = discord.Embed(
            title="Error!",
            description=f"An unknown error occurred while executing the command\n`{error}`",
            color=discord.Color.red()
        )
        await context.send(embed=embed)
    raise error


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
