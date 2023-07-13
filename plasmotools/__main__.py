import asyncio
import logging

import plasmotools.utils.database.banker.setup
import plasmotools.utils.database.plasmo_structures.setup
from plasmotools import log, settings
from plasmotools.bot import PlasmoTools
from plasmotools.utils.database.rrs import actions, roles

log.setup()

bot = PlasmoTools.create()
logger = logging.getLogger(__name__)


async def setup_databases():
    await plasmotools.utils.database.plasmo_structures.setup.setup_database()
    await roles.setup_database()
    await actions.setup_database()
    await plasmotools.utils.database.banker.setup.setup_database()


asyncio.run(setup_databases())
bot.i18n.load("plasmotools/locale/")
bot.load_extensions("plasmotools/ext")
bot.run(settings.TOKEN)
