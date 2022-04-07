import logging
import os

import disnake
from disnake.ext import commands

import settings

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s/%(levelname)s]: %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

intents = disnake.Intents.all()

bot = commands.Bot(owner_ids=[737501414141591594, 222718720127139840, 191836876980748298],
                   status=disnake.Status.invisible,
                   intents=intents,
                   sync_commands=True,
                   sync_permissions=True,
                   )

for file in os.listdir('./cogs'):
    if file.endswith(".py"):
        try:
            bot.load_extension(f"cogs.{file[:-3]}")
            logger.debug(f"Загружен: {file}")
        except Exception as e:
            logger.critical(f"Не удалось загрузить: {file} по причине {e}")

if __name__ == '__main__':
    bot.run(settings.token)
