import logging

import disnake
from disnake import ApplicationCommandInteraction
from disnake.ext import tasks, commands

from plasmotools import settings
from plasmotools.utils.database import rrs as rrs_database
from plasmotools.utils.database.plasmo_structures import guilds as guilds_database

logger = logging.getLogger(__name__)


class RRSCommands(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    @commands.is_owner()
    @commands.slash_command(name="rrs-list", dm_permission=False, guild_ids=[settings.DevServer.guild_id])
    async def get_registered_rrs_entries(self, inter: ApplicationCommandInteraction):
        """
        Get list of registered RRS entries
        """
        entries = await rrs_database.get_rrs_roles()
        roles_text = "id - disabled - sgid - srid - prid:\n"
        for entry in entries:
            roles_text += f"{entry.id} - {entry.disabled} - SGID {entry.structure_guild_id} " \
                          f"- SRID {entry.structure_role_id} - PRID {entry.plasmo_role_id}\n"

        await inter.send(roles_text, ephemeral=True)

    @commands.is_owner()
    @commands.slash_command(name="rrs-add", dm_permission=False, guild_ids=[settings.DevServer.guild_id])
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
        guild = await guilds_database.get_guild(int(sgid))
        if guild is None:
            await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description="Сервер не зарегистрирован как офицальная структура.\n"
                                "Если вы считаете что это ошибка - обратитесь в "
                                f"[поддержку digital drugs technologies]({settings.DevServer.support_invite})",
                ),
                ephemeral=True,
            )
            return

        entry = await rrs_database.register_rrs_role(
            structure_guild_id=int(sgid),
            structure_role_id=int(srid),
            plasmo_role_id=int(prid),
            disabled=disabled,
        )
        await inter.send(f"{entry.id} - registered", ephemeral=True)

    @commands.is_owner()
    @commands.slash_command(name="rrs-remove", dm_permission=False, guild_ids=[settings.DevServer.guild_id])
    async def delete_rrs_entry(
            self,
            inter: ApplicationCommandInteraction,
            id: int,
    ):
        """
        Delete RRS entry

        Parameters
        ----------
        id: entry id
        """
        entry = await rrs_database.get_rrs_role(id)
        if entry is None:
            await inter.send("Entry not found", ephemeral=True)
            return

        data_string = f"{entry.id} - {entry.disabled} - SGID {entry.structure_guild_id} " \
                      f"- SRID {entry.structure_role_id} - PRID {entry.plasmo_role_id}"
        await entry.delete()
        await inter.send(f"{data_string} - deleted", ephemeral=True)

    @commands.is_owner()
    @commands.slash_command(name="rrs-edit", dm_permission=False, guild_ids=[settings.DevServer.guild_id])
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
