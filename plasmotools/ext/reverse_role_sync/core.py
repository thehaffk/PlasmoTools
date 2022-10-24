import logging

import disnake
from disnake.ext import tasks, commands

from plasmotools import settings
from plasmotools.utils.database import rrs as rrs_database
from plasmotools.utils.database.plasmo_structures import guilds as guilds_database

logger = logging.getLogger(__name__)


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

    @disnake.ui.button(
        label="Пожаловаться на превышение полномочий",
        style=disnake.ButtonStyle.danger,
        emoji="⚠",
        row=1,
    )
    async def report_to_ddt(
        self, button: disnake.ui.Button, interaction: disnake.Interaction
    ):
        self.report_to_ddt = True
        self.decision = False
        await interaction.response.send_message(
            "Операция успешно отменена, жалоба отправлена", ephemeral=True
        )
        self.stop()

    async def on_timeout(self) -> None:
        self.decision = False
        self.stop()


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
        added_roles = [role for role in after.roles if role not in before.roles]
        removed_roles = [role for role in before.roles if role not in after.roles]
        # ????
        target_roles = added_roles if added_roles else removed_roles
        is_role_added = True if added_roles else False

        async for entry in after.guild.audit_logs(
            action=disnake.AuditLogAction.member_role_update, limit=100
        ):
            if entry.target == after:
                if (is_role_added and entry.changes.after.roles == target_roles) or (
                    not is_role_added and entry.changes.before.roles == target_roles
                ):
                    return await self.sync_structure_update(
                        after, target_roles[0], is_role_added, entry
                    )

    async def get_head_decision(
        self,
        head_user: disnake.Member,
        structure_member: disnake.Member,
        structure_role: disnake.Role,
        plasmo_role: disnake.Role,
        operation_is_add: bool,
        operation_author: disnake.Member,
    ) -> bool:
        info_embed = disnake.Embed(
            title="RRS - Подтверждение операции",
            description=f"В дискорде структуры `{head_user.guild.name}` "
            f"`{operation_author.display_name}`({operation_author.mention}) "
            f"попытался {'добавить' if operation_is_add else 'забрать'} "
            f"роль `{structure_role.name}` {'игроку' if operation_is_add else 'у игрока'} "
            f"`{structure_member.display_name}`({structure_member.mention})\n\n"
            f"К локальной роли структуры`{structure_role.name}` "
            f"привязана роль `{plasmo_role.name}` на Plasmo\n\n"
            f"У `{operation_author.display_name}`({operation_author.mention}) нет полномочий на выдачу "
            f"этой роли на Plasmo, поэтому RRS требует вашего подтверждения на.",
            color=disnake.Color.dark_green(),
        )
        view = RRSConfirmView()
        confirm_msg = await head_user.send(embed=info_embed, view=view)
        await view.wait()
        if view.decision is None:
            await head_user.send("Время ожидания ответа истекло")
            view.decision = False
        elif view.report_to_ddt:
            await self.bot.get_channel(settings.LogsServer.rrs_logs_channel_id).send(
                embed=disnake.Embed(
                    title="Глава пожаловался на превышение полномочий",
                    description=f"`User:` {structure_member.mention} ||{structure_member.id}||\n"
                    f"`Structure:` {structure_role.name} ||{structure_role.id}||\n"
                    f"`Plasmo:` {plasmo_role.name} ||{plasmo_role.id}||\n"
                    f"`Author:` {operation_author.mention} ||{operation_author.id}||\n"
                    f"`Operation:` {'Add' if operation_is_add else 'Remove'}\n"
                    f"`Operation author:` {operation_author.display_name} {operation_author.mention}\n"
                    f"`Structure head:` {head_user.display_name} {head_user.mention}\n"
                    f"`Guild:` {head_user.guild.name} ||{head_user.guild.id}||",
                    color=disnake.Color.red(),
                )
            )
        await confirm_msg.edit(components=[])
        return view.decision

    async def sync_structure_update(
        self,
        member: disnake.Member,
        role: disnake.Role,
        structure_role_added: bool,
        audit_entry: disnake.AuditLogEntry,
    ):
        # todo: divide this into smaller functions

        if audit_entry.user == self.bot.user and str(audit_entry.reason).startswith(
            "RRS"
        ):
            # Abort if role is added/removed by RRS (structure head declined request / some other errors)
            return
        db_roles = await rrs_database.get_rrs_roles(structure_role_id=role.id)
        db_roles = [role for role in db_roles if not role.disabled]
        if not db_roles:
            return

        db_guild = await guilds_database.get_guild(member.guild.id)
        if not db_guild:
            logger.warning(
                "There is active RRS role(s) (%s) in guild %s, but guild is not registered as structure,"
                " disabling RRS entry",
                db_roles,
                member.guild.id,
            )
            for db_role in db_roles:
                await db_role.edit(disabled=True)
            raise RuntimeError(
                f"There is active RRS role(s) {db_roles} in guild {member.guild.id}, "
                f"but guild is not registered as structure"
            )

        plasmo_guild = self.bot.get_guild(
            settings.LogsServer.guild_id
            if settings.DEBUG
            else settings.PlasmoRPGuild.guild_id
        )

        plasmo_member = plasmo_guild.get_member(member.id)
        if not plasmo_member:
            if structure_role_added:
                await member.remove_roles(role, reason="RRS AutoRemove")
                return await self.bot.get_channel(db_guild.logs_channel_id).send(
                    content=audit_entry.user.mention,
                    embed=disnake.Embed(
                        title="RRS AutoRemove",
                        description=f"Role {role.mention} was added to {member.mention},\n"
                        f"but user is not in PlasmoRP server, so role was removed by PT",
                        color=disnake.Color.red(),
                    ),
                )

        structure_heads = member.guild.get_role(db_guild.head_role_id).members
        for db_role in db_roles:
            plasmo_role = plasmo_guild.get_role(db_role.plasmo_role_id)
            if not plasmo_role:
                logger.warning(
                    "Unable to find plasmo role %s, disabling RRS entry",
                    db_role.plasmo_role_id,
                )
                await db_role.edit(disabled=True)
                raise RuntimeError(
                    f"Unable to find plasmo role {db_role.plasmo_role_id}"
                )

            operation_is_allowed = False

            if audit_entry.user == self.bot.user:
                operation_author = member.guild.get_member(
                    int(audit_entry.reason.split("/ ")[-1][:-1])
                )
            else:
                operation_author = audit_entry.user
            if operation_author in structure_heads:
                operation_is_allowed = True

            operation_author_plasmo_member = plasmo_guild.get_member(
                operation_author.id
            )
            if operation_author_plasmo_member:
                allowed_roles_ids = (
                    settings.PlasmoRPGuild.admin_role_id,
                    settings.PlasmoRPGuild.president_role_id,
                    settings.PlasmoRPGuild.helper_role_id,
                )
                if (
                    any(
                        role.id in allowed_roles_ids
                        for role in operation_author_plasmo_member.roles
                    )
                ):
                    operation_is_allowed = True

            # TODO: ask head
            if not operation_is_allowed:
                if structure_role_added:
                    await member.remove_roles(role, reason="RRS | 403 | HOLD")
                else:
                    await member.add_roles(role, reason="RRS | 403 | HOLD")
                hold_embed = disnake.Embed(
                    title="RRS - Недостаточно полномочий",
                    color=disnake.Color.yellow(),
                    description=f"К локальной роли {role.mention} привяна роль **{plasmo_role.name}** на Plasmo RP\n\n"
                    f"Так как у вас нет полномочий управлять ролями на Plasmo - "
                    f"**операция ожидает подтверждения от главы структуры**",
                ).set_footer(text="Plasmo Tools Reverse Role Sync")
                await self.bot.get_channel(
                    settings.LogsServer.rrs_logs_channel_id
                ).send(
                    embed=disnake.Embed(
                        title="403 | HOLD",
                        description=f"`User:` {member.mention} ||{member.id}||\n"
                        f"`Structure:` {role.name} ||{role.id}||\n"
                        f"`Plasmo:` {plasmo_role.name} ||{plasmo_role.id}||\n"
                        f"`Author:` {operation_author.mention} ||{operation_author.id}||\n"
                        f"`Operation:` {'Add' if structure_role_added else 'Remove'}\n"
                        f"`Guild:` {member.guild.name} ||{member.guild.id}||",
                    )
                )
                await self.bot.get_channel(db_guild.logs_channel_id).send(
                    content=operation_author.mention,
                    embed=hold_embed,
                    components=[
                        disnake.ui.Button(
                            label="Отменить операцию (Потом сделаю)",
                            emoji="❌",
                            style=disnake.ButtonStyle.red,
                            disabled=True,
                        )
                    ],
                )

                if len(structure_heads) != 1:
                    head_role = member.guild.get_role(db_guild.head_role_id)
                    alert_embed = disnake.Embed(
                        title="RRS Alert",
                        description=f"Не удалось найти главу структуры!\n"
                        f"Ролью {head_role.name}||{head_role.mention}|| "
                        f"должен владеть только один пользователь\n"
                        f"Если вы считаете, что произошла ошибка откройте тикет в дискорде Plasmo RP",
                        color=disnake.Color.red(),
                    )
                    await self.bot.get_channel(db_guild.logs_channel_id).send(
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

                try:
                    if not await self.get_head_decision(
                        head_user=structure_heads[0],
                        structure_member=member,
                        structure_role=role,
                        plasmo_role=plasmo_role,
                        operation_author=operation_author,
                        operation_is_add=structure_role_added,
                    ):
                        await member.guild.get_channel(db_guild.logs_channel_id).send(
                            content=operation_author.mention,
                            embed=disnake.Embed(
                                title="RRS - Операция отклонена главой структуры",
                                color=disnake.Color.red(),
                                description=f"Операция была отклонена главой структуры {structure_heads[0].mention}",
                            )
                            .set_footer(text="Plasmo Tools Reverse Role Sync")
                            .add_field(
                                name="Операция",
                                value=f"{'Добавление' if structure_role_added else 'Удаление'} "
                                f"роли {role.mention}",
                            ),
                        )

                        await self.bot.get_channel(
                            settings.LogsServer.rrs_logs_channel_id
                        ).send(
                            embed=disnake.Embed(
                                title="403 | DENIED",
                                description=f"`User:` {member.mention} ||{member.id}||\n"
                                f"`Structure:` {role.name} ||{role.id}||\n"
                                f"`Plasmo:` {plasmo_role.name} ||{plasmo_role.id}||\n"
                                f"`Author:` {operation_author.mention} ||{operation_author.id}||\n"
                                f"`Operation:` {'Add' if structure_role_added else 'Remove'}\n"
                                f"`Guild:` {member.guild.name} ||{member.guild.id}||",
                            )
                        )
                        continue
                    else:
                        if structure_role_added:
                            await member.add_roles(
                                role,
                                reason="RRS | UNHOLD by " + structure_heads[0].name,
                            )
                        else:
                            await member.remove_roles(
                                role,
                                reason="RRS | UNHOLD by " + structure_heads[0].name,
                            )

                except disnake.Forbidden:
                    alert_embed = disnake.Embed(
                        title="RRS Alert",
                        description=f"Не удалось отправить сообщение главе структуры!\n"
                        f"Операция отменена",
                        color=disnake.Color.red(),
                    )
                    await self.bot.get_channel(db_guild.logs_channel_id).send(
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

            plasmo_role_removed = False
            plasmo_role_added = False
            if structure_role_added:
                plasmo_role_added = plasmo_role not in plasmo_member.roles
                if plasmo_role_added:
                    await plasmo_member.add_roles(
                        plasmo_role,
                        reason=f"RRS / {operation_author.display_name} / {operation_author.id}",
                    )
            else:
                plasmo_role_removed = True
                attached_db_roles = await rrs_database.get_rrs_roles(
                    plasmo_role_id=plasmo_role.id
                )
                attached_db_roles = [
                    role
                    for role in attached_db_roles
                    if not role.disabled and role.id != db_role.id
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
                        reason=f"RRS / {operation_author.display_name} / {operation_author.id}",
                    )

            log_embed = disnake.Embed(
                title="RRS Log",
                description=f"`User`: {member.mention}\n"
                f"`Structure:` **{'+' if structure_role_added else '-'}** "
                f"{role.name} ||{role.mention}||\n"
                f"`Plasmo:` {'**-**' if plasmo_role_removed else ' '}{'**+**' if plasmo_role_added else ' '} "
                f"{plasmo_role.name} ||{plasmo_role.id}||\n"
                f"`Author`: {operation_author.mention}({operation_author.display_name})",
                color=disnake.Color.green(),
            )
            await self.bot.get_channel(db_guild.logs_channel_id).send(embed=log_embed)
            await self.bot.get_channel(settings.LogsServer.rrs_logs_channel_id).send(
                embed=log_embed.add_field(
                    name="Guild", value=f"{member.guild.name} ({member.guild.id})"
                )
            )

    async def cog_load(self):
        logger.info("%s Ready", __name__)


def setup(client):
    """
    Internal disnake setup function
    """
    client.add_cog(RRSCore(client))
