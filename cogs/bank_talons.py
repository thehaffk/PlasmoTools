"""
Cog-file for talons
"""
import logging
import disnake
from disnake import ApplicationCommandInteraction
from disnake.ext import commands

import settings

logger = logging.getLogger(__name__)


class BankTalons(commands.Cog):
    """
    Cog for 4
    """
    print("4")

    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        """
        Called when disnake bot object is ready
        """

        logger.info("%s Ready", __name__)


def setup(client):
    """
    Disnake internal setup function
    """
    client.add_cog(BankTalons(client))
