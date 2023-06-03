import logging
from typing import List

import disnake
from disnake.ext import commands, tasks

from plasmotools import settings, checks
from plasmotools.utils import api

logger = logging.getLogger(__name__)


class PenaltyUtilities(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_ban(self, guild: disnake.Guild, member: disnake.Member):
        if guild.id != settings.PlasmoRPGuild.guild_id:
            return False

        await self.check_all_penalties()

    @commands.Cog.listener()
    async def on_ready(self):
        await self.check_all_penalties()

    async def _cancel_penalty(self, penalty: dict):
        await self.bot.get_channel(settings.DevServer.penalty_logs_channel_id).send(
            embed=disnake.Embed(
                title="Automatic penalty cancellation",
            ).add_field("penalty data", penalty, inline=False)
        )
        await api.bank.cancel_penalty(penalty["id"])

    @tasks.loop(hours=12)
    async def penalties_task(self):
        await self.check_all_penalties()

    async def check_all_penalties(self):
        """
        Check all penalties and cancel them if user is banned
        """
        logger.info("Running check_all_penalties")
        active_penalties = await api.bank.get_penalties("active")
        expired_penalties = await api.bank.get_penalties("expired")
        on_check_penalties = await api.bank.get_penalties("check")

        # todo: alert when helper cannot manage penalty
        banned_players: List[str] = []
        active_players: List[str] = []
        for penalty in active_penalties + expired_penalties + on_check_penalties:
            if penalty["user"] in active_players:
                continue

            if penalty["user"] in banned_players or penalty["user"] == "PlasmoTools":
                await self._cancel_penalty(penalty)
                continue

            user_data = await api.user.get_user_data(nick=penalty["user"])
            if user_data is None:
                logger.warning("User %s not found", penalty["user"])
                continue

            if user_data["banned"]:
                banned_players.append(penalty["user"])
                await self._cancel_penalty(penalty)
            else:
                active_players.append(penalty["user"])
                continue

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
            embed=disnake.Embed(
                description="Running manual penalty check...",
                color=disnake.Color.green(),
            ),
            ephemeral=True,
        )
        await self.check_all_penalties()

    async def cog_load(self):
        logger.info("%s Ready", __name__)


def setup(client):
    """
    Internal disnake setup function
    """
    client.add_cog(PenaltyUtilities(client))
