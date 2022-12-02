import asyncio
import logging

from plasmotools import log
from plasmotools import settings
from plasmotools.bot import PlasmoSync
from plasmotools.utils.database import banker
from plasmotools.utils.database import plasmo_structures
from plasmotools.utils.database import rrs

log.setup()

bot = PlasmoSync.create()
logger = logging.getLogger(__name__)

bot.load_extensions("plasmotools/ext")
asyncio.run(plasmo_structures.setup_database())
asyncio.run(rrs.roles.setup_database())
asyncio.run(rrs.actions.setup_database())
asyncio.run(banker.setup_database())

bot.run(settings.TOKEN)
