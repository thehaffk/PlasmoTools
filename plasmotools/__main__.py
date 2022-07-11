import asyncio
import logging

from plasmotools import log
from plasmotools import settings
from plasmotools.bot import PlasmoSync
from plasmotools.utils.database.plasmo_structures import setup_database

log.setup()

bot = PlasmoSync.create()
logger = logging.getLogger(__name__)

bot.load_extensions("plasmotools/ext")
asyncio.run(setup_database())

bot.run(settings.TOKEN)
