# import asyncio
import logging

from plasmotools import log
from plasmotools import settings
from plasmotools.bot import PlasmoSync

# from plasmotools.utils import database

log.setup()

bot = PlasmoSync.create()
logger = logging.getLogger(__name__)

bot.load_extensions("plasmotools/ext")
# asyncio.run(database.setup())

bot.run(settings.TOKEN)
