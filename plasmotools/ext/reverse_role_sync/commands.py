import logging

import disnake
from disnake import ApplicationCommandInteraction
from disnake.ext import tasks, commands

from plasmotools import settings
from plasmotools import utils
from plasmotools.ext.reverse_role_sync.core import RRSCore
from plasmotools.utils.database import rrs as rrs_database
from plasmotools.utils.database.plasmo_structures import guilds as guilds_database

logger = logging.getLogger(__name__)


class RRSCommands(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    @commands.slash_command(name="rrs-sync")
    @commands.is_owner()
    async def rrs_sync_command(
        self,
        interaction: ApplicationCommandInteraction,
        user: disnake.User = None,
        user_id: str = None,
    ):
        await interaction.response.defer(ephemeral=True)
        if user_id is not None:
            user = await self.bot.fetch_user(int(user_id))
        if user is None:
            await interaction.edit_original_message("Please provide a user")
            return
        rrs_core: RRSCore = self.bot.get_cog("RRSCore")
        await rrs_core.sync_user(user, reason=f"Индивидуальная синхронизация")
        await interaction.edit_original_message(
            f"Синхронизация {user.mention} завершена"
        )

    @commands.slash_command(
        name="rrs-everyone-sync", guild_ids=[settings.DevServer.guild_id]
    )
    @commands.is_owner()
    async def rrs_everyone_sync_command(
        self, inter: ApplicationCommandInteraction, all_guilds: bool = False
    ):
        await inter.response.defer(ephemeral=True)

        status_embed = disnake.Embed(
            title=f"Синхронизация всех пользователей через RRS",
            color=disnake.Color.dark_green(),
        )
        plasmo_members = self.bot.get_guild(settings.PlasmoRPGuild.guild_id).members
        if all_guilds:
            guilds = await guilds_database.get_all_guilds()
            guilds = [self.bot.get_guild(guild.id) for guild in guilds]
            for guild in guilds:
                plasmo_members += guild.members
            plasmo_members = set(plasmo_members)

        rrs_core: RRSCore = self.bot.get_cog("RRSCore")

        lazy_update_members_count = len(plasmo_members) // 10
        for counter, member in enumerate(plasmo_members):
            status_embed.clear_fields()
            await rrs_core.sync_user(
                member,
                reason=f"Синхронизация всех игроков, вызвано {inter.author.display_name}",
            )
            status_embed.add_field(
                name=f"Прогресc",
                value=utils.build_progressbar(counter + 1, len(plasmo_members)),
            )

            if counter % lazy_update_members_count == 0:
                await inter.edit_original_message(embed=status_embed)
            continue

        status_embed.clear_fields()
        status_embed.add_field(
            name=f"Синхронизировано пользователей: {len(plasmo_members)}/{len(plasmo_members)}",
            value=utils.build_progressbar(1, 1),
            inline=False,
        )
        await inter.edit_original_message(embed=status_embed)

    @commands.slash_command(
        name="rrs-list",
        dm_permission=False,
    )
    @commands.default_member_permissions(manage_roles=True)
    async def get_registered_rrs_entries(self, inter: ApplicationCommandInteraction):
        """
        Get list of registered RRS entries
        """
        entries = await rrs_database.get_rrs_roles(
            structure_guild_id=inter.guild.id
            if inter.guild.id != settings.DevServer.guild_id
            else None
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
        name="rrs-add", dm_permission=False, guild_ids=[settings.DevServer.guild_id]
    )
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
        # todo: add confirmation

        entry = await rrs_database.register_rrs_role(
            structure_guild_id=int(sgid),
            structure_role_id=int(srid),
            plasmo_role_id=int(prid),
            disabled=disabled,
        )
        await inter.send(f"{entry.id} - registered", ephemeral=True)

    @commands.is_owner()
    @commands.command(name="rrs-add", hidden=True)
    async def register_rrs_entry_text_command(
        self,
        ctx: commands.Context,
        srid: str,
        prid: str,
    ):
        """
        Register RRS entry

        Parameters
        ----------
        srid: structure role id
        prid: plasmo role id
        """
        await ctx.message.delete()
        await rrs_database.register_rrs_role(
            structure_guild_id=ctx.guild.id,
            structure_role_id=int(srid),
            plasmo_role_id=int(prid),
        )

        await ctx.send("⚠ RRS rule was registered without verification ⚠")

    @commands.is_owner()
    @commands.slash_command(
        name="rrs-remove", dm_permission=False, guild_ids=[settings.DevServer.guild_id]
    )
    async def delete_rrs_entry(
        self,
        inter: ApplicationCommandInteraction,
        entry_id: int,
    ):
        """
        Delete RRS entry

        Parameters
        ----------
        entry_id: entry id
        """
        entry = await rrs_database.get_rrs_role(entry_id)
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
        name="rrs-edit", dm_permission=False, guild_ids=[settings.DevServer.guild_id]
    )
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
        entry_id: entry id
        disabled: is disabled
        structure_guild_id: structure guild id
        structure_role_id: structure role id
        plasmo_role_id: plasmo role id
        """
        entry = await rrs_database.get_rrs_role(entry_id)
        if entry is None:
            await inter.send("Entry not found", ephemeral=True)
            return

        await entry.edit(
            disabled=disabled,
            structure_guild_id=int(structure_guild_id) if structure_guild_id else None,
            structure_role_id=int(structure_role_id) if structure_role_id else None,
            plasmo_role_id=int(plasmo_role_id) if plasmo_role_id else None,
        )
        await inter.send(f"{entry.id} - edited", ephemeral=True)

    async def cog_load(self):
        logger.info("%s Ready", __name__)


def setup(client):
    """
    Internal disnake setup function
    """
    client.add_cog(RRSCommands(client))
