"""
Cog-file for synchronization nicknames and roles at BAC discord guild
"""
import asyncio
import logging

import aiomysql
import disnake
import pymysql
from aiohttp import ClientSession
from disnake.ext import commands

import settings

logger = logging.getLogger(__name__)


# TODO: Create auto-schedule


class GCAMCSync(commands.Cog):
    """
    Cog for GCA(Grand Court of Appeal) minecraft synchronization
    """

    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot
        # Guilds
        self.bac_guild: disnake.Guild = self.bot.get_guild(settings.BACGuild.guild_id)

        # Channels
        self.dev_logs_channel: disnake.TextChannel = self.bac_guild.get_channel(
            settings.BACGuild.dev_logs_channel_id
        )
        self.mc_logs_channel: disnake.TextChannel = self.bac_guild.get_channel(
            settings.BACGuild.mc_logs_channel_id
        )

        # Roles
        self.defendant_role = self.bac_guild.get_role(
            settings.BACGuild.defendant_role_id
        )
        self.juror_role = self.bac_guild.get_role(settings.BACGuild.juror_role_id)
        self.bac_has_pass_role: disnake.Role = self.bac_guild.get_role(
            settings.BACGuild.has_pass_role_id
        )
        self.bac_banned_role: disnake.Role = self.bac_guild.get_role(
            settings.BACGuild.banned_role_id
        )
        self.conn = None
        self.cursor: aiomysql.Cursor = None

    async def sync(self, member: disnake.Member, uuid=None) -> bool:
        """
        Synchronizes given member with mc db

        :param member: member to sync
        :param uuid:
        :return: bool - success or failed
        """
        permissions = {
            settings.BACGuild.banned_role_id: "group.banned",
            settings.BACGuild.juror_role_id: "group.jury",
            settings.BACGuild.has_pass_role_id: "group.player",
            settings.BACGuild.culture_member_role_id: "group.culture",
        }

        # Get user uuid from PRP API if method called from button/GCAMCSync.on_member_update
        if uuid is None:
            # TODO: Rewrite with plasmo.py
            for _ in range(10):
                async with ClientSession() as session:
                    async with session.get(
                            url=f"https://rp.plo.su/api/user/profile?discord_id={member.id}",
                    ) as response:

                        response_json = await response.json()

                        if response.status != 200:
                            logger.warning(
                                "Could not get data from PRP API: %s",
                                await response_json,
                            )
                            return False
                        status = response_json.get("status")
                        user_data = response_json.get("data", None)

                        if not status:
                            logger.warning(
                                "Could not get data from PRP API: %s",
                                response_json,
                            )
                            return False

                        if user_data is None:
                            logger.warning(
                                "Could not get data from PRP API: \n %s \n %s",
                                response.status,
                                await response.text(),
                            )
                            await asyncio.sleep(10)
                            continue

            uuid: str = user_data.get("uuid", None)
        # APi responded with error (most likely user not found or cloudflare error)
        if uuid is None:
            logger.warning(
                "Could not get UUID from PRP API nick=%s discord_id=%s",
                member.display_name,
                member.id,
            )
            return False

        mc_groups = []
        for role in member.roles:
            if role.id in permissions:
                mc_groups.append(permissions[role.id])

        try:
            await self.cursor.execute(
                query="SELECT permission FROM luckperms_user_permissions WHERE uuid = %s AND permission LIKE %s",
                args=(uuid, "group.%"),
            )
            mc_actual_groups_tuple = await self.cursor.fetchall()
            mc_actual_groups = []
            for group in mc_actual_groups_tuple:
                group = group[0]
                if group not in permissions.values():
                    continue

                mc_actual_groups.append(group)

            # Remove group from mc
            for group in set(mc_actual_groups) - set(mc_groups):
                logger.info(f"Removing {group} from {member.display_name} [{uuid}]")
                await self.mc_logs_channel.send(
                    f"[{__name__}/INFO]: Removing {group} from {member.display_name} [{uuid}]"
                )
                await self.cursor.execute(
                    query="DELETE FROM luckperms_user_permissions "
                          "WHERE uuid = %s AND permission = %s",
                    args=(uuid, group),
                )
                f"[{__name__}/INFO]: Removed {group} from {member.display_name} [{uuid}]"

            # Add group to mc
            for group in set(mc_groups) - set(mc_actual_groups):
                logger.info(f"Adding {group} to {member.display_name} [{uuid}]")
                await self.mc_logs_channel.send(
                    f"[{__name__}/INFO]: Adding {group} to {member.display_name} [{uuid}]"
                )
                await self.cursor.execute(
                    query="INSERT INTO "
                          "luckperms_user_permissions(uuid, permission, value, server, world, expiry, contexts) "
                          "VALUES (%s, %s, 1, 'global', 'global', 0, '{}')",
                    args=(uuid, group),
                )

            await self.cursor.execute(
                query="SELECT permission FROM luckperms_user_permissions WHERE uuid = %s AND permission LIKE %s",
                args=(uuid, "group.%"),
            )
        except pymysql.err.OperationalError as error:
            logging.warning("Error whilst querying database %s", error)
            await self.update_db_connection()
            await self.sync(member=member, uuid=uuid)

    @commands.user_command(
        name="MC Sync",
        default_permission=True,
        guild_ids=[settings.BACGuild.guild_id],
    )
    async def force_sync_button(self, inter, user: disnake.Member):
        """
        Button that appears when you click on a member in Discord
        """
        await inter.response.defer(ephemeral=True)
        await self.sync(user)
        embed_counter = disnake.Embed(
            title=(f"Синхронизировал {user} | " + str(inter.guild))
        )

        await inter.edit_original_message(embed=embed_counter)

    @commands.Cog.listener()
    async def on_member_update(
            self, before: disnake.Member, after: disnake.Member
    ) -> bool:
        """
        Discord event, called when member has been updated
        """
        if not before.guild.id == settings.BACGuild.guild_id:
            return False
        if before.roles != after.roles:
            return await self.sync(after)

    async def update_db_connection(self):
        """
        Updates connection to plasmo database
        """
        logger.info("Updating database connection")
        self.conn = await aiomysql.connect(
            host=settings.DBConfig.ip,
            port=settings.DBConfig.port,
            user=settings.DBConfig.user,
            password=settings.DBConfig.password,
            db="plasmo_rp_off",
            autocommit=True,
        )
        self.cursor = await self.conn.cursor()

    async def cog_load(self):
        """
        Called when disnake bot object is ready
        """
        await self.update_db_connection()

        logger.info("%s Ready", __name__)


def setup(client):
    """
    Disnake internal setup function
    """
    client.add_cog(GCAMCSync(client))
