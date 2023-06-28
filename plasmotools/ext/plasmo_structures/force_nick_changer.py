import logging

import disnake
from disnake.ext import commands

from plasmotools import settings
from plasmotools.utils import models

logger = logging.getLogger(__name__)

# todo: sync every structure on startup


class ForceNickChanger(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_member_update")
    async def force_nick_changer(self, before: disnake.Member, after: disnake.Member):
        """
        Change user's nickname if it differs in structure and on Plasmo
        """
        if before.nick == after.nick:
            return
        if before.guild.id == settings.PlasmoRPGuild.guild_id:
            return
        if not (
            await models.StructureGuild.objects.filter(
                discord_id=before.guild.id
            ).exists()
        ):
            return

        plasmo_guild = self.bot.get_guild(settings.PlasmoRPGuild.guild_id)
        if plasmo_guild is None:
            if settings.DEBUG:
                return
            logger.critical("Plasmo guild not found")

        plasmo_member = plasmo_guild.get_member(before.id)
        if plasmo_member is None:
            return

        if plasmo_member.display_name != after.display_name:
            await after.edit(
                nick=plasmo_member.display_name,
                reason="Changing nicknames in structures is not allowed",
            )

    async def cog_load(self):
        """
        Called when disnake bot object is ready
        """

        logger.info("%s loaded", __name__)


def setup(bot: disnake.ext.commands.Bot):
    """
    Disnake internal setup function
    """
    bot.add_cog(ForceNickChanger(bot))
