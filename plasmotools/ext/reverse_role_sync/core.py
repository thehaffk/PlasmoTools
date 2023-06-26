import logging

import disnake
from disnake.ext import commands
from disnake.ext import commands

from plasmotools import settings
from plasmotools.utils.database import rrs as rrs_database
from plasmotools.utils.database.plasmo_structures import guilds as guilds_database

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
        await interaction.response.send_message("Подтверждено", ephemeral=True)
        self.stop()

    @disnake.ui.button(label="Отменить", style=disnake.ButtonStyle.gray, emoji="❌")
    async def cancel(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        self.decision = False
        await interaction.response.send_message("Отменено", ephemeral=True)
        self.stop()

    async def on_timeout(self) -> None:
        self.decision = None
        self.stop()



async def is_author_has_permission(
    structure_role: disnake.Role,
    plasmo_role: disnake.Role,
    db_guild: guilds_database.Guild,
    entry: disnake.AuditLogEntry,
) -> bool:
    """
    Check if author has permission to change structure role
    Parameters
    ----------
    structure_role: disnake.Role
    plasmo_role: disnake.Role
    db_guild: guilds_database.Guild
    entry: disnake.AuditLogEntry

    Returns
    -------
    bool: True if author has permission, False if not
    """
    plasmo_author = plasmo_role.guild.get_member(entry.user.id)
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

    if structure_role == db_guild.head_role_id:
        return any(
            [
                settings.PlasmoRPGuild.president_role_id in author_plasmo_roles_ids,
                settings.PlasmoRPGuild.admin_role_id in author_plasmo_roles_ids,
            ]
        )

    if db_guild.head_role_id in [role.id for role in entry.user.roles]:
        return True

    return False


class RRSCore(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    # todo: rewrite
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

        if entry.user.id == self.bot.user.id and str(entry.reason).endswith("RRSNR"):
            return  # RRS Not required (already handled)

        if entry.action == disnake.AuditLogAction.member_role_update:
            if entry.guild.id == settings.PlasmoRPGuild.guild_id:
                return await self.process_donor_role_change(entry=entry)

            else:
                return await self.process_structure_role_change(entry=entry)

        elif entry.action == disnake.AuditLogAction.role_delete:
            return await self.process_role_deletion(entry=entry)

    async def process_structure_role_change(self, entry: disnake.AuditLogEntry):
        """
        Checks if changed role has any RRS rules, if so, syncs them

        Parameters
        ----------
        entry: disnake.AuditLogEntry

        Returns
        -------
        None
        """

        added_roles_ids = [
            _.id for _ in entry.after.roles if _ not in entry.before.roles
        ]
        removed_roles_ids = [
            _.id for _ in entry.before.roles if _ not in entry.after.roles
        ]

        db_guild = await guilds_database.get_guild(entry.guild.id)
        rrs_logs_channel = self.bot.get_channel(settings.LogsServer.rrs_logs_channel_id)

        for role in entry.before.roles + entry.after.roles:
            rrs_rules = await rrs_database.roles.get_rrs_roles(
                structure_role_id=role.id
            )
            for rrs_rule in rrs_rules:
                if rrs_rule.disabled:
                    continue

                if db_guild is None:
                    await self.update_rrs_rule(rule_id=rrs_rule.id, rrs_rule=rrs_rule)
                    continue

                plasmo_guild = self.bot.get_guild(settings.PlasmoRPGuild.guild_id)
                plasmo_member = plasmo_guild.get_member(int(entry.target.id))
                if not plasmo_member or not (
                    settings.PlasmoRPGuild.player_role_id
                    in [_.id for _ in plasmo_member.roles]
                ):
                    if role.id in added_roles_ids:
                        await entry.target.remove_roles(
                            role,
                            reason="It is forbidden to give non-players roles, related to rrs | RRSNR",
                        )
                        await rrs_logs_channel.send(
                            embed=disnake.Embed(
                                color=disnake.Color.dark_gray(),
                                title="Action prevented",
                                description=f"""
                                 `Author`: {entry.user.display_name} ({entry.user.id})
                                 `Target`: {entry.target.display_name} ({entry.target.id})
                                 `Role`: {role.name} ({role.id})
                                 `Reason`: It is forbidden to give non-players roles, related to rrs
                                 """,
                            ).add_field(
                                name="Guild",
                                value=f"{entry.guild.name} | {entry.guild.id}",
                            )
                        )
                        return
                    continue

                plasmo_role = plasmo_guild.get_role(rrs_rule.plasmo_role_id)
                author_has_permission = await is_author_has_permission(
                    structure_role=role,
                    plasmo_role=plasmo_role,
                    db_guild=db_guild,
                    entry=entry,
                )

    async def update_rrs_rule(self, rule_id: int, rrs_rule=None, db_guild=None):
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
            rrs_rule = await rrs_database.roles.get_rrs_role(rule_id)
        if not rrs_rule or rrs_rule.disabled:
            return

        if not db_guild:
            db_guild = await guilds_database.get_guild(rrs_rule.structure_guild_id)
        guild = self.bot.get_guild(rrs_rule.structure_guild_id)
        if not db_guild or not guild:
            await rrs_rule.edit(disabled=True)
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
            await rrs_rule.edit(disabled=True)
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
            await rrs_rule.edit(disabled=True)
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

    async def process_donor_role_change(self, entry: disnake.AuditLogEntry):
        ...

    # todo: implement
    async def process_role_deletion(self, entry: disnake.AuditLogEntry):
        if entry.guild.id == settings.PlasmoRPGuild.guild_id:
            return

        active_linked_structure_rules = await rrs_database.roles.get_rrs_roles(
            structure_role_id=int(entry.target.id), active=True
        )
        if not active_linked_structure_rules:
            return
        logger.info(
            "Linked structure role got deleted: sgid %s, srid: %s",
            entry.guild.id,
            entry.target.id,
        )

        structure_logs_channel = self.bot.get_channel(
            (await guilds_database.get_guild(discord_id=entry.guild.id)).logs_channel_id
        )
        rrs_logs_channel = self.bot.get_channel(settings.LogsServer.rrs_logs_channel_id)
        for rrs_rule in active_linked_structure_rules:
            await rrs_rule.edit(disabled=True)
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

    # @tasks.loop(hours=1)
    # async def scheduled_sync(self):
    #     ...

    # @commands.Cog.listener()
    # async def on_ready(self):
    #     if not self.sync_all_players.is_running():
    #         await self.sync_all_players.start()

    async def cog_load(self):
        logger.info("%s loaded", __name__)


def setup(client):
    """
    Internal disnake setup function
    """
    client.add_cog(RRSCore(client))
