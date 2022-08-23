import logging

import disnake
from disnake.ext import tasks, commands

from plasmotools import settings

logger = logging.getLogger(__name__)


class CompolsoryService(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.check_all_entries()

    @tasks.loop(hours=12)
    async def check_all_entries(self):
        """
        Check all penalties and cancel them if user is banned
        """
        logger.info("Running check_all_entries")
        ...

    @commands.slash_command(
        name="manual-cs-check",
        guild_ids=[settings.DevServer.guild_id, settings.LogsServer.guild_id],
    )
    async def manual_penalty_check(self, inter: disnake.ApplicationCommandInteraction):
        """
        Manual check all penalties
        """
        await inter.send(
            embed=disnake.Embed(
                description="Running manual penalty check...",
                color=disnake.Color.green(),
            ),
            ephemeral=True,
        )
        await self.check_all_entries()

    async def cog_load(self):
        logger.info("%s Ready", __name__)


def setup(client):
    """
    Internal disnake setup function
    """
    client.add_cog(CompolsoryService(client))
