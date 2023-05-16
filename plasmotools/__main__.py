import asyncio
import logging

from plasmotools import log, settings
from plasmotools.bot import PlasmoTools
from plasmotools.utils.database import banker, plasmo_structures, rrs

log.setup()

bot = PlasmoTools.create()
logger = logging.getLogger(__name__)

asyncio.run(plasmo_structures.setup_database())
asyncio.run(rrs.roles.setup_database())
asyncio.run(rrs.actions.setup_database())
asyncio.run(banker.setup_database())

bot.i18n.load("plasmotools/locale/")
bot.load_extensions("plasmotools/ext")
bot.run(settings.TOKEN)
