import datetime
import logging
from typing import List

import disnake
from disnake.ext import tasks, commands

from plasmotools import settings
from plasmotools.utils.database import rrs as rrs_database
from plasmotools.utils.database.plasmo_structures import guilds as guilds_database

logger = logging.getLogger(__name__)


# todo: force role sync
# todo: scheduled sync
# todo: check for player role

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
            operation_author = audit_entry.guild.get_member(
                int(str(audit_entry.reason).split("/")[-1].replace("]", "").strip())
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

        db_rules: List[rrs_database.RRSRole] = await rrs_database.get_rrs_roles(
            structure_role_id=role.id
        )
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
            db_action = await rrs_database.register_action(
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
                attached_db_roles = await rrs_database.get_rrs_roles(
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

    async def cog_load(self):
        logger.info("%s Ready", __name__)


def setup(client):
    """
    Internal disnake setup function
    """
    client.add_cog(RRSCore(client))
