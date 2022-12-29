"""
Cog-file for listener, detects bans, unbans, role changes, cheats, deaths, fwarns in Plasmo RP Guild / Server
"""
import asyncio
import logging
import random
import re

import disnake
from aiohttp import ClientSession
from disnake.ext import commands

from plasmotools import settings
from plasmotools.utils.database.rrs import get_action, get_rrs_roles

logger = logging.getLogger(__name__)

logo_emojis = [
    "👍",
    "😭",
    "🤨",
    "<:aRolf:952482170881048616>",
    "<:KOMAP:995730375504568361>",
    "4️⃣",
    "❤️",
    "🇿",
    "😎",
    "🍆",
    "🤡",
    "☠️",
    "🇷🇺",
    "🇺🇦",
    "<:DIANA:1053604789147160656>",
    "<:S1mple:1048173667781193738>",
    "<:4_:890216267804467280>",
]


# todo: check audit log for bans, unbans, role changes


class PlasmoLogger(commands.Cog):
    """
    Cog for listener, detects bans, unbans, role changes, cheats, deaths, fwarns in Plasmo RP Guild / Server
    """

    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_leave(self, member: disnake.Member):
        if member.guild.id != settings.PlasmoRPGuild.guild_id:
            return

        logs_guild = self.bot.get_guild(settings.LogsServer.guild_id)
        log_channel = logs_guild.get_channel(settings.LogsServer.leave_logs_channel_id)
        await log_channel.send(
            embed=disnake.Embed(
                title="PRP User Leave log",
                description=f"**Member:** {member.display_name}{member.mention}\n"
                f"**Roles:** {', '.join([role.name for role in member.roles[1:]])}",
            )
        )

    @commands.Cog.listener()
    async def on_member_update(self, before: disnake.Member, after: disnake.Member):
        """
        Listener for role changes at Plasmo RP
        """

        if (
            after.guild.id != settings.PlasmoRPGuild.guild_id
        ) or before.roles == after.roles:
            return False

        added_roles = [role for role in after.roles if role not in before.roles]
        removed_roles = [role for role in before.roles if role not in after.roles]

        audit_entry = None
        async for entry in after.guild.audit_logs(
            action=disnake.AuditLogAction.member_role_update, limit=30
        ):
            if entry.target == after and (
                added_roles == entry.after.roles or removed_roles == entry.after.roles
            ):
                audit_entry = entry
                break

        for role in removed_roles:
            await self.log_role_change(after, role, False, audit_entry)

        for role in added_roles:
            await self.log_role_change(after, role, True, audit_entry)

    async def log_role_change(
        self,
        user: disnake.Member,
        role: disnake.Role,
        is_role_added: bool,
        audit_entry: disnake.AuditLogEntry,
    ):
        if role.id not in settings.PlasmoRPGuild.monitored_roles:
            return

        description_text = (
            f" [u/{user.display_name}](https://rp.plo.su/u/{user.display_name}) "
            f"| {user.mention}"
        )
        description_text += "\n\n"

        executed_by_rrs = str(audit_entry.reason).startswith("RRS")
        if executed_by_rrs:
            if audit_entry.reason.endswith("RRS | Automated Sync"):
                description_text += (
                    "**"
                    + ("Выдано " if is_role_added else "Снято ")
                    + f"через Plasmo Tools**\n"
                    f"Причина: Автоматическая синхронизация с дискордами структур (RRS)\n"
                )
            if "RRSID" in audit_entry.reason:
                rrs_entry_id = int(
                    re.findall(r"RRS / \w* / RRSID: (\d+)", audit_entry.reason)[0]
                )
                rrs_entry = await get_action(rrs_entry_id)

                description_text += (
                    "**"
                    + ("Выдано " if is_role_added else "Снято ")
                    + f"через Plasmo Tools** (ID: {rrs_entry.id})\n"
                )

                rrs_rules = await get_rrs_roles(
                    structure_role_id=rrs_entry.structure_role_id
                )
                rrs_rule = [
                    rule for rule in rrs_rules if rule.plasmo_role_id == role.id
                ][0]
                structure_guild = self.bot.get_guild(rrs_rule.structure_guild_id)
                structure_role = structure_guild.get_role(rrs_rule.structure_role_id)

                description_text += (
                    f"**Структура:** {structure_guild.name}\n"
                    f"**Роль:** {structure_role.name}\n"
                    f"**Автор:** <@{rrs_entry.author_id}>\n"
                    f"**Одобрил:** <@{rrs_entry.approved_by_user_id}>"
                )
        else:
            operation_author = audit_entry.user
            description_text += (
                "**"
                + ("Выдал: " if is_role_added else "Снял: ")
                + "**"
                + operation_author.display_name
                + " "
                + operation_author.mention
            )

        description_text += f"\n\n|||"
        description_text += "**Роли после изменения:** " + ", ".join(
            [role.name for role in user.roles[1:]]
        )

        log_embed = disnake.Embed(
            color=disnake.Color.dark_green()
            if is_role_added
            else disnake.Color.dark_red(),
            title=f"{user.display_name}  - Роль {role.name} {'добавлена' if is_role_added else 'снята'}",
            description=description_text,
        )
        logs_guild = self.bot.get_guild(settings.LogsServer.guild_id)
        log_channel = logs_guild.get_channel(settings.LogsServer.role_logs_channel_id)
        await log_channel.send(embed=log_embed)

        logs_guild_member = logs_guild.get_member(user.id)
        if logs_guild_member:
            if (
                logs_guild.get_role(settings.LogsServer.roles_notifications_role_id)
                in logs_guild_member.roles
            ):
                await logs_guild_member.send(embed=log_embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: disnake.Guild, member: disnake.Member):
        """
        Monitor bans, calls PlasmoAPI to get reason, nickname and discord user project_id
        """
        if guild is not None and guild.id != settings.PlasmoRPGuild.guild_id:
            return False

        await asyncio.sleep(10)  # Wait for plasmo API to update

        for tries in range(10):
            async with ClientSession() as session:
                async with session.get(
                    url=f"https://rp.plo.su/api/user/profile?discord_id={member.id}&fields=stats,teams,warns",
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

        log_channel = self.bot.get_guild(settings.LogsServer.guild_id).get_channel(
            settings.LogsServer.ban_logs_channel_id
        )

        reason: str = user_data.get("ban_reason", "Не указана")
        nickname: str = user_data.get("nick", "")
        if nickname == "":
            return await log_channel.send(f"{member.mention} got banned")

        ban_time: int = user_data.get("ban_time", 0)
        user_stats: dict = user_data.get("stats", {})

        warns_text = ""
        if reason == "За красные варны":
            warns = user_data.get("warns", [])
            warns = [warn for warn in warns if not warn["revoked"] and warn["force"]]
            if warns:
                warns_text = f"**Список красных варнов:\n**"
            for warn in warns:
                warns_text += f"⚠ Выдал **{warn['helper']}** <t:{warn['date']}:R>\n {warn['message']}\n"

        log_embed = disnake.Embed(
            title=f"⚡ {nickname} получил бан",
            color=disnake.Color.dark_red(),
            description=f"""
            Причина: **{reason.strip()}**
            {'> Примечание: rows - это количество строк(логов) в базе данных. Т.е. - количество выкопанных блоков'
            if 'rows' in reason else ''}
            Профиль [Plasmo](https://rp.plo.su/u/{nickname}) | {member.mention}
            
            {warns_text.strip()}
            
            {('Получил бан: <t:' + str(ban_time) + ':R>') if ban_time > 0 else ''}
            Наиграно за текущий сезон: {user_stats.get('all', 0) / 3600:.2f} ч.
            {'Состоит в общинах:' if user_data.get('teams') else ''} {', '.join([('[' + team['name'] 
                                                                                  + '](https://rp.plo.su/t/' 
                                                                                  + team['url'] + ')')
                        for team in user_data.get('teams', [])])}
            
            {random.choice(logo_emojis)} Powered by [digital drugs technologies]({settings.LogsServer.invite_url})
                        """,
        ).set_thumbnail(url="https://rp.plo.su/avatar/" + nickname)

        msg: disnake.Message = await log_channel.send(embed=log_embed)
        await msg.publish()

    @commands.Cog.listener()
    async def on_member_unban(self, guild: disnake.Guild, member: disnake.User):
        """
        Monitor unbans, calls PlasmoAPI to get nickname and discord user project_id
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

        nickname = user_data.get("nick", "")
        if nickname == "":
            return

        log_embed = disnake.Embed(
            title=f"⚡ {nickname} был разбанен",
            color=disnake.Color.green(),
            description=f"""
            {member.mention}
            В 
            {random.choice(logo_emojis)} Powered by [digital drugs technologies]({settings.LogsServer.invite_url})""",
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
        if (
            message.channel.id == settings.PlasmoRPGuild.notifications_channel_id
            and message.author.name == "Предупреждения"
        ):
            warned_user = message.mentions[0]
            try:
                await warned_user.send(
                    "https://media.discordapp.net/"
                    "attachments/899202029656895518/971525622297931806/ezgif-7-17469e0166d2.gif"
                )
                await warned_user.send(
                    embed=disnake.Embed(
                        title="⚠ Вам выдали предупреждение на Plasmo RP",
                        color=disnake.Color.dark_red(),
                        description=f"Оспорить решение "
                        f"модерации или снять варн можно "
                        f"только тут - {settings.GCAGuild.invite_url}\n\n\n"
                        f"⚡ by [digital drugs]({settings.LogsServer.invite_url})",
                    )
                )
                await warned_user.send(
                    content=f"{settings.GCAGuild.invite_url}",
                )
            except disnake.Forbidden as err:
                logger.warning(err)
                return False

    @commands.Cog.listener()
    async def on_message_delete(self, message: disnake.Message):
        if (
            message.author.bot
            or message.guild is None
            or message.guild.id
            not in [guild.discord_id for guild in settings.structure_guilds]
            + [settings.PlasmoRPGuild.guild_id]
        ):
            return False
        if message.author.id == self.bot.user.id:
            return

        logs_channel = self.bot.get_channel(settings.LogsServer.messages_channel_id)
        embed = (
            disnake.Embed(
                description=f"Guild: **{message.guild}**\n\n"
                f"{message.author.mention} deleted message in {message.channel.mention}",
                color=disnake.Color.red(),
            )
            .add_field(
                name="Raw message",
                value=f"```{message.content}```" if message.content else "empty",
            )
            .set_footer(
                text=f"Message ID: {message.id} / Author ID: {message.author.id} / Guild ID : {message.guild.id}"
            )
        )
        if message.attachments:
            embed.set_image(url=message.attachments[0].url)
            embed.add_field(
                name="Attachments",
                value="\n".join([attachment.url for attachment in message.attachments]),
            )
        await logs_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: disnake.Message, after: disnake.Message):
        if (
            before.author.bot
            or before.guild is None
            or before.guild.id
            not in [guild.discord_id for guild in settings.structure_guilds]
            + [settings.PlasmoRPGuild.guild_id]
        ):
            return False
        if before.author.id == self.bot.user.id:
            return
        if before.content == after.content:
            return False

        logs_channel = self.bot.get_channel(settings.LogsServer.messages_channel_id)
        embed = (
            disnake.Embed(
                description=f"Guild: **{before.guild}**  \n\n{before.author.mention} edited "
                f"[message]({after.jump_url}) in {before.channel.mention}",
                color=disnake.Color.yellow(),
            )
            .add_field(
                name="Raw old message",
                value=f"```{before.content}```" if before.content else "empty",
                inline=False,
            )
            .add_field(
                name="Raw new message",
                value=f"```{after.content}```" if after.content else "empty",
            )
            .set_footer(
                text=f"Message ID: {before.id} / Author ID: {before.author.id} / Guild ID : {before.guild.id}"
            )
        )
        if before.attachments != after.attachments:
            embed.add_field(
                name="Attachments",
                value=f"{[attachment.url for attachment in before.attachments]}\n\n"
                f"{[attachment.url for attachment in after.attachments]}",
            )
        await logs_channel.send(embed=embed)

    async def cog_load(self):
        logger.info("%s Ready", __name__)


def setup(client):
    """
    Internal disnake setup function
    """
    client.add_cog(PlasmoLogger(client))
