import logging

import disnake
from disnake.ext import tasks, commands

logger = logging.getLogger(__name__)


class BankerPatents(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    async def cog_load(self):
        logger.info("%s Ready", __name__)


def setup(client):
    """
    Internal disnake setup function
    """
    client.add_cog(BankerPatents(client))
