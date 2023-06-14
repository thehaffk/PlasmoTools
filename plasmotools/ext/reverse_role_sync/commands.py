import logging
from typing import Optional

import disnake
from disnake import ApplicationCommandInteraction
from disnake.ext import commands

from plasmotools import checks, settings, utils
from plasmotools.ext.reverse_role_sync.core import RRSCore
from plasmotools.utils.database import rrs as rrs_database
from plasmotools.utils.database.plasmo_structures import guilds as guilds_database

logger = logging.getLogger(__name__)


class AdminConfirmationView(disnake.ui.View):
    """
    Confirmation view for admin commands
    """

    def __init__(self, plasmo_guild: disnake.Guild, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plasmo_guild = plasmo_guild
        self.decision = None
        self.bot = bot
        self.admin = None

    async def check_user(self, user: disnake.User) -> bool:
        """
        Check if user is admin
        """
        if settings.DEBUG:
            return user.id in self.bot.owner_ids  # Apehum
        plasmo_user = self.plasmo_guild.get_member(user.id)
        if plasmo_user is None:
            return False
        return plasmo_user.guild_permissions.administrator

    @disnake.ui.button(label="Approve", style=disnake.ButtonStyle.green)
    async def confirm(
        self, button: disnake.ui.Button, interaction: ApplicationCommandInteraction
    ):
        """
        Confirm button
        """
        if not await self.check_user(interaction.user):
            await interaction.response.send_message(
                "You are not allowed to approve/reject this request", ephemeral=True
            )
            return

        await interaction.response.send_message("Confirmed", ephemeral=True)
        self.decision = True
        self.admin = interaction.user
        self.stop()

    @disnake.ui.button(label="Reject", style=disnake.ButtonStyle.red)
    async def cancel(
        self, button: disnake.ui.Button, interaction: ApplicationCommandInteraction
    ):
        """
        Cancel button
        """
        if not await self.check_user(interaction.user):
            await interaction.response.send_message(
                "You are not allowed to approve/reject this request", ephemeral=True
            )
            return

        await interaction.response.send_message("Cancelled", ephemeral=True)
        self.decision = False
        self.admin = interaction.user
        self.stop()


class RRSCommands(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    async def get_admin_confirmation(
        self,
        author: disnake.Member,
        structure_guild_id: int,
        structure_role_id: int,
        plasmo_role_id: int,
        edit: bool = False,
        entry_id: int = None,
    ) -> bool:
        structure_guild_id = int(structure_guild_id)
        structure_role_id = int(structure_role_id)
        plasmo_role_id = int(plasmo_role_id)

        embed_title = (
            "RRS "
            + ("Добавление новой роли" if not edit else "Редактирование роли")
            + " требует подтверждения"
        )
        embed_text = ""
        if edit and entry_id is not None:
            embed_text += "Entry ID: " + str(entry_id) + "\n"
            entry = await rrs_database.roles.get_rrs_role(entry_id)
            new_structure_guild = self.bot.get_guild(structure_guild_id)
            if entry.structure_guild_id != structure_guild_id:
                old_structure_guild = self.bot.get_guild(entry.structure_guild_id)
                embed_text += (
                    f"Structure guild was changed:\n"
                    f"{old_structure_guild} -> {new_structure_guild}\n"
                    f"{entry.structure_guild_id} -> {structure_guild_id}\n"
                )
            if entry.structure_role_id != structure_role_id:
                old_structure_role = new_structure_guild.get_role(
                    entry.structure_role_id
                )
                new_structure_role = new_structure_guild.get_role(structure_role_id)
                embed_text += (
                    f"Structure role was changed:\n"
                    f"{old_structure_role} -> {new_structure_role}\n"
                    f"{entry.structure_role_id} -> {structure_role_id}\n"
                )
            if entry.plasmo_role_id != plasmo_role_id:
                if not settings.DEBUG:
                    plasmo_guild = self.bot.get_guild(settings.PlasmoRPGuild.guild_id)
                    old_plasmo_role = plasmo_guild.get_role(entry.plasmo_role_id)
                    new_plasmo_role = plasmo_guild.get_role(plasmo_role_id)
                    embed_text += (
                        f"Plasmo role was changed:\n"
                        f"{old_plasmo_role} -> {new_plasmo_role}\n"
                        f"{entry.plasmo_role_id} -> {plasmo_role_id}\n"
                    )
                else:
                    embed_text += (
                        f"Plasmo role was changed (Debug mode is enabled, unable to get actual role names):\n"
                        f"{entry.plasmo_role_id} -> {plasmo_role_id}\n"
                    )
        else:
            structure_guild = self.bot.get_guild(structure_guild_id)
            structure_role = structure_guild.get_role(structure_role_id)
            if not settings.DEBUG:
                plasmo_role = self.bot.get_guild(
                    settings.PlasmoRPGuild.guild_id
                ).get_role(plasmo_role_id)
            else:
                plasmo_role = "DEBUG MODE IS ENABLED"
            embed_text += (
                f"Structure guild: {structure_guild} {structure_guild_id}\n"
                f"Structure role: {structure_role} {structure_role_id}\n"
                f"Plasmo role: {plasmo_role} {plasmo_role_id}\n"
            )

        view = AdminConfirmationView(
            self.bot.get_guild(settings.PlasmoRPGuild.guild_id),
            self.bot,
            timeout=60 * 60 * 24,
        )
        msg = await self.bot.get_channel(
            settings.LogsServer.rrs_verification_channel_id
        ).send(
            content=f"<@&{settings.LogsServer.rrs_verifications_notifications_role_id}>",
            embed=disnake.Embed(
                title=embed_title,
                description=embed_text,
                color=disnake.Color.dark_teal(),
            ),
            view=view,
        )
        await view.wait()
        await msg.edit(
            components=[
                disnake.ui.Button(
                    label=("Approved" if view.decision else "Rejected")
                    + f" by {view.admin.display_name}"
                    if view.admin
                    else "",
                    style=disnake.ButtonStyle.gray,
                    disabled=True,
                )
            ]
        )
        return view.decision

    @commands.slash_command(name="rrs-sync")
    @commands.default_member_permissions(manage_roles=True)
    @checks.blocked_users_slash_command_check()
    async def rrs_sync_command(
        self,
        interaction: ApplicationCommandInteraction,
        user: disnake.User = None,
        user_id: str = None,
    ):
        """
        Sync roles for user

        Parameters
        ----------
        interaction
        user: User to sync roles for
        user_id: User ID to sync roles for
        """
        await interaction.response.defer(ephemeral=True)
        if user_id is not None:
            user = await self.bot.fetch_user(int(user_id))
        if user is None:
            await interaction.edit_original_message("Please provide a user")
            return
        rrs_core: Optional[RRSCore] = self.bot.get_cog("RRSCore")
        await rrs_core.sync_user(user, reason=f"Индивидуальная синхронизация")
        await interaction.edit_original_message(
            f"Синхронизация {user.mention} завершена"
        )

    @commands.slash_command(
        name="rrs-everyone-sync",
        guild_ids=[settings.DevServer.guild_id, settings.LogsServer.guild_id],
    )
    @checks.blocked_users_slash_command_check()
    @commands.is_owner()
    async def rrs_everyone_sync_command(self, inter: ApplicationCommandInteraction):
        """
        Run rrs sync for all users
        """
        await inter.response.defer(ephemeral=True)

        status_embed = disnake.Embed(
            title=f"Синхронизация всех пользователей через RRS",
            color=disnake.Color.dark_green(),
        )
        plasmo_members = self.bot.get_guild(settings.PlasmoRPGuild.guild_id).members
        guilds = await guilds_database.get_all_guilds()
        guilds = [self.bot.get_guild(guild.id) for guild in guilds]
        for guild in guilds:
            plasmo_members += guild.members
        plasmo_members = set(plasmo_members)

        rrs_core: Optional[RRSCore] = self.bot.get_cog("RRSCore")

        lazy_update_members_count = len(plasmo_members) // 10
        for counter, member in enumerate(plasmo_members):
            status_embed.clear_fields()
            await rrs_core.sync_user(
                member,
                reason=f"Синхронизация всех игроков, вызвано {inter.author.display_name}",
            )
            status_embed.add_field(
                name=f"Прогресc",
                value=utils.formatters.build_progressbar(
                    counter + 1, len(plasmo_members)
                ),
            )

            if counter % lazy_update_members_count == 0:
                await inter.edit_original_message(embed=status_embed)
            continue

        status_embed.clear_fields()
        status_embed.add_field(
            name=f"Синхронизировано пользователей: {len(plasmo_members)}/{len(plasmo_members)}",
            value=utils.formatters.build_progressbar(1, 1),
            inline=False,
        )
        await inter.edit_original_message(embed=status_embed)

    @commands.slash_command(
        name="rrs-list",
        dm_permission=False,
    )
    @commands.default_member_permissions(manage_roles=True)
    @checks.blocked_users_slash_command_check()
    async def get_registered_rrs_entries(
        self, inter: ApplicationCommandInteraction, entry_id: int = None
    ):
        """
        Get list of registered RRS entries for this guild or a list of role members if entry id is provided
        """
        await inter.response.defer(ephemeral=True)
        if entry_id is not None:
            entry = await rrs_database.roles.get_rrs_role(entry_id)
            if entry is None:
                await inter.edit_original_message("Entry not found")
                return
            if (
                entry.structure_guild_id != inter.guild.id
                and inter.author.id not in self.bot.owner_ids
            ):
                await inter.edit_original_message("You can't view this entry")
                return

            structure_guild = self.bot.get_guild(entry.structure_guild_id)
            if structure_guild is None:
                structure_guild = "Structure guild not found"
                logger.warning("Structure guild not found, disabling RRS entry")
                await entry.edit(disabled=True)
            structure_role = structure_guild.get_role(entry.structure_role_id)
            if structure_role is None:
                structure_role = "Structure role not found"
                logger.warning("Structure role not found, disabling RRS entry")
                await entry.edit(disabled=True)

            if not settings.DEBUG:
                plasmo_role_name = (
                    self.bot.get_guild(settings.PlasmoRPGuild.guild_id)
                    .get_role(entry.plasmo_role_id)
                    .name
                )
            else:
                plasmo_role_name = "debug mode is enabled"

            embed = disnake.Embed(
                title=f"RRS Entry {entry.id} | Disabled: {entry.disabled}",
                description=f"**Structure guild:** {structure_guild} `{entry.structure_guild_id}`\n"
                f"**Structure role:**  {structure_role} `{entry.structure_role_id}`\n"
                f"**Plasmo role:** {plasmo_role_name} `{entry.plasmo_role_id}`\n",
            )
            if structure_guild and structure_role:
                embed.add_field(
                    name="Structure role members",
                    value=(
                        ", ".join(
                            [
                                f"{member.display_name} {member.mention}"
                                for member in structure_role.members
                            ]
                        )
                    ).replace("_", "\_"),
                )

            return await inter.edit_original_message(
                embed=embed,
            )

        entries = await rrs_database.roles.get_rrs_roles(
            structure_guild_id=inter.guild.id
            if inter.guild.id != settings.DevServer.guild_id
            and inter.guild.id != settings.LogsServer.guild_id
            else None  # Provide None for dev/logs server, so it will return all entries, not only for dev server
        )

        rrs_embed = disnake.Embed(
            title="Registered RRS entries",
            color=disnake.Color.green(),
            description="`id`.`локальная роль` **->** `роль на PRP` **|** `количество игроков с ролью`",
        )

        plasmo_guild = self.bot.get_guild(settings.PlasmoRPGuild.guild_id)
        for structure_guild_id in set([entry.structure_guild_id for entry in entries]):
            guild = self.bot.get_guild(structure_guild_id)
            if guild is None:
                rrs_embed.add_field(
                    name="Guild not found", value=f"Guild ID: {structure_guild_id}"
                )
                continue
            roles_text = ""
            for entry in [
                entry
                for entry in entries
                if entry.structure_guild_id == structure_guild_id
            ]:
                structure_role = guild.get_role(entry.structure_role_id)
                if plasmo_guild is None and settings.DEBUG:
                    plasmo_role = None
                elif plasmo_guild is None:
                    raise RuntimeError("Plasmo guild not found")
                else:
                    plasmo_role = plasmo_guild.get_role(entry.plasmo_role_id)
                if not structure_role or not plasmo_role:
                    await entry.edit(disabled=True)
                roles_text += (
                    f"**{entry.id}.** {structure_role} **->** {plasmo_role} **|** {len(structure_role.members) if structure_role else 'role not found'} "
                    f"{'** Disabled**' if entry.disabled else ''}\n"
                ) + (
                    f"SRID: {structure_role.id}\n"
                    if inter.guild_id != settings.DevServer.guild_id
                    else ""
                )

            rrs_embed.add_field(name=guild.name, value=roles_text, inline=False)

        await inter.send(embed=rrs_embed, ephemeral=True)

    @commands.is_owner()
    @commands.slash_command(
        name="rrs-add",
        dm_permission=False,
        guild_ids=[settings.DevServer.guild_id, settings.LogsServer.guild_id],
    )
    @checks.blocked_users_slash_command_check()
    async def register_rrs_entry(
        self,
        inter: ApplicationCommandInteraction,
        sgid: str,
        srid: str,
        prid: str,
        disabled: bool = False,
    ):
        """
        Register RRS entry

        Parameters
        ----------
        inter
        sgid: structure guild id
        srid: structure role id
        prid: plasmo role id
        disabled: is disabled
        """
        await inter.response.defer(ephemeral=True)
        guild = await guilds_database.get_guild(int(sgid))
        if guild is None:
            await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description="Сервер не зарегистрирован как официальная структура.\n"
                    "Если вы считаете что это ошибка - обратитесь в "
                    f"[поддержку digital drugs technologies]({settings.DevServer.support_invite})",
                ),
                ephemeral=True,
            )
            return
        try:
            sgid = int(sgid)
            srid = int(srid)
            prid = int(prid)
        except ValueError:
            await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description="Некорректный формат ID",
                ),
                ephemeral=True,
            )
            return

        structure_guild = self.bot.get_guild(sgid)
        if structure_guild is None:
            await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description="Сервер структуры не найден",
                ),
                ephemeral=True,
            )
            return

        structure_role = structure_guild.get_role(srid)
        if structure_role is None:
            await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description="Роль в структуре не найдена",
                ),
                ephemeral=True,
            )
            return

        plasmo_guild = self.bot.get_guild(settings.PlasmoRPGuild.guild_id)
        if plasmo_guild is None:
            if settings.DEBUG:
                plasmo_role = None
            else:
                raise RuntimeError("Plasmo guild not found")
        else:
            plasmo_role = plasmo_guild.get_role(prid)
            if plasmo_role is None:
                await inter.send(
                    embed=disnake.Embed(
                        color=disnake.Color.red(),
                        title="Ошибка",
                        description="Роль в Plasmo RP не найдена",
                    ),
                    ephemeral=True,
                )
                return

        await inter.edit_original_message(
            embed=disnake.Embed(
                color=disnake.Color.green(),
                title="Data",
                description=f"**Structure guild**: {sgid} | {structure_guild}\n"
                f"**Structure role**: {srid} | {structure_role}\n"
                f"**Plasmo role**: {prid} | {plasmo_role}\n"
                f"**Disabled**: {disabled}",
            )
        )
        await inter.send("Отправлено на подтверждение", ephemeral=True)
        admin_decision = await self.get_admin_confirmation(
            inter.author,
            structure_guild.id,
            structure_role.id,
            plasmo_role.id if not settings.DEBUG else prid,
            disabled,
        )
        if not admin_decision:
            return

        entry = await rrs_database.roles.register_rrs_role(
            structure_guild_id=int(sgid),
            structure_role_id=int(srid),
            plasmo_role_id=int(prid),
            disabled=disabled,
        )

    @commands.is_owner()
    @commands.slash_command(
        name="rrs-remove",
        dm_permission=False,
        guild_ids=[settings.DevServer.guild_id, settings.LogsServer.guild_id],
    )
    @checks.blocked_users_slash_command_check()
    async def delete_rrs_entry(
        self,
        inter: ApplicationCommandInteraction,
        entry_id: int,
    ):
        """
        Delete RRS entry

        Parameters
        ----------
        inter
        entry_id: entry id
        """
        entry = await rrs_database.roles.get_rrs_role(entry_id)
        if entry is None:
            await inter.send("Entry not found", ephemeral=True)
            return

        data_string = (
            f"{entry.id} - {entry.disabled} - SGID {entry.structure_guild_id} "
            f"- SRID {entry.structure_role_id} - PRID {entry.plasmo_role_id}"
        )
        await entry.delete()
        await inter.send(f"{data_string} - deleted", ephemeral=True)

    @commands.is_owner()
    @commands.slash_command(
        name="rrs-edit",
        dm_permission=False,
        guild_ids=[settings.DevServer.guild_id, settings.LogsServer.guild_id],
    )
    @checks.blocked_users_slash_command_check()
    async def edit_rrs_entry(
        self,
        inter: ApplicationCommandInteraction,
        entry_id: int,
        disabled: bool = None,
        structure_guild_id: str = None,
        structure_role_id: str = None,
        plasmo_role_id: str = None,
    ):
        """
        Edit rrs entry

        Parameters
        ----------
        inter
        entry_id: entry id
        disabled: is disabled
        structure_guild_id: structure guild id
        structure_role_id: structure role id
        plasmo_role_id: plasmo role id
        """
        entry = await rrs_database.roles.get_rrs_role(entry_id)
        if entry is None:
            await inter.send("Entry not found", ephemeral=True)
            return

        if structure_role_id is not None or plasmo_role_id is not None:
            await inter.send("Отправлено на подтверждение", ephemeral=True)
            admin_decision = await self.get_admin_confirmation(
                inter.author,
                structure_guild_id or entry.structure_guild_id,
                structure_role_id or entry.structure_role_id,
                plasmo_role_id or entry.plasmo_role_id,
                edit=True,
                entry_id=entry_id,
            )

            if not admin_decision:
                return

        await entry.edit(
            disabled=disabled,
            structure_guild_id=int(structure_guild_id) if structure_guild_id else None,
            structure_role_id=int(structure_role_id) if structure_role_id else None,
            plasmo_role_id=int(plasmo_role_id) if plasmo_role_id else None,
        )
        await inter.edit_original_response(
            embed=disnake.Embed(
                title="RRS Rule updated",
                description=f"""raw data: 
        `entry_id = {entry_id},
        disabled = {disabled},
        structure_guild_id = {structure_guild_id},
        structure_role_id = {structure_role_id},
        plasmo_role_id = {plasmo_role_id},`
        """,
            )
        )

    async def cog_load(self):
        logger.info("%s Ready", __name__)


def setup(client):
    """
    Internal disnake setup function
    """
    client.add_cog(RRSCommands(client))
