"""
main PlasoTools file

use `python3 main.py` to start bot
"""

import logging
import os

import disnake
from disnake.ext import commands

import settings

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s/%(levelname)s]: %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()],
)
logger = logging.getLogger()

intents = disnake.Intents.all()

bot = commands.Bot(
    owner_ids=[
        737501414141591594,  # /h#9140
        222718720127139840,  # Apehum#1878
        191836876980748298,  # KPidS#3754
    ],
    status=disnake.Status.invisible,
    intents=intents,
    sync_commands=True,
    sync_permissions=True,
)

for file in os.listdir("./cogs"):
    if file.endswith(".py"):
        try:
            bot.load_extension(f"cogs.{file[:-3]}")
            logger.debug(f"Загружен: {file}")
        except Exception as err:
            logger.critical(f"Не удалось загрузить: {file}\n по причине {err}")


@bot.listen("on_ready")
async def on_ready():
    """
    On startup
    """
    await bot.get_channel(settings.DevServer.bot_logs_channel_id).send(
        embed=disnake.Embed(
            title="⚒ Plasmo Tools has been restarted",
            description=f"Version: `{settings.__version__}`",
        )
    )


if __name__ == "__main__":
    bot.run(settings.token)
