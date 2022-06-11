"""
Cog-file for listener, detects bans, unbans, role changes, cheats, deaths, fwarns in Plasmo RP Guild / Server
"""
import asyncio
import logging

import disnake
from aiohttp import ClientSession
from disnake.ext import commands

from plasmotools import settings

logger = logging.getLogger(__name__)


# TODO: Death logger (????)
# TODO: fwarns logger


class PlasmoLogger(commands.Cog):
    """
    Cog for listener, detects bans, unbans, role changes, cheats, deaths, fwarns in Plasmo RP Guild / Server
    """

    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

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

        log_channel = self.bot.get_guild(settings.LogsServer.guild_id).get_channel(
            settings.LogsServer.role_logs_channel_id
        )

        removed_roles = list(set(before.roles) - set(after.roles))
        added_roles = list(set(after.roles) - set(before.roles))

        for role in removed_roles:
            if (
                    role.id not in settings.PlasmoRPGuild.monitored_roles
                    and role.id != settings.PlasmoRPGuild.player_role_id
            ):
                continue

            log_embed = disnake.Embed(
                title=f"Роль {role.name} снята - {after.display_name}",
                color=disnake.Color.dark_red(),
                description=f"{after.mention}("
                            f"[{after.display_name}](https://rp.plo.su/u/"
                            f"{after.display_name}))",
            )

            await log_channel.send(content=f"<@{before.id}>", embed=log_embed)

        for role in added_roles:
            if role.id not in settings.PlasmoRPGuild.monitored_roles:
                continue

            log_embed = disnake.Embed(
                title=f"Роль {role.name} добавлена - {after.display_name}",
                color=disnake.Color.dark_green(),
                description=f"{after.mention}("
                            f"[{after.display_name}](https://rp.plo.su/u/"
                            f"{after.display_name}))",
            )

            msg = await log_channel.send(content=f"<@{before.id}>", embed=log_embed)
            try:
                await msg.publish()
            except disnake.HTTPException:
                pass

    @commands.Cog.listener()
    async def on_member_ban(self, guild: disnake.Guild, member: disnake.Member):
        """
        Monitor bans, calls PlasmoAPI to get reason, nickname and discord user id
        """
        if guild.id != settings.PlasmoRPGuild.guild_id:
            return False

        # TODO: Rewrite with plasmo.py

        await asyncio.sleep(10)

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

        reason: str = user_data.get("ban_reason", "Не указана")
        nickname: str = user_data.get("nick", "Неизвестен")

        log_embed = disnake.Embed(
            title="☠️ Игрок забанен",
            color=disnake.Color.red(),
            description=f"[{nickname}]"
                        f"(https://rp.plo.su/u/{nickname}) был забанен\n\n"
                        f"**Причина:**\n{reason.strip()}"
                        f"\n\n⚡ by [digital drugs technologies]({settings.LogsServer.invite_url})",
        )
        log_channel = self.bot.get_guild(settings.LogsServer.guild_id).get_channel(
            settings.LogsServer.ban_logs_channel_id
        )
        msg: disnake.Message = await log_channel.send(
            content=member.mention, embed=log_embed
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
                        await asyncio.sleep(10)
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
                        f"\n\n⚡ by [digital drugs]({settings.LogsServer.invite_url})",
        )
        log_channel = self.bot.get_guild(settings.LogsServer.guild_id).get_channel(
            settings.LogsServer.ban_logs_channel_id
        )
        msg: disnake.Message = await log_channel.send(
            content=f"<@{member.id}>", embed=log_embed
        )
        await msg.publish()

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if message.guild.id == 672312131760291842 and message.type == disnake.MessageType.thread_created:
            try:
                await message.delete(delay=10)
            except disnake.Forbidden:
                ...

    async def cog_load(self):
        logger.info("%s Ready", __name__)


def setup(client):
    """
    Internal disnake setup function
    """
    client.add_cog(PlasmoLogger(client))
