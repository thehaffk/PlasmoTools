"""
Cog-file for listener, detects bans, unbans, role changes, cheats, deaths, fwarns in Plasmo RP Guild / Server
"""
import asyncio
import logging
from typing import List

import disnake
from aiohttp import ClientSession
from disnake.ext import commands

import settings

logger = logging.getLogger(__name__)


# TODO: Death logger
# TODO: fwarns logger


class PlasmoLogger(commands.Cog):
    """
    Cog for listener, detects bans, unbans, role changes, cheats, deaths, fwarns in Plasmo RP Guild / Server
    """

    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

        self.dev_guild: disnake.Guild = self.bot.get_guild(settings.DevServer.guild_id)
        self.ban_logs_channel: disnake.TextChannel = self.dev_guild.get_channel(  # type: ignore
            settings.DevServer.ban_logs_channel_id
        )
        self.role_log_channel: disnake.TextChannel = self.dev_guild.get_channel(  # type: ignore
            settings.DevServer.role_logs_channel_id
        )

        self.monitored_roles: List[int] = settings.PlasmoRPGuild.monitored_roles

    @commands.Cog.listener()
    async def on_member_update(self, before: disnake.Member, after: disnake.Member):
        """
        Listener for role changes at Plasmo RP
        """

        if (
            after.guild.id != settings.PlasmoRPGuild.guild_id
            or before.roles == after.roles
        ):
            return False

        removed_roles = list(set(before.roles) - set(after.roles))
        added_roles = list(set(after.roles) - set(before.roles))

        for role in removed_roles:
            if role.id not in [
                *self.monitored_roles,
                [settings.PlasmoRPGuild.player_role_id],
            ]:
                continue

            log_embed = disnake.Embed(
                title=f"Роль {role.name} снята",
                color=disnake.Color.dark_red(),
                description=f"{after.mention}("
                f"[{after.display_name}](https://rp.plo.su/u/"
                f"{after.display_name}))",
            )

            await self.role_log_channel.send(content=f"<@{before.id}>", embed=log_embed)

        for role in added_roles:
            # There is no reason to monitor player_role, useless
            if role.id not in self.monitored_roles:
                continue

            log_embed = disnake.Embed(
                title=f"Роль {role.name} добавлена",
                color=disnake.Color.dark_green(),
                description=f"{after.mention}("
                f"[{after.display_name}](https://rp.plo.su/u/"
                f"{after.display_name}))",
            )

            msg = await self.role_log_channel.send(
                content=f"<@{before.id}>", embed=log_embed
            )
            try:
                await msg.publish()
            except disnake.HTTPException:
                pass

    @commands.Cog.listener()
    async def on_member_ban(self, guild: disnake.Guild, member: disnake.Member):
        """
        Monitor bans, calls PlasmoAPI to get reason, nickname (idk why) and discord user id
        """
        if guild.id != settings.PlasmoRPGuild.guild_id:
            return False

        # TODO: Rewrite with plasmo.py
        for tries in range(10):
            async with ClientSession() as session:
                async with session.get(
                    url=f"https://rp.plo.su/api/user/profile?discord_id={member.id}&fields=warns",
                ) as response:
                    try:
                        user_data = (await response.json())["data"]
                    except Exception as err:
                        logger.warning("Could not get data from PRP API: %s", err)
                        await asyncio.sleep(30)
                        continue
                    if response.status != 200:
                        logger.warning("Could not get data from PRP API: %s", user_data)
            break

        reason = user_data.get("ban_reason", "Не указана")
        nickname = user_data.get("nick", "Неизвестен")

        log_embed = disnake.Embed(
            title="☠️ Игрок забанен",
            color=disnake.Color.red(),
            description=f"[{nickname}]"
            f"(https://rp.plo.su/u/{nickname}) был забанен\n\n"
            f"**Причина:**\n{reason}"
            f"\n\n⚡ by [digital drugs]({settings.DevServer.invite_url})",
        )
        msg: disnake.Message = await self.ban_logs_channel.send(
            content=f"<@{member.id}>", embed=log_embed
        )
        await msg.publish()

    @commands.Cog.listener()
    async def on_member_unban(self, guild: disnake.Guild, member: disnake.User):
        """
        Monitor unbans, calls PlasmoAPI to get nickname and discord user id
        """
        if guild.id != settings.PlasmoRPGuild.guild_id:
            return False

        # TODO: Rewrite with plasmo.py
        for tries in range(10):
            async with ClientSession() as session:
                async with session.get(
                    url=f"https://rp.plo.su/api/user/profile?discord_id={member.id}&fields=warns",
                ) as response:
                    try:
                        user_data = (await response.json())["data"]
                    except Exception as err:
                        logger.warning("Could not get data from PRP API: %s", err)
                        await asyncio.sleep(30)
                        continue
                    if response.status != 200:
                        logger.warning("Could not get data from PRP API: %s", user_data)
            break

        nickname = user_data.get("nick", "unknown")

        log_embed = disnake.Embed(
            title="🔓 Игрок разбанен",
            color=disnake.Color.green(),
            description=f"[{nickname}]"
            f"(https://rp.plo.su/u/{nickname}) был разбанен"
            f"\n\n⚡ by [digital drugs]({settings.DevServer.invite_url})",
        )
        msg: disnake.Message = await self.ban_logs_channel.send(
            content=f"<@{member.id}>", embed=log_embed
        )
        await msg.publish()

    async def cog_load(self):
        """
        Init method
        """

        logger.info("%s Ready", __name__)


def setup(client):
    """
    Internal disnake setup function
    """
    client.add_cog(PlasmoLogger(client))
