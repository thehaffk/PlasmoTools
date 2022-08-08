"""
Cog-file for listener, detects bans, unbans, role changes, cheats, deaths, fwarns in Plasmo RP Guild / Server
"""
import logging

import disnake
from disnake.ext import tasks, commands

logger = logging.getLogger(__name__)


class Fun(commands.Cog):
    """
    Cog for listener, detects bans, unbans, role changes, cheats, deaths, fwarns in Plasmo RP Guild / Server
    """

    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if message.content == self.bot.user.mention:
            try:
                await message.reply(
                    "https://tenor.com/view/discord-komaru-gif-26032653"
                )
            except disnake.Forbidden:
                pass

    async def cog_load(self):
        logger.info("%s Ready", __name__)


def setup(client):
    """
    Internal disnake setup function
    """
    client.add_cog(Fun(client))
