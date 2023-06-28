import datetime
import logging

import disnake
from disnake.ext import commands
from disnake.ext import commands

from plasmotools import settings
from plasmotools.utils import models

logger = logging.getLogger(__name__)


# class RRSSupervisorConfirmationView(disnake.ui.View):
#     def __init__(
#         self,
#     ):
#         super().__init__(timeout=86400)
#         self.decision = None
#         self.report_to_ddt = False
#
#     @disnake.ui.button(label="Подтвердить", style=disnake.ButtonStyle.green, emoji="✅")
#     async def confirm(
#         self, button: disnake.ui.Button, interaction: disnake.Interaction
#     ):
#         self.decision = True
#         await interaction.response.send_message("Подтверждено", ephemeral=True)
#         self.stop()
#
#     @disnake.ui.button(label="Отменить", style=disnake.ButtonStyle.gray, emoji="❌")
#     async def cancel(self, button: disnake.ui.Button, interaction: disnake.Interaction):
#         self.decision = False
#         await interaction.response.send_message("Отменено", ephemeral=True)
#         self.stop()
#
#     async def on_timeout(self) -> None:
#         self.decision = None
#         self.stop()


async def is_author_has_permission(
    structure_role: disnake.Role,
    plasmo_role: disnake.Role,
    author: disnake.Member,
    db_guild=None,
) -> bool:
    """
    Check if author has permission to change structure role
    Parameters
    ----------
    structure_role: disnake.Role
    plasmo_role: disnake.Role
    author: disnake.Member
    db_guild: guilds_database.Guild

    Returns
    -------
    bool: True if author has permission, False if not
    """
    plasmo_author = plasmo_role.guild.get_member(author.id)
    if not plasmo_author:
        return False

    author_plasmo_roles_ids = [role.id for role in plasmo_author.roles]
    if plasmo_role.id == settings.PlasmoRPGuild.president_role_id:
        return any(
            [
                settings.PlasmoRPGuild.helper_role_id in author_plasmo_roles_ids,
                settings.PlasmoRPGuild.admin_role_id in author_plasmo_roles_ids,
            ]
        )

    if plasmo_role.id in settings.disallowed_to_rrs_roles:
        return False

    if db_guild is None:
        db_guild = await models.StructureGuild.objects.get(
            discord_id=structure_role.guild.id
        )

    if structure_role == db_guild.head_role_id:
        return any(
            [
                settings.PlasmoRPGuild.president_role_id in author_plasmo_roles_ids,
                settings.PlasmoRPGuild.admin_role_id in author_plasmo_roles_ids,
            ]
        )

    if db_guild.head_role_id in [role.id for role in author.roles]:
        return True

    return False


