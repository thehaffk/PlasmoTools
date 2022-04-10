"""
Cog-file for synchronization nicknames and roles at BAC discord guild
"""
import asyncio
import logging
import disnake
from aiohttp import ClientSession
from disnake import HTTPException
from disnake.ext import commands

import settings

logger = logging.getLogger(__name__)


class BACSynchronization(commands.Cog):
    """
    Cog for synchronization nicknames and roles at BAC discord guild
    """

    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

        self.bac_guild: disnake.Guild = None
        self.bac_banned_role: disnake.Role = None
        self.bac_without_pass_role: disnake.Role = None
        self.bac_has_pass_role: disnake.Role = None

    async def sync(self, member: disnake.Member) -> bool:
        """
        Synchronizes given member

        :param member: member to sync
        :return: bool - success or failed
        """
        if member not in self.bac_guild.members or member.bot:
            return False
        logger.info(f"Syncing {member} ({member.display_name})")

        # TODO: Rewrite with plasmo.py
        user_data = None
        for tries in range(10):
            async with ClientSession() as session:
                async with session.get(
                    url=f"https://rp.plo.su/api/user/profile?discord_id={member.id}",
                ) as response:
                    if response.status != 200:
                        logger.warning("Could not get data from PRP API: %s", await response.json())
                        return False
                    try:
                        user_data = (await response.json())["data"]
                    except Exception as err:
                        logger.warning("Could not get data from PRP API: %s", err)
                        await asyncio.sleep(30)
                        continue

            break
        if user_data is None:
            return False

        is_banned: bool = user_data.get("banned", False)
        has_pass: bool = user_data.get("on_server", False)
        nickname: str = user_data.get("nick", "")
        bac_member: disnake.Member = self.bac_guild.get_member(member.id)

        try:
            await bac_member.edit(nick=nickname)
        except HTTPException:
            pass

        try:
            if has_pass:
                await bac_member.add_roles(self.bac_has_pass_role)
                await bac_member.remove_roles(self.bac_without_pass_role)
            else:
                await bac_member.add_roles(self.bac_without_pass_role)
                await bac_member.remove_roles(self.bac_has_pass_role)

            if is_banned:
                await bac_member.add_roles(self.bac_banned_role)
            else:
                await bac_member.remove_roles(self.bac_banned_role)

        except disnake.HTTPException as err:
            logger.warning(
                err,
            )
            return False
        await self.bot.get_cog("GCAMCSync").sync(bac_member)

        return True

    @commands.Cog.listener()
    async def on_member_update(
        self, before: disnake.Member, after: disnake.Member
    ) -> bool:
        """
        Discord event, called when member has been updated
        """
        if not before.guild.id == settings.PlasmoRPGuild.guild_id:
            return False
        if before.display_name != after.display_name or before.roles != after.roles:
            return await self.sync(after)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: disnake.Guild, member: disnake.Member):
        """
        Called on discord event when user is banned, sends user DM to join BAC guild
        """
        if not guild.id == settings.PlasmoRPGuild.guild_id:
            return False
        if member not in self.bac_guild.members or member.id == 737501414141591594:
            try:
                await member.send(
                    embed=disnake.Embed(
                        title="Вы были забанены на Plasmo RP",
                        color=disnake.Color.dark_red(),
                        description=f"Узнать причину бана, оспорить решение "
                        f"администрации или разбаниться можно "
                        f"только тут - {settings.BACGuild.invite_url}\n\n\n"
                        f"⚡ by [digital drugs]({settings.DevServer.invite_url})",
                    )
                )
                await member.send(
                    content=f"{settings.BACGuild.invite_url}",
                )
            except Exception as e:
                logger.warning(e)
                return False
        else:
            return await self.sync(member)

    @commands.Cog.listener()
    async def on_member_unban(
        self, guild: disnake.Guild, member: disnake.Member
    ) -> bool:
        """
        Called on discord event when user is unbanned, sends user DM to join PRP guild
        """
        if not guild.id == settings.PlasmoRPGuild.guild_id:
            return False
        try:
            await member.send(
                embed=disnake.Embed(
                    title="Вас разбанили на Plasmo RP",
                    color=disnake.Color.green(),
                    description=f"Держите инвайт и не забывайте соблюдать "
                    f"правила сервера {settings.PlasmoRPGuild.invite_url}\n\n\n"
                    f"⚡ by [digital drugs]({settings.DevServer.invite_url})",
                )
            )
            await member.send(
                content=f"{settings.PlasmoRPGuild.invite_url}",
            )
        except Exception as e:
            logger.warning(e)
            return False
        return await self.sync(member)

    @commands.Cog.listener()
    async def on_member_join(self, member: disnake.Member) -> bool:
        """
        Called on discord event when user join the guild, used for automatically sync user
        """
        if not member.guild.id == settings.BACGuild.guild_id:
            return False
        return await self.sync(member)

    @commands.slash_command(
        name="everyone-sync", guild_ids=[settings.BACGuild.guild_id]
    )
    @commands.has_permissions(manage_roles=True)
    async def everyone_sync(self, inter: disnake.ApplicationCommandInteraction):
        # Docstring is in russian because disnake automatically puts in slash-command description
        """
        Синхронизировать всех пользователей на сервере.
        """

        members = inter.guild.members

        embed_counter = disnake.Embed(
            title=("Синхронизация | " + str(inter.guild)), color=disnake.Color.yellow()
        )

        embed_counter.add_field(name="🔃 Синхронизация", value=f"0 / {len(members)}")

        await inter.response.send_message(embed=embed_counter, ephemeral=True)

        for counter, member in enumerate(members):
            embed_counter.clear_fields()
            embed_counter.add_field(
                name="🔃 Синхронизация", value=f"{counter} / {len(members)}\n {member}"
            )
            await inter.edit_original_message(embed=embed_counter)
            await self.sync(member)

        await inter.edit_original_message(
            embed=disnake.Embed(
                title="✅ Синхронизация завершена",
                description="Успешно",
                color=disnake.Color.dark_green(),
            )
        )

    @commands.slash_command(
        name="sync", guild_ids=[settings.BACGuild.guild_id], auto_sync=False
    )
    @commands.has_permissions(manage_roles=True)
    async def sync_user(
        self, inter: disnake.ApplicationCommandInteraction, user: disnake.Member
    ):
        # Docstring is in russian because disnake automatically puts in command description

        """
        Синхронизировать пользователя.

        Parameters
        ----------
        user: Пользователь которого нужно синхронизировать

        """

        await inter.response.send_message(
            embed=disnake.Embed(
                title=f"Синхронизация {user} | {inter.guild.name}",
                color=disnake.Color.yellow(),
            ),
            ephemeral=True,
        )
        if await self.sync(user):
            await inter.edit_original_message(
                embed=disnake.Embed(
                    title="✅ Синхронизация завершена",
                    description="Успешно",
                    color=disnake.Color.dark_green(),
                )
            )
            return True

        return False

    @disnake.ext.commands.user_command(
        name="Синхронизировать",
        default_permission=True,
        guild_ids=[settings.BACGuild.guild_id],
    )
    async def sync_button(
        self, inter: disnake.ApplicationCommandInteraction, user: disnake.Member
    ):
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
    async def on_ready(self):
        """
        Called when disnake bot object is ready
        """
        self.bac_guild: disnake.Guild = self.bot.get_guild(settings.BACGuild.guild_id)
        self.bac_has_pass_role: disnake.Role = self.bac_guild.get_role(
            settings.BACGuild.has_pass_role_id
        )
        self.bac_without_pass_role: disnake.Role = self.bac_guild.get_role(
            settings.BACGuild.without_pass_role_id
        )
        self.bac_banned_role: disnake.Role = self.bac_guild.get_role(
            settings.BACGuild.banned_role_id
        )

        logger.info("%s Ready", __name__)


def setup(client):
    """
    Disnake internal setup function
    """
    client.add_cog(BACSynchronization(client))
