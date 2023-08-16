import asyncio
import logging
import os

from plasmotools import log, settings, models
from plasmotools.bot import PlasmoTools

log.setup()

bot = PlasmoTools.create()
logger = logging.getLogger(__name__)

bot.i18n.load(os.path.join("plasmotools", "locale"))
bot.load_extensions(os.path.join("plasmotools", "cogs"))
asyncio.run(models.setup_database())
bot.run(settings.TOKEN)
