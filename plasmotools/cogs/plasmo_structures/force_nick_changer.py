import logging

import disnake
from disnake.ext import commands

from plasmotools import models, settings

logger = logging.getLogger(__name__)


class ForceNickChanger(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    async def _sync_plasmo_nickname(self, member: disnake.Member):
        plasmo_guild = self.bot.get_guild(settings.PlasmoRPGuild.guild_id)
        if plasmo_guild is None:
            if settings.DEBUG:
                return
            logger.critical("Plasmo guild not found")
            return

        plasmo_member = plasmo_guild.get_member(member.id)
        if plasmo_member is None:
            return

        if plasmo_guild == member.guild:
            return

        if plasmo_member.display_name != member.display_name:
            try:
                await member.edit(
                    nick=plasmo_member.display_name,
                    reason="Changing nicknames in structures is not allowed",
                )
            except disnake.Forbidden:
                logger.warning(
                    "Unable to update username for %s at %s",
                    member.name,
                    member.guild.name,
                )

    @commands.Cog.listener("on_member_update")
    async def force_nick_changer(self, before: disnake.Member, after: disnake.Member):
        """
        Change user's nickname if it differs in structure and on Plasmo
        """
        if (
            after is None
            or before.nick == after.nick
            or before.guild.id == settings.PlasmoRPGuild.guild_id
        ):
            return

        if not (
            await models.StructureGuild.objects.filter(
                discord_id=before.guild.id
            ).exists()
        ):
            return

        await self._sync_plasmo_nickname(member=after)

    async def cog_load(self):
        """
        Called when disnake bot object is ready
        """

        logger.info("%s loaded", __name__)

        if settings.DEBUG:
            return
        await self.bot.wait_until_ready()
        logger.info("Running sync_plasmo_nickname on every player")
        for guild in self.bot.guilds:
            if not (
                await models.StructureGuild.objects.filter(discord_id=guild.id).exists()
            ):
                continue
            for member in guild.members:
                await self._sync_plasmo_nickname(member=member)


def setup(bot: disnake.ext.commands.Bot):
    """
    Disnake internal setup function
    """
    bot.add_cog(ForceNickChanger(bot))