class RRSCore(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    # todo: rewrite
    async def generate_profile_embed(self, user: disnake.Member) -> disnake.Embed:
        all_rrs_rules = await models.RRSRole.objects.all()
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
                + "\n Debug mode is enabled, RRS works only in debug guilds"
                if settings.DEBUG
                else ""
            )
            return embed
        plasmo_member = plasmo_guild.get_member(user.id)
        if not plasmo_member:
            embed.description = "Пользователя нет в дискорде Plasmo"
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

    # RRS events:
    # 1. Structure role is changed -> sync
    # 2. Left structure -> stroles = 0, sync
    # 3. Left plasmo -> remove all roles
    # 4. Plasmo role is removed -> authority check, [smart sync]
    # 5. Plasmo role is given -> authority check, [smart sync]
    # 6. Plasmo role is deleted
    # 7. Structure role is deleted
    # 8. Account transferting -> fetch new account, sync all roles, must match "Перенос аккаунта на \d+"

    @commands.Cog.listener("on_audit_log_entry_create")
    async def audit_listener(self, entry: disnake.AuditLogEntry):
        """
        Listens for audit log entries and processes them
        Parameters
        ----------
        entry: disnake.AuditLogEntry

        Returns
        -------
        None
        """
        # todo: remove
        if entry.guild.id != settings.DevServer.guild_id:
            return

        if entry.user.id == self.bot.user.id:
            if str(entry.reason).endswith("RRSNR") or str(entry.reason).startswith(
                "RRS |"
            ):
                return  # RRS Not required (already handled)

        if entry.action == disnake.AuditLogAction.member_role_update:
            if entry.guild.id == settings.PlasmoRPGuild.guild_id:
                return await self._process_plasmo_member_role_update_entry(entry=entry)

            else:
                return await self._process_structure_member_role_update_entry(
                    entry=entry
                )

        elif entry.action == disnake.AuditLogAction.role_delete:
            return await self._process_role_deletion(entry=entry)

    async def _process_structure_member_role_update_entry(
        self, entry: disnake.AuditLogEntry
    ):
        """
        Processes structure member role update entry
        """
        await self._process_structure_member_roles_update(
            author=entry.user,
            target=entry.target,
            added_roles=entry.after.roles,
            removed_roles=entry.before.roles,
            reason=entry.reason,
            from_audit=True,
        )

    async def _process_structure_member_roles_update(
        self,
        author: disnake.Member,
        target: disnake.Member,
        added_roles: list[disnake.Role],
        removed_roles: list[disnake.Role],
        reason: str = None,
        from_audit: bool = False,
    ):
        added_roles_ids = [_.id for _ in added_roles if _ not in removed_roles]
        removed_roles_ids = [_.id for _ in removed_roles if _ not in added_roles]

        not_permitted_roles_to_add = []
        not_permitted_roles_to_remove = []

        db_guild = await models.StructureGuild.objects.get(discord_id=target.guild.id)
        rrs_logs_channel = self.bot.get_channel(settings.LogsServer.rrs_logs_channel_id)

        for role in added_roles + removed_roles:
            rrs_rules = await models.RRSRole.objects.filter(
                structure_role_id=role.id
            ).all()
            for rrs_rule in rrs_rules:
                if rrs_rule.disabled:
                    continue

                if db_guild is None:
                    await self._update_rrs_rule(rule_id=rrs_rule.id, rrs_rule=rrs_rule)
                    continue

                plasmo_guild = self.bot.get_guild(settings.PlasmoRPGuild.guild_id)
                plasmo_member = plasmo_guild.get_member(target.id)
                if not plasmo_member or not any(
                    [
                        settings.PlasmoRPGuild.player_role_id
                        in [_.id for _ in plasmo_member.roles],
                        settings.PlasmoRPGuild.new_player_role_id
                        in [_.id for _ in plasmo_member.roles],
                    ]
                ):
                    if role.id in added_roles_ids:
                        await target.remove_roles(
                            role,
                            reason="RRS | It is forbidden to give non-players roles, related to rrs",
                        )
                        await rrs_logs_channel.send(
                            embed=disnake.Embed(
                                color=disnake.Color.dark_gray(),
                                title="Action prevented",
                                description=f"""
                                 `Author`: {author.display_name} ({author.id})
                                 `Target`: {target.display_name} ({target.id})
                                 `Role`: {role.name} ({role.id})
                                 `Reason`: It is forbidden to give non-players roles, related to rrs
                                 """,
                            ).add_field(
                                name="Guild",
                                value=f"{target.guild.name} | {target.guild.id}",
                            )
                        )
                        return
                    continue

                plasmo_role = plasmo_guild.get_role(rrs_rule.plasmo_role_id)
                author_has_permission = await is_author_has_permission(
                    structure_role=role,
                    plasmo_role=plasmo_role,
                    db_guild=db_guild,
                    author=author,
                )
                if not author_has_permission:
                    if role.id in added_roles_ids:
                        not_permitted_roles_to_add.append(role)
                    elif role.id in removed_roles_ids:
                        not_permitted_roles_to_remove.append(role)
                    continue

                rrs_action = await models.RRSAction.objects.create(
                    structure_role_id=role.id,
                    user_id=target.id,
                    author_id=author.id,
                    approved_by_user_id=author.id,
                    is_role_granted=role.id in added_roles_ids,
                    reason="Manual" if not from_audit else reason,
                    date=datetime.datetime.utcnow(),
                )

                if role.id in added_roles_ids:
                    try:
                        await plasmo_member.add_roles(
                            plasmo_role,
                            reason=f"RRS | {author.display_name} | RRSID {rrs_action.id}",
                        )
                    except disnake.Forbidden:
                        await rrs_action.delete()
                        await target.remove_roles(
                            role, reason="RRS | Unable to add role at Plasmo"
                        )
                        alert_embed = disnake.Embed(
                            title="RRS Error",
                            description=f"""
                            Unable to add role at Plasmo
                            `Author`: {author.display_name} ({author.id})
                            `Target`: {target.display_name} ({target.id})
                            `Structure Role`: {role.name} ({role.id})
                            `Plasmo Role`: {plasmo_role.name} ({plasmo_role.id})
                            `Reason`: {reason}
                            """,
                            color=disnake.Color.dark_red(),
                        ).add_field(
                            name="Guild",
                            value=f"{target.guild.name} | {target.guild.id}",
                        )
                        await rrs_logs_channel.send(
                            content=f"<@&{settings.LogsServer.rrs_alerts_role_id}>",
                            embed=alert_embed,
                        )
                        await author.send(
                            embed=alert_embed.add_field(
                                name="Произошла неожиданная ошибка",
                                value="Не удалось выдать роль на сервере Plasmo. "
                                "Если вы считаете, что это баг - "
                                "обратитесь в тикеты PRP",
                            )
                        )
                elif role.id in removed_roles_ids:
                    try:
                        await plasmo_member.remove_roles(
                            plasmo_role,
                            reason=f"RRS | {author.display_name} | RRSID {rrs_action.id}",
                        )
                    except disnake.Forbidden:
                        await rrs_action.delete()
                        await target.add_roles(
                            role, reason="RRS | Unable to remove role at Plasmo"
                        )
                        alert_embed = disnake.Embed(
                            title="RRS Error",
                            description=f"""
                            Unable to remove role at Plasmo
                            `Author`: {author.display_name} ({author.id})
                            `Target`: {target.display_name} ({target.id})
                            `Structure Role`: {role.name} ({role.id})
                            `Plasmo Role`: {plasmo_role.name} ({plasmo_role.id})
                            `Reason`: {reason}
                            """,
                            color=disnake.Color.dark_red(),
                        ).add_field(
                            name="Guild",
                            value=f"{target.guild.name} | {target.guild.id}",
                        )
                        await rrs_logs_channel.send(
                            content=f"<@&{settings.LogsServer.rrs_alerts_role_id}>",
                            embed=alert_embed,
                        )
                        await author.send(
                            embed=alert_embed.add_field(
                                name="Произошла неожиданная ошибка",
                                value="Не удалось забрать роль на сервере Plasmo. "
                                "Если вы считаете, что это баг - "
                                "обратитесь в тикеты PRP",
                            )
                        )

        ...  # todo: Process roles in not_permitted_..

    async def _update_rrs_rule(self, rule_id: int, rrs_rule=None, db_guild=None):
        """
        Checks if RRS rule is valid, if not, disables it
        Parameters
        ----------
        rule_id: Rule id
        rrs_rule: RRS rule, may be passed to save some db callc
        db_guild

        Returns
        -------

        """
        if not rrs_rule:
            rrs_rule = await models.RRSRole.objects.get(id=rule_id)
        if not rrs_rule or rrs_rule.disabled:
            return

        if not db_guild:
            db_guild = await models.StructureGuild.objects.get(
                discord_id=rrs_rule.structure_guild_id
            )
        guild = self.bot.get_guild(rrs_rule.structure_guild_id)
        if not db_guild or not guild:
            await rrs_rule.update(disabled=True)
            alert_embed = disnake.Embed(
                title="Problem with RRS rule",
                description=f"""
                Unable to locate db_guild/guild for rule {rrs_rule.id}
                `db_guild`: {db_guild}
                `guild`: {guild}
                
                **rule is now disabled**
                """,
                color=disnake.Color.dark_red(),
            )
            await self.bot.get_channel(settings.LogsServer.rrs_logs_channel_id).send(
                content=f"<@&{settings.LogsServer.rrs_alerts_role_id}>",
                embed=alert_embed,
            )
            return

        guild_role = guild.get_role(rrs_rule.structure_role_id)
        if not guild_role:
            await rrs_rule.update(disabled=True)
            alert_embed = disnake.Embed(
                title="Problem with RRS rule",
                description=f"""
                Unable to locate local structure role
                `rrsid`: {rrs_rule.id}
                `structure`: {guild.name} ({guild.id})
                `guild_role`: {rrs_rule.structure_role_id}

                
                **rule is now disabled**
                """,
                color=disnake.Color.dark_red(),
            )
            await self.bot.get_channel(settings.LogsServer.rrs_logs_channel_id).send(
                content=f"<@&{settings.LogsServer.rrs_alerts_role_id}>",
                embed=alert_embed,
            )
            await self.bot.get_channel(db_guild.logs_channel_id).send(
                content=f"<@&{db_guild.head_role_id}>",
                embed=alert_embed.add_field(
                    name="Warning", value="Please report this to plasmo support ASAP"
                ),
            )
            return

        plasmo_guild = self.bot.get_guild(settings.PlasmoRPGuild.guild_id)
        if plasmo_guild is None:
            if not settings.DEBUG:
                logger.error("Unable to locate plasmo guild")
                return

        plasmo_role = plasmo_guild.get_role(rrs_rule.plasmo_role_id)
        if not plasmo_role:
            await rrs_rule.update(disabled=True)
            alert_embed = disnake.Embed(
                title="Problem with RRS rule",
                description=f"""
                Unable to locate plasmo role
                `rrsid`: {rrs_rule.id}
                `structure`: {guild.name} ({guild.id})
                `plasmo_role`: {rrs_rule.plasmo_role_id}

                
                **rule is now disabled**
                """,
                color=disnake.Color.dark_red(),
            )
            await self.bot.get_channel(settings.LogsServer.rrs_logs_channel_id).send(
                content=f"<@&{settings.LogsServer.rrs_alerts_role_id}>",
                embed=alert_embed,
            )
            await self.bot.get_channel(db_guild.logs_channel_id).send(
                content=f"<@&{db_guild.head_role_id}>",
                embed=alert_embed.add_field(
                    name="Warning", value="Please report this to plasmo support ASAP"
                ),
            )
            return

    async def _process_plasmo_member_role_update_entry(
        self, entry: disnake.AuditLogEntry
    ):
        """
        Processes plasmo member role update entry
        """
        await self._process_plasmo_member_roles_update(
            author=entry.user,
            target=entry.target,
            added_roles=entry.after.roles,
            removed_roles=entry.before.roles,
            reason=entry.reason,
            from_audit=True,
        )

    async def _process_plasmo_member_roles_update(
        self,
        author: disnake.Member,
        target: disnake.Member,
        added_roles: list[disnake.Role],
        removed_roles: list[disnake.Role],
        reason: str = None,
        from_audit: bool = False,
    ):
        ...  # todo: implement

    async def _process_role_deletion(self, entry: disnake.AuditLogEntry):
        # todo: implement
        if entry.guild.id == settings.PlasmoRPGuild.guild_id:
            return

        active_linked_structure_rules = await models.RRSRole.objects.filter(
            structure_role_id=int(entry.target.id), disabled=False
        ).all()
        if not active_linked_structure_rules:
            return
        logger.info(
            "Linked structure role got deleted: structure_guild_id %s, structure_role_id: %s",
            entry.guild.id,
            entry.target.id,
        )

        structure_logs_channel = self.bot.get_channel(
            (
                await models.StructureGuild.objects.get(discord_id=entry.guild.id)
            ).logs_channel_id
        )
        rrs_logs_channel = self.bot.get_channel(settings.LogsServer.rrs_logs_channel_id)
        for rrs_rule in active_linked_structure_rules:
            await rrs_rule.update(disabled=True)
            embed = disnake.Embed(
                color=disnake.Color.dark_red(),
                title="Linked RRS role got deleted",
                description=f"""
                `User`: {entry.user.display_name} ({entry.user.mention})
                `rrs_id` {rrs_rule.id}
                `Plasmo` {self.bot.get_guild(settings.PlasmoRPGuild.guild_id)
                .get_role(rrs_rule.plasmo_role_id).name 
                if not settings.DEBUG 
                else '**debug mode is enabled**'} ({rrs_rule.plasmo_role_id})
                `Structure` {entry.before.name} {rrs_rule.structure_role_id}
                
                **rule is now disabled** 
                """,
            )
            await rrs_logs_channel.send(
                content=f"<@&{settings.LogsServer.rrs_alerts_role_id}>",
                embed=embed.add_field(
                    name="Guild", value=f"{entry.guild.name} ({entry.guild.id})"
                ),
                components=[
                    disnake.ui.Button(
                        style=disnake.ButtonStyle.green,
                        label="Attempt to restore",
                        custom_id="RRS-FIX-DELETED-ROLE_"
                        + str(rrs_rule.structure_role_id),
                        disabled=True,  # todo: remove when fixer is implemented
                    )
                ],
            )
            try:
                await structure_logs_channel.send(embed=embed)
            except disnake.HTTPException as e:  # in case of server raids (role is being deleted, it can be raid)
                logger.warning(
                    "Unable to send log message to structure logs channel because of %s",
                    e.text,
                )

    @commands.Cog.listener("on_button_click")
    async def fix_button_listener(self, inter: disnake.MessageInteraction):
        if not inter.component.custom_id.startswith("RRS-FIX-DELETED-ROLE_"):
            return
        await inter.response.send_message(
            "Sorry, this feature is not implemented yet", ephemeral=True
        )
        return

    async def process_UM_structure_role_change(
        self,
        member: disnake.Member,
        role: disnake.Role,
        author: disnake.Member,
        role_is_added: bool,
    ) -> bool:
        # todo: impement asap
        linked_rules = await models.RRSRole.objects.filter(
            structure_role_id=role.id, disabled=False
        ).all()

        plasmo_guild = self.bot.get_guild(settings.PlasmoRPGuild.guild_id)
        if not plasmo_guild:
            if settings.DEBUG:
                return True
            logger.critical("Unable to locate plasmo guild")
            return False

        return all(
            [
                await is_author_has_permission(
                    structure_role=role,
                    plasmo_role=plasmo_guild.get_role(rule.plasmo_role_id),
                    author=author,
                )
                for rule in linked_rules
            ]
        )

    # @tasks.loop(hours=1)
    # async def scheduled_sync(self):
    #     ...

    # @commands.Cog.listener()
    # async def on_ready(self):
    # if not self.sync_all_players.is_running():
    #     await self.sync_all_players.start()

    async def cog_load(self):
        logger.info("%s loaded", __name__)


def setup(client):
    """
    Internal disnake setup function
    """
    client.add_cog(RRSCore(client))
