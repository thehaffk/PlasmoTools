import logging
from typing import List

import disnake
from disnake.ext import commands, tasks

from plasmotools import checks, plasmo_api, settings
from plasmotools.embeds import build_simple_embed

logger = logging.getLogger(__name__)


class PenaltyUtilities(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_ban(self, guild: disnake.Guild, _: disnake.Member):
        if guild.id == settings.PlasmoRPGuild.guild_id:
            await self.check_all_penalties()

    @commands.Cog.listener()
    async def on_ready(self):
        if settings.DEBUG:
            return
        await self.check_all_penalties()

    async def _cancel_penalty(self, penalty: dict):
        await self.bot.get_channel(settings.DevServer.penalty_logs_channel_id).send(
            embed=disnake.Embed(
                title="Automatic penalty cancellation",
            ).add_field("penalty data", penalty, inline=False)
        )
        await plasmo_api.bank.cancel_penalty(penalty["id"])

    @tasks.loop(hours=12)
    async def penalties_task(self):
        await self.check_all_penalties()

    async def check_all_penalties(self):
        """
        Check all penalties and cancel them if user is banned
        """
        logger.info("Running check_all_penalties")
        active_penalties = await plasmo_api.bank.get_penalties("active")
        expired_penalties = await plasmo_api.bank.get_penalties("expired")
        on_check_penalties = await plasmo_api.bank.get_penalties("check")

        # Checking if penalty "user" is banned
        banned_players: List[str] = []
        active_players: List[str] = []

        for penalty in active_penalties + expired_penalties + on_check_penalties:
            if penalty["user"] in active_players:
                continue

            if penalty["user"] in banned_players or penalty["user"] == "PlasmoTools":
                await self._cancel_penalty(penalty)
                continue

            user_data = await plasmo_api.user.get_user_data(nick=penalty["user"])
            if user_data is None:
                logger.warning("User %s not found", penalty["user"])
                continue

            if user_data["banned"]:
                banned_players.append(penalty["user"])
                await self._cancel_penalty(penalty)
            else:
                active_players.append(penalty["user"])

        # TODO This when ill have a access to penalty API
        # Checking if user who owns the penalty is capable of managing it
        # (admin, helper, interpol, keeper, soviet-helper)
        # can_manage_penalties: List[str] = []
        # cannot_manage_penalties: List[str] = []

        # for penalty in active_penalties + expired_penalties + on_check_penalties:
        #     if penalty["helper"] in can_manage_penalties:
        #         continue
        #
        #     if penalty["user"] in banned_players or penalty["user"] == "PlasmoTools":
        #         await self.
        #         continue
        #
        #     user_data = await plasmo_api.user.get_user_data(nick=penalty["user"])
        #     if user_data is None:
        #         logger.warning("User %s not found", penalty["user"])
        #         continue
        #
        #     if roles check:
        #         banned_players.append(penalty["user"])
        #         await self.
        #     else:
        #         active_players.append(penalty["user"])
        #         continue

    @commands.slash_command(
        name="manual-penalty-check",
        guild_ids=[settings.DevServer.guild_id, settings.LogsServer.guild_id],
        dm_permission=False,
    )
    @checks.blocked_users_slash_command_check()
    async def manual_penalty_check(self, inter: disnake.ApplicationCommandInteraction):
        """
        Manual check all penalties
        """
        await inter.send(
            embed=build_simple_embed(
                "Running manual penalty check...",
            ),
            ephemeral=True,
        )
        await self.check_all_penalties()

    async def cog_load(self):
        logger.info("%s loaded", __name__)


def setup(client):
    """
    Internal disnake setup function
    """
    client.add_cog(PenaltyUtilities(client))
