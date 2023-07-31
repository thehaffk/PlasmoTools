import asyncio
import logging
import os

from plasmotools import log, settings
from plasmotools.bot import PlasmoTools
from plasmotools.utils import models

log.setup()

bot = PlasmoTools.create()
logger = logging.getLogger(__name__)

bot.i18n.load(os.path.join("plasmotools", "locale"))
bot.load_extensions(os.path.join("plasmotools", "ext"))
asyncio.run(models.setup_database())
bot.run(settings.TOKEN)
