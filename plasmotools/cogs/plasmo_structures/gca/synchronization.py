import logging

import disnake
from disnake import HTTPException
from disnake.ext import commands, tasks

from plasmotools import checks, formatters, plasmo_api, settings
from plasmotools.embeds import build_simple_embed

logger = logging.getLogger(__name__)


class BACSynchronization(commands.Cog):
    """
    Cog for synchronization nicknames and roles at BAC discord guild
    """

    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    async def _sync(self, user: disnake.User | disnake.Member) -> bool:
        """
        Synchronize given member
        """
        gca_guild = self.bot.get_guild(settings.GCAGuild.guild_id)
        member = gca_guild.get_member(user.id)
        if member is None or member.bot:
            return False

        logger.debug("Syncing %s (%s)", member, member.display_name)

        plasmo_guild = self.bot.get_guild(settings.PlasmoRPGuild.guild_id)
        plasmo_member = plasmo_guild.get_member(user.id)
        if plasmo_member:
            user_data = {
                "banned": False,
                "has_access": plasmo_guild.get_role(
                    settings.PlasmoRPGuild.player_role_id
                )
                in plasmo_member.roles
                or plasmo_guild.get_role(settings.PlasmoRPGuild.new_player_role_id)
                in plasmo_member.roles,
                "nick": plasmo_member.display_name,
            }
        else:
            user_data = await plasmo_api.user.get_user_data(discord_id=member.id)

            if user_data is None:
                return False

        is_banned: bool = user_data.get("banned", False)
        has_pass: bool = user_data.get("has_access", False)
        nickname: str = user_data.get("nick", "")

        has_pass_role: disnake.Role = gca_guild.get_role(
            settings.GCAGuild.has_pass_role_id
        )
        without_pass_role: disnake.Role = gca_guild.get_role(
            settings.GCAGuild.without_pass_role_id
        )
        banned_role: disnake.Role = gca_guild.get_role(settings.GCAGuild.banned_role_id)

        if member.display_name != nickname:
            try:
                await member.edit(nick=nickname)
            except HTTPException:
                pass

        await member.add_roles(
            has_pass_role if has_pass else without_pass_role,
            reason="GCA Sync | RRSNR",
            atomic=False,
        )
        await member.remove_roles(
            without_pass_role if has_pass else has_pass_role,
            reason="GCA Sync | RRSNR",
            atomic=False,
        )

        if is_banned:
            await member.add_roles(banned_role, reason="GCA Sync | RRSNR", atomic=False)
        else:
            await member.remove_roles(
                banned_role, reason="GCA Sync | RRSNR", atomic=False
            )

        return True

    # Plasmo Sync is now in charge of handling nick changes

    @commands.Cog.listener()  # todo: move somewhere else
    async def on_member_ban(self, guild: disnake.Guild, member: disnake.Member):
        if guild.id != settings.PlasmoRPGuild.guild_id:
            return

        try:
            await member.send(
                "https://media.discordapp.net/"
                "attachments/899202029656895518/971525622297931806/ezgif-7-17469e0166d2.gif"
            )
            await member.send(
                embed=disnake.Embed(
                    title="Вас забанили на Plasmo RP",
                    color=disnake.Color.dark_red(),
                    description=f"Узнать причину бана, оспорить решение "
                    f"администрации или разбаниться можно "
                    f"только тут - {settings.GCAGuild.invite_url}\n\n\n"
                    f"⚡ by [digital drugs]({settings.LogsServer.invite_url})",
                )
            )
            await member.send(
                content=f"{settings.GCAGuild.invite_url}",
            )
        except HTTPException as err:
            logger.warning(err)

        await self._sync(member)

    @commands.Cog.listener()
    async def on_member_unban(
        self, guild: disnake.Guild, member: disnake.Member
    ) -> bool:
        if guild.id != settings.PlasmoRPGuild.guild_id:
            return False

        try:
            await member.send(settings.Gifs.est_slova)
            await member.send(
                embed=disnake.Embed(
                    title="Вас разбанили на Plasmo RP",
                    color=disnake.Color.dark_green(),
                    description=f"Держите инвайт и не забывайте соблюдать "
                    f"правила сервера {settings.PlasmoRPGuild.invite_url}\n\n\n"
                    f"⚡ by [digital drugs]({settings.LogsServer.invite_url})",
                )
            )
            await member.send(
                content=f"{settings.PlasmoRPGuild.invite_url}",
            )
        except HTTPException as err:
            logger.warning(err)
            return False
        return await self._sync(member)

    @commands.Cog.listener()
    async def on_member_join(self, member: disnake.Member):
        if member.guild.id == settings.GCAGuild.guild_id:
            await self._sync(member)

    @commands.slash_command(
        name="everyone-sync",
        guild_ids=[settings.GCAGuild.guild_id],
    )
    @checks.blocked_users_slash_command_check()
    @commands.has_permissions(manage_roles=True)
    async def everyone_sync(self, inter: disnake.ApplicationCommandInteraction):
        """
        Синхронизировать всех пользователей на сервере. {{EVERYONE_SYNC}}
        """

        members = inter.guild.members

        embed_counter = disnake.Embed(
            title=("Синхронизация | " + str(inter.guild)), color=disnake.Color.yellow()
        )

        progress_bar = f'[{"-" * 30}]'
        embed_counter.add_field(
            name="🔃 Синхронизация", value=f"0 / {len(members)}\n{progress_bar}"
        )

        await inter.response.send_message(embed=embed_counter, ephemeral=True)

        lazy_update_members_count = inter.guild.member_count // 10
        for counter, member in enumerate(members):
            embed_counter.clear_fields()
            if not member.bot:
                await self._sync(member)
            embed_counter.add_field(
                name="Прогресс...",
                value=formatters.build_progressbar(counter + 1, len(members)),
            )

            if counter % lazy_update_members_count == 0:
                await inter.edit_original_message(embed=embed_counter)

        embed_counter.clear_fields()
        embed_counter.add_field(
            name=f"Синхронизировано пользователей: {len(members)}/{len(members)}",
            value=formatters.build_progressbar(1, 1),
            inline=False,
        )
        await inter.edit_original_message(embed=embed_counter)

    @commands.slash_command(
        name="sync", guild_ids=[settings.GCAGuild.guild_id], dm_permission=False
    )
    @checks.blocked_users_slash_command_check()
    @commands.has_permissions(manage_roles=True)
    async def sync_user(
        self, inter: disnake.ApplicationCommandInteraction, user: disnake.Member
    ):
        """# todo: localization
        Синхронизировать пользователя.

        Parameters
        ----------
        inter
        user: Пользователь которого нужно синхронизировать

        """

        await inter.response.send_message(
            embed=disnake.Embed(
                title=f"Синхронизация {user} | {inter.guild.name}",
                color=disnake.Color.yellow(),
            ),
            ephemeral=True,
        )
        if await self._sync(user):
            await inter.edit_original_message(
                embed=build_simple_embed(
                    "Синхронизация завершена",
                )
            )
            return True

        return False

    @disnake.ext.commands.user_command(
        name="Sync",
        guild_ids=[settings.GCAGuild.guild_id],
    )
    async def sync_button(
        self, inter: disnake.ApplicationCommandInteraction, user: disnake.Member
    ):
        """
        Button that appears when you click on a member
        """
        await inter.response.defer(ephemeral=True)
        await self._sync(user)
        embed_counter = disnake.Embed(
            title=(f"Синхронизировал {user} | " + str(inter.guild)),
            color=disnake.Color.dark_green(),
        )

        await inter.edit_original_message(embed=embed_counter)

    @tasks.loop(hours=12)
    async def everyone_sync_task(self):
        gca_guild = self.bot.get_guild(settings.GCAGuild.guild_id)
        for member in gca_guild.members:
            await self._sync(member)

    @everyone_sync_task.before_loop
    async def before_everyone_sync_task(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.everyone_sync_task.is_running() and not settings.DEBUG:
            self.everyone_sync_task.start()

    async def cog_load(self):
        logger.info("%s loaded", __name__)


def setup(client):
    """
    Disnake internal setup function
    """
    client.add_cog(BACSynchronization(client))
