import asyncio
import datetime
import logging
from typing import List, Union

import disnake
from disnake.ext import commands, tasks

from plasmotools import settings
from plasmotools.utils.database import rrs as rrs_database
from plasmotools.utils.database.plasmo_structures import \
    guilds as guilds_database

logger = logging.getLogger(__name__)


# todo: force role sync
# todo: scheduled sync
# todo: check for player role
# todo: rewrite all with on_audit smth

# RRS default scenario:
# listen to role changes at structure
# check if role is registered
# find operation author
# check permissions + head role check
# ask head for confirmation if needed
#       if head is not available - ask for confirmation from president
#       if president is not available - ask for confirmation from ddtech
#       rollback role at structure until confirmation
#       log changes
# check plasmo roles
# edit plasmo roles if needed
# save changes to database

# leave
# player role removed
# account transfer
# head changes


class RRSConfirmView(disnake.ui.View):
    def __init__(
        self,
    ):
        super().__init__(timeout=86400)
        self.decision = None
        self.report_to_ddt = False

    @disnake.ui.button(label="Подтвердить", style=disnake.ButtonStyle.green, emoji="✅")
    async def confirm(
        self, button: disnake.ui.Button, interaction: disnake.Interaction
    ):
        self.decision = True
        await interaction.response.send_message(
            "Операция успешно подтверждена", ephemeral=True
        )
        self.stop()

    @disnake.ui.button(label="Отменить", style=disnake.ButtonStyle.gray, emoji="❌")
    async def cancel(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        self.decision = False
        await interaction.response.send_message(
            "Операция успешно отменена", ephemeral=True
        )
        self.stop()

    # @disnake.ui.button(
    #     label="Пожаловаться на превышение полномочий",
    #     style=disnake.ButtonStyle.danger,
    #     emoji="⚠",
    #     row=1,
    # )
    # async def report_to_ddt(
    #     self, button: disnake.ui.Button, interaction: disnake.Interaction
    # ):
    #     self.report_to_ddt = True
    #     self.decision = False
    #     await interaction.response.send_message(
    #         "Операция успешно отменена, жалоба отправлена", ephemeral=True
    #     )
    #     self.stop()

    async def on_timeout(self) -> None:
        self.decision = False
        self.stop()


async def check_for_authority(
    member: disnake.Member,
    plasmo_role: disnake.Role,
    operation_author: disnake.Member,
    db_guild: guilds_database.Guild,
) -> bool:
    if (
        plasmo_role != settings.PlasmoRPGuild.mko_head_role_id
        and db_guild.head_role_id in [role.id for role in operation_author.roles]
    ):
        return True

    operation_author_plasmo_member = plasmo_role.guild.get_member(operation_author.id)
    if operation_author_plasmo_member:
        allowed_roles_ids = (
            settings.PlasmoRPGuild.admin_role_id,
            settings.PlasmoRPGuild.president_role_id,
            settings.PlasmoRPGuild.helper_role_id,
        )
        if any(
            role.id in allowed_roles_ids
            for role in operation_author_plasmo_member.roles
        ):
            return True
    return False


class RRSCore(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    async def generate_profile_embed(self, user: disnake.Member) -> disnake.Embed:
        all_rrs_rules = await rrs_database.roles.get_rrs_roles()
        embed = disnake.Embed(
            title=f"Профиль RRS - {user.display_name}",
            color=disnake.Colour.dark_green(),
        )
        plasmo_guild = self.bot.get_guild(settings.PlasmoRPGuild.guild_id)
        if not plasmo_guild:
            if settings.DEBUG:
                logger.debug(
                    "Unable to create conection with Plasmo Guild, but debug mode is on"
                )
            else:
                logger.critical("Unable to connect to Plasmo Guild")
            embed.description = (
                "Не удалось подключиться к дискорду Plasmo, сбилдить профиль не удалось"
                + "\n Debug mode is enabled, RRS is working only in debug guilds"
                if settings.DEBUG
                else ""
            )
            return embed
        plasmo_member = plasmo_guild.get_member(user.id)
        if not plasmo_member:
            embed.description = "Игрока нет в дискорде Plasmo RP"
            return embed

        active_rules_string = (
            "`id`. `роль на plasmo` - `структура` - `роль в структуре`\n"
        )
        for rule in all_rrs_rules:
            if rule.disabled:
                continue
            structure_guild = self.bot.get_guild(rule.structure_guild_id)
            if not structure_guild:
                continue
            structure_member = structure_guild.get_member(user.id)
            if not structure_member:
                continue
            structure_role = structure_guild.get_role(rule.structure_role_id)
            if not structure_role:
                continue
            if structure_role in structure_member.roles:
                plasmo_role = plasmo_guild.get_role(rule.plasmo_role_id)
                if not plasmo_role:
                    continue
                active_rules_string += f"{rule.id}. `{plasmo_role.name}` - `{structure_guild.name}` - `{structure_role.name}`\n"

        embed.add_field(
            name="Активные роли",
            value=active_rules_string,
            inline=False,
        )
        embed.add_field(
            name="История изменения ролей",
            value="В разработке, предполагаемая версия релиза - 1.6.0",
            inline=False,
        )

        return embed

    @commands.Cog.listener("on_member_update")
    async def on_member_update_listener(
        self, before: disnake.Member, after: disnake.Member
    ):
        if before.roles == after.roles:
            return
        if before.guild.id == (
            settings.LogsServer.guild_id
            if settings.DEBUG
            else settings.PlasmoRPGuild.guild_id
        ):
            return
        if await guilds_database.get_guild(
            before.guild.id
        ) is None or not await rrs_database.roles.get_rrs_roles(
            structure_guild_id=before.guild.id
        ):
            return

        async for entry in after.guild.audit_logs(
            action=disnake.AuditLogAction.member_role_update, limit=100
        ):
            if entry.target == after:
                if (
                    entry.changes.after.roles
                    == [role for role in after.roles if role not in before.roles]
                ) and (
                    (
                        entry.changes.before.roles
                        == [role for role in before.roles if role not in after.roles]
                    )
                ):
                    return await self.on_structure_role_update(entry)

    async def on_structure_role_update(
        self,
        audit_entry: disnake.AuditLogEntry,
    ):
        if audit_entry.user == self.bot.user and (
            str(audit_entry.reason).startswith("RRS")
            or str(audit_entry.reason).endswith("RRSNR")  # RRS Not Required
        ):
            # Abort if role is added/removed by RRS
            # or if update was already processed by other functions (like /hire /fire)
            return
        if audit_entry.user != self.bot.user:
            operation_author = audit_entry.user
        else:
            # todo: remove
            # todo: refactor with re
            try:
                operation_author = audit_entry.guild.get_member(
                    int(str(audit_entry.reason).split("/")[-1].replace("]", "").strip())
                )
            except ValueError:
                return logger.error(
                    f"Unexpected error while parsing reason: {audit_entry.reason}, "
                    f"{audit_entry.__dict__}"
                )

        for role in audit_entry.changes.after.roles:
            return await self.process_structure_role_change(
                member=audit_entry.target,
                role=role,
                operation_author=operation_author,
                role_is_added=True,
            )
        for role in audit_entry.changes.before.roles:
            return await self.process_structure_role_change(
                member=audit_entry.target,
                role=role,
                operation_author=operation_author,
                role_is_added=False,
            )

    async def get_head_decision(
        self,
        structure_head_role: disnake.Role,
        structure_member: disnake.Member,
        structure_role: disnake.Role,
        plasmo_role: disnake.Role,
        operation_is_add: bool,
        operation_author: disnake.Member,
    ) -> (bool, disnake.Member):
        if len(structure_head_role.members) == 0:
            return False, self.bot.user
        elif (
            len(structure_head_role.members) > 1
        ):  # todo: add support for multiple heads
            raise RuntimeError("More than one head role member")

        structure_head = structure_head_role.members[0]

        info_embed = disnake.Embed(
            title="RRS - Подтверждение операции",
            description=f"В дискорде структуры `{structure_head.guild.name}` "
            f"пользователь `{operation_author.display_name}`({operation_author.mention}) "
            f"попытался {'добавить' if operation_is_add else 'забрать'} "
            f"роль `{structure_role.name}` {'игроку' if operation_is_add else 'у игрока'} "
            f"`{structure_member.display_name}`({structure_member.mention})\n\n"
            f"К локальной роли структуры `{structure_role.name}` "
            f"привязана роль `{plasmo_role.name}` на Plasmo\n\n"
            f"У `{operation_author.display_name}`({operation_author.mention}) нет полномочий на выдачу "
            f"этой роли на Plasmo, поэтому RRS требует вашего подтверждения.",
            color=disnake.Color.dark_green(),
        )
        view = RRSConfirmView()
        confirm_msg = await structure_head.send(embed=info_embed, view=view)
        await view.wait()
        if view.decision is None:
            await structure_head.send("Время ожидания ответа истекло")
            view.decision = False
        elif view.report_to_ddt:
            await self.bot.get_channel(settings.LogsServer.rrs_logs_channel_id).send(
                embed=disnake.Embed(
                    title="Глава пожаловался на превышение полномочий",
                    description=f"`User:` {structure_member.mention} ||{structure_member.id}||\n"
                    f"`Structure:` {structure_role.name} ||{structure_role.id}||\n"
                    f"`Plasmo:` {plasmo_role.name} ||{plasmo_role.id}||\n"
                    f"`Operation:` {'Add' if operation_is_add else 'Remove'}\n"
                    f"`Operation author:` {operation_author.display_name} {operation_author.mention}\n"
                    f"`Structure head:` {structure_head.display_name} {structure_head.mention}\n"
                    f"`Guild:` {structure_head.guild.name} ||{structure_head.guild.id}||",
                    color=disnake.Color.red(),
                )
            )
        await confirm_msg.edit(components=[])
        return view.decision, structure_head

    async def process_structure_role_change(
        self,
        member: disnake.Member,
        role: disnake.Role,
        operation_author: disnake.Member,
        role_is_added: bool,
    ) -> bool:
        # todo: refactor

        db_rules: List[
            rrs_database.roles.RRSRole
        ] = await rrs_database.roles.get_rrs_roles(structure_role_id=role.id)
        db_rules = [rule for rule in db_rules if not rule.disabled]
        if not db_rules:
            return True

        db_guild = await guilds_database.get_guild(member.guild.id)
        if not db_guild:
            logger.warning(
                "There is active RRS role(s) (%s) in guild %s, but guild is not registered as structure,"
                " disabling RRS entry",
                db_rules,
                member.guild.id,
            )
            for rule in db_rules:
                await rule.edit(disabled=True)
            raise RuntimeError(
                f"There is active RRS role(s) {db_rules} in guild {member.guild.id}, "
                f"but guild is not registered as structure"
            )

        guild_logs_channel = self.bot.get_channel(db_guild.logs_channel_id)
        rrs_logs_channel = self.bot.get_channel(settings.LogsServer.rrs_logs_channel_id)

        plasmo_guild = self.bot.get_guild(
            settings.PlasmoRPGuild.guild_id
            if not settings.DEBUG
            else settings.LogsServer.guild_id
        )
        if not plasmo_guild:
            logger.error("Plasmo guild not found")
            raise RuntimeError("Plasmo guild not found")

        plasmo_member = plasmo_guild.get_member(member.id)
        if not plasmo_member:
            if role_is_added:
                await member.remove_roles(role, reason="RRS AutoRemove")
                await guild_logs_channel.send(
                    content=operation_author.mention,
                    embed=disnake.Embed(
                        title="RRS AutoRemove",
                        description=f"Role {role.mention} was added to {member.mention},\n"
                        f"but user is not in PlasmoRP server, so role was removed by PT",
                        color=disnake.Color.red(),
                    ),
                )
                return False

        for rrs_rule in db_rules:
            plasmo_role = plasmo_guild.get_role(rrs_rule.plasmo_role_id)
            if not plasmo_role:
                logger.warning(
                    "Unable to find plasmo role %s, disabling RRS entry",
                    rrs_rule.plasmo_role_id,
                )
                await rrs_logs_channel.send(
                    embed=disnake.Embed(
                        title="RRS Error",
                        description=f"Unable to find plasmo role {rrs_rule.plasmo_role_id}, disabling RRS entry\n"
                        f"RRS entry: {rrs_rule.__dict__}",
                        color=disnake.Color.red(),
                    )
                )
                return await rrs_rule.edit(disabled=True)

            operation_is_allowed = await check_for_authority(
                member=member,
                plasmo_role=plasmo_role,
                operation_author=operation_author,
                db_guild=db_guild,
            )

            # todo: rename head_user
            if not operation_is_allowed:
                if role_is_added:
                    await member.remove_roles(role, reason="RRS | 403 > HOLD")
                else:
                    await member.add_roles(role, reason="RRS | 403 > HOLD")
                await guild_logs_channel.send(
                    embed=disnake.Embed(
                        title="HOLD",
                        description=f"`User:` {member.display_name} {member.mention}\n"
                        f"`Structure:` {role.name} ||{role.id}||\n"
                        f"`Plasmo:` {plasmo_role.name} ||{plasmo_role.id}||\n"
                        f"`Author:` {operation_author.display_name} {operation_author.mention}\n"
                        f"`Operation:` {'Add' if role_is_added else 'Remove'}\n"
                        f"`Guild:` {member.guild.name} ||{member.guild.id}||",
                    )
                )
                await guild_logs_channel.send(
                    content=operation_author.mention,
                    embed=disnake.Embed(
                        title="RRS - Недостаточно полномочий",
                        color=disnake.Color.yellow(),
                        description=f"К локальной роли {role.mention}"
                        f" привяна роль **{plasmo_role.name}** на Plasmo RP\n\n"
                        f"Так как у вас нет полномочий управлять ролями на Plasmo - "
                        f"**операция ожидает подтверждения от главы структуры**",
                    ).set_footer(text="Plasmo Tools RRS"),
                )
                structure_head_role = member.guild.get_role(db_guild.head_role_id)
                if not structure_head_role:
                    logger.error(
                        "Unable to find structure head role %s", db_guild.head_role_id
                    )
                    raise RuntimeError(
                        f"Unable to find structure head role {db_guild.head_role_id}"
                    )
                try:
                    if plasmo_role.id == settings.PlasmoRPGuild.mko_head_role_id:
                        await guild_logs_channel.send(
                            content=operation_author.mention,
                            embed=disnake.Embed(
                                title="RRS - Недостаточно полномочий",
                                color=disnake.Color.dark_red(),
                                description=f"You are not allowed to change mko_head roles",
                            ),
                        )
                        return False
                    head_decision, head_user = await self.get_head_decision(
                        structure_head_role=structure_head_role,
                        structure_member=member,
                        structure_role=role,
                        plasmo_role=plasmo_role,
                        operation_author=operation_author,
                        operation_is_add=role_is_added,
                    )
                except disnake.Forbidden:
                    alert_embed = disnake.Embed(
                        title="RRS Alert",
                        description=f"Не удалось отправить сообщение главе структуры!\n"
                        f"Операция отменена",
                        color=disnake.Color.red(),
                    )
                    await guild_logs_channel.send(
                        content=operation_author.mention,
                        embed=alert_embed,
                    )
                    await self.bot.get_channel(
                        settings.LogsServer.rrs_logs_channel_id
                    ).send(
                        embed=alert_embed.add_field(
                            name="Guild",
                            value=f"{member.guild.name} ||{member.guild.id}||",
                        )
                    )
                    continue

                if not head_decision:
                    if head_user == self.bot.user:
                        await guild_logs_channel.send(
                            embed=disnake.Embed(
                                title="RRS - Невозможно подтвердить операцию",
                                color=disnake.Color.red(),
                                description=f"Не удалось найти главу структуры\n"
                                f"Операция отменена, в будущем будет добавлена поддержка альтернативных "
                                f"способов подтверждения операций",
                            ).set_footer(text="Plasmo Tools RRS"),
                        )
                        await rrs_logs_channel.send(
                            embed=disnake.Embed(
                                title="RRS Error",
                                description=f"Unable to find structure head role {db_guild} {member.guild}\n",
                            )
                        )
                        return False

                    await guild_logs_channel.send(
                        content=operation_author.mention,
                        embed=disnake.Embed(
                            title="RRS - Операция отклонена главой структуры",
                            color=disnake.Color.red(),
                            description=f"Операция была отклонена главой структуры {head_user.mention}",
                        )
                        .set_footer(text="Plasmo Tools Reverse Role Sync")
                        .add_field(
                            name="Операция",
                            value=f"{'Добавление' if role_is_added else 'Удаление'} "
                            f"роли {role.mention}",
                        ),
                    )

                    await self.bot.get_channel(
                        settings.LogsServer.rrs_logs_channel_id
                    ).send(
                        embed=disnake.Embed(
                            title="403 > DENIED",
                            description=f"`User:` {member.display_name} {member.mention}\n"
                            f"`Structure:` {role.name} ||{role.id}||\n"
                            f"`Plasmo:` {plasmo_role.name} ||{plasmo_role.id}||\n"
                            f"`Author:` {operation_author.display_name} {operation_author.mention}\n"
                            f"`Operation:` {'Add' if role_is_added else 'Remove'}\n"
                            f"`Guild:` {member.guild.name} ||{member.guild.id}||",
                        )
                    )
                    return False

                else:
                    if role_is_added:
                        await member.add_roles(
                            role,
                            reason=f"RRS | UNHOLD by {head_user}",
                        )
                    else:
                        await member.remove_roles(
                            role,
                            reason=f"RRS | UNHOLD by {head_user}",
                        )
            else:
                head_user = operation_author
            db_action = await rrs_database.actions.register_action(
                structure_role_id=role.id,
                user_id=member.id,
                author_id=operation_author.id,
                approved_by_user_id=head_user.id,
                is_role_granted=role_is_added,
                date=int(datetime.datetime.utcnow().timestamp()),
                reason="MANUAL",
            )

            plasmo_role_removed = False
            plasmo_role_added = False
            if role_is_added:
                plasmo_role_added = plasmo_role not in plasmo_member.roles
                if plasmo_role_added:
                    await plasmo_member.add_roles(
                        plasmo_role,
                        reason=f"RRS / {operation_author.display_name} / RRSID: {db_action.id}",
                    )
            else:
                plasmo_role_removed = True
                attached_db_roles = await rrs_database.roles.get_rrs_roles(
                    plasmo_role_id=plasmo_role.id
                )
                attached_db_roles = [
                    role
                    for role in attached_db_roles
                    if not role.disabled and role.id != rrs_rule.id
                ]
                if attached_db_roles:
                    for attached_db_role in attached_db_roles:
                        attached_role_members = (
                            self.bot.get_guild(attached_db_role.structure_guild_id)
                            .get_role(attached_db_role.structure_role_id)
                            .members
                        )
                        if member in attached_role_members:
                            plasmo_role_removed = False

                if plasmo_role_removed:
                    await plasmo_member.remove_roles(
                        plasmo_role,
                        reason=f"RRS / {operation_author.display_name} / RRSID: {db_action.id}",
                    )

            log_embed = disnake.Embed(
                title="RRS Log",
                description=f"`User`: {member.display_name}({member.mention})\n"
                f"`Structure:` **{'+' if role_is_added else '-'}** "
                f"{role.name} ||{role.id}||\n"
                f"`Plasmo:` {'**-**' if plasmo_role_removed else ' '}{'**+**' if plasmo_role_added else ' '} "
                f"{plasmo_role.name} ||{plasmo_role.id}||\n"
                f"`Author`: {operation_author.display_name}({operation_author.mention})",
                color=disnake.Color.green(),
            )
            await guild_logs_channel.send(embed=log_embed)
            await rrs_logs_channel.send(
                embed=log_embed.add_field(
                    name="Guild", value=f"{member.guild.name} ({member.guild.id})"
                )
            )
            return True

    async def sync_user(
        self, user: Union[disnake.Member, disnake.User], reason="Not specified"
    ):
        """
        Syncs user roles with RRS rules
        :param user: User to sync
        :param reason: Reason for sync
        """
        all_rules = [
            rule
            for rule in await rrs_database.roles.get_rrs_roles()
            if not rule.disabled
            and rule.plasmo_role_id not in settings.disallowed_to_rrs_roles
        ]
        neccessary_plasmo_roles = []
        unwanted_plasmo_roles = []
        rrs_logs_channel = self.bot.get_channel(settings.LogsServer.rrs_logs_channel_id)

        plasmo_guild = self.bot.get_guild(settings.PlasmoRPGuild.guild_id)
        if not plasmo_guild:
            return logger.critical("Unable to connect to Plasmo Guild")

        plasmo_member = plasmo_guild.get_member(user.id)
        if (
            not plasmo_member
            or plasmo_guild.get_role(settings.PlasmoRPGuild.player_role_id)
            not in plasmo_member.roles
        ):
            for rule in all_rules:
                structure_guild = self.bot.get_guild(rule.structure_guild_id)
                if not structure_guild:
                    logger.warning(
                        "Unable to connect to structure guild %d, disabling rule %d",
                        rule.structure_guild_id,
                        rule.id,
                    )
                    await rule.edit(disabled=True)
                    continue

                structure_user = structure_guild.get_member(user.id)
                if not structure_user:
                    continue

                structure_role = structure_guild.get_role(rule.structure_role_id)
                if not structure_role:
                    logger.warning(
                        "Unable to get role %d from guild %d, disabling rule %d",
                        rule.structure_role_id,
                        rule.structure_guild_id,
                        rule.id,
                    )
                    await rule.edit(disabled=True)
                    continue

                if structure_role in structure_user.roles:
                    try:
                        await structure_user.remove_roles(
                            structure_role,
                            reason="RRS | Automated Sync | User is not a player",
                        )
                        log_embed = disnake.Embed(
                            title="Automated Sync Log",
                            description=f"**Removing role bc user is not a player**\n"
                            f"`User`: {user.display_name} ({user.mention})\n"
                            f"`Structure`: {structure_guild.name} {structure_guild.id}\n"
                            f"`Role`: {structure_role.name} {structure_role.id}\n"
                            f"`Sync reason`: {reason}",
                            color=disnake.Color.dark_red(),
                        )
                        structure_logs_channel = self.bot.get_channel(
                            (
                                await guilds_database.get_guild(structure_guild.id)
                            ).logs_channel_id
                        )
                        for channel in [structure_logs_channel, rrs_logs_channel]:
                            await channel.send(embed=log_embed)
                    except disnake.Forbidden:
                        logger.warning(
                            "Unable to remove role %s from user %s",
                            structure_role.name,
                            structure_user.display_name,
                        )
                        await rrs_logs_channel.send(
                            content=f"<@&{settings.LogsServer.errors_notifications_role_id}>",
                            embed=disnake.Embed(
                                title="UNABLE TO SYNC USER",
                                description=f"**Unable to remove structure role**\n"
                                f"`User`: {user.display_name}({user.mention})\n"
                                f"`Structure`: {structure_guild.name} \n"
                                f"`Role`: {structure_role.name} \n",
                                color=disnake.Color.dark_red(),
                            ),
                        )
            return

        for rule in all_rules:
            structure_guild = self.bot.get_guild(rule.structure_guild_id)
            if not structure_guild:
                logger.warning(
                    "Unable to find guild with id %s", rule.structure_guild_id
                )
                continue

            structure_role = structure_guild.get_role(rule.structure_role_id)
            if not structure_role:
                logger.warning("Unable to find role with id %s", rule.structure_role_id)
                await rule.edit(disabled=True)
                continue

            structure_user = structure_guild.get_member(user.id)
            if not structure_user:
                unwanted_plasmo_roles.append(rule.plasmo_role_id)
                continue

            if structure_role in structure_user.roles:
                neccessary_plasmo_roles.append(rule.plasmo_role_id)
            else:
                unwanted_plasmo_roles.append(rule.plasmo_role_id)

        neccessary_plasmo_roles = set(neccessary_plasmo_roles)
        unwanted_plasmo_roles = set(unwanted_plasmo_roles) - neccessary_plasmo_roles

        removed_plasmo_roles = (
            set(  # todo: rename variables (roles_to_remove, roles_to_add or smth)
                [
                    plasmo_guild.get_role(role)
                    for role in set(unwanted_plasmo_roles)
                    if role in [_.id for _ in plasmo_member.roles]
                ]
            )
        )
        added_plasmo_roles = set(
            [
                plasmo_guild.get_role(role)
                for role in set(neccessary_plasmo_roles)
                if role not in [_.id for _ in plasmo_member.roles]
            ]
        )
        if removed_plasmo_roles or added_plasmo_roles:
            try:
                await plasmo_member.remove_roles(
                    *removed_plasmo_roles,
                    reason="RRS | Automated Sync | " + reason,
                    atomic=False,
                )
                await plasmo_member.add_roles(
                    *added_plasmo_roles,
                    reason="RRS | Automated Sync | " + reason,
                    atomic=False,
                )
                await rrs_logs_channel.send(
                    embed=disnake.Embed(
                        title="Automated Sync Log",
                        description=f"`User`: {user.display_name}({user.mention})\n"
                        f"`Removed:` {', '.join([role.name for role in removed_plasmo_roles])}\n"
                        f"`Added:` {', '.join([role.name for role in added_plasmo_roles])}\n"
                        f"`Sync reason:` {reason}",
                        color=disnake.Color.green(),
                    )
                )
            except disnake.Forbidden:
                logger.warning("Unable to sync user %s", user.id)
                await self.bot.get_channel(
                    settings.LogsServer.rrs_logs_channel_id
                ).send(
                    embed=disnake.Embed(
                        title="UNABLE TO SYNC ERROR",
                        description=f"`User`: {user.display_name}({user.mention})\n"
                        f"`not Removed:` {', '.join([role.name for role in removed_plasmo_roles])}\n"
                        f"`not Added:` {', '.join([role.name for role in added_plasmo_roles])}\n"
                        f"`Reason:` {reason}",
                        color=disnake.Color.dark_red(),
                    )
                )
                return

        return

    @tasks.loop(hours=1)
    async def sync_all_players(self):
        plasmo_guild = self.bot.get_guild(settings.PlasmoRPGuild.guild_id)
        if not plasmo_guild:
            if settings.DEBUG:
                logger.debug(
                    "Unable to create conection with Plasmo Guild, but debug mode is on"
                )
            else:
                logger.critical("Unable to connect to Plasmo Guild")
            return
        for user in plasmo_guild.members:
            await self.sync_user(user, "Синхронизация всех игроков")

    @commands.Cog.listener("on_member_remove")
    async def guild_leave_listener(self, member: disnake.Member):
        if member.guild.id == settings.PlasmoRPGuild.guild_id:
            await self.sync_user(member, "Пользователь вышел из дискорда Plasmo RP")
        elif (
            len(
                await rrs_database.roles.get_rrs_roles(
                    structure_guild_id=member.guild.id
                )
            )
            > 0
        ):
            await self.sync_user(member, "Пользователь вышел из дискорда структуры")

    @commands.Cog.listener("on_member_update")
    async def plasmo_updates_listener(
        self, before: disnake.Member, after: disnake.Member
    ):
        if before.guild.id != settings.PlasmoRPGuild.guild_id:
            return
        if before.roles == after.roles:
            return
        await asyncio.sleep(3)

        # Check if user is a player
        player_role = before.guild.get_role(settings.PlasmoRPGuild.player_role_id)
        if player_role in before.roles and player_role not in after.roles:
            await self.sync_user(
                after, "У пользователя забрали роль игрока в дискорде Plasmo RP"
            )

        # Remove all structure roles if role is removed in Plasmo Guild
        removed_roles = set([role for role in before.roles if role not in after.roles])
        operation_author = None
        operation_reason = None
        async for entry in after.guild.audit_logs(
            action=disnake.AuditLogAction.member_role_update, limit=100
        ):
            if entry.target == after:
                if (
                    entry.changes.after.roles
                    == [role for role in after.roles if role not in before.roles]
                ) and (
                    (
                        entry.changes.before.roles
                        == [role for role in before.roles if role not in after.roles]
                    )
                ):
                    operation_author = entry.user
                    operation_reason = entry.reason
                    break

        for removed_role in removed_roles:
            if removed_role.id == settings.PlasmoRPGuild.player_role_id:
                continue
            rrs_rules = [
                rule
                for rule in await rrs_database.roles.get_rrs_roles(
                    plasmo_role_id=removed_role.id
                )
                if not rule.disabled
            ]
            for rule in rrs_rules:
                structure_guild = self.bot.get_guild(rule.structure_guild_id)
                if not structure_guild:
                    logger.critical(
                        "Unable to connect to structure guild %d",
                        rule.structure_guild_id,
                    )
                    continue

                structure_role = structure_guild.get_role(rule.structure_role_id)
                if not structure_role:
                    logger.warning(
                        "Unable to found structure role %d, disabling rrs rule",
                        rule.structure_role_id,
                    )
                    await rule.edit(disabled=True)
                    continue

                structure_member = structure_guild.get_member(after.id)
                if not structure_member:
                    continue
                if structure_role in structure_member.roles:
                    try:
                        await structure_member.remove_roles(
                            structure_role,
                            reason="RRS | Automated Sync | У пользователя забрали роль в дискорде Plasmo RP",
                            atomic=False,
                        )
                        await self.bot.get_channel(
                            settings.LogsServer.rrs_logs_channel_id
                        ).send(
                            embed=disnake.Embed(
                                title="Automated Sync Log",
                                description=f"Removing structure roles bc plasmo role was removed\n"
                                f"`User`: {after.display_name}({after.mention})\n"
                                f"`Structure`: {structure_guild.name}\n"
                                f"`Removed:` {structure_role.name}\n"
                                f"`Operation author`: "
                                f"{operation_author.display_name if operation_author is not None else operation_author}"
                                f"({operation_reason})\n",
                                color=disnake.Color.green(),
                            )
                        )
                    except disnake.Forbidden:
                        logger.warning("Unable to sync user %s", after.id)
                        await self.bot.get_channel(
                            settings.LogsServer.rrs_logs_channel_id
                        ).send(
                            embed=disnake.Embed(
                                title="UNABLE TO SYNC ERROR",
                                description=f"Removing structure roles bc plasmo role was removed\n"
                                f"`User`: {after.display_name}({after.mention})\n"
                                f"`Structure`: {structure_guild.name}\n"
                                f"`not Removed:` {structure_role.name}\n",
                                color=disnake.Color.dark_red(),
                            )
                        )
                        continue

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            await self.sync_all_players.start()
        except RuntimeError:
            pass

    async def cog_load(self):
        logger.info("%s loaded", __name__)


def setup(client):
    """
    Internal disnake setup function
    """
    client.add_cog(RRSCore(client))
