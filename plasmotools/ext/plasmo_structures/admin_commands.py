import logging

import disnake
from disnake import ApplicationCommandInteraction
from disnake.ext import commands

from plasmotools import checks
from plasmotools.utils.database import plasmo_structures as database

logger = logging.getLogger(__name__)


# todo: Rewrite with buttons


class AdminCommands(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    @commands.is_owner()
    @commands.guild_only()
    @commands.slash_command()
    @commands.default_member_permissions(administrator=True)
    @checks.blocked_users_slash_command_check()
    async def register_guild(
        self,
        inter: ApplicationCommandInteraction,
        alias: str,
        player_role: disnake.Role,
        head_role: disnake.Role,
        public_chat: disnake.TextChannel,
        logs_channel: disnake.TextChannel,
    ):
        """
        Регистрация/редактирование сервера в базе данных
        """
        guild: database.guilds.Guild = await database.guilds.get_guild(inter.guild.id)
        if guild is not None:
            embed = disnake.Embed(
                title="GUILD CHANGELOG",
                description=f"""
                `alias`: {guild.alias} -> {alias}
                `player_role`: {guild.player_role_id} -> {player_role.name}
                `head_role`: {guild.head_role_id} -> {head_role.name}
                `public_chat`: {guild.public_chat_channel_id} -> {public_chat.name}
                `logs_channel`: {guild.logs_channel_id} -> {logs_channel.name}
                """,
                color=disnake.Color.green(),
            )
            await inter.send(embed=embed, ephemeral=True)
        guild: database.guilds.Guild = await database.guilds.register_guild(
            discord_id=inter.guild.id,
            alias=alias,
            player_role_id=player_role.id,
            head_role_id=head_role.id,
            public_chat_channel_id=public_chat.id,
            logs_channel_id=logs_channel.id,
        )
        await inter.send(
            embed=disnake.Embed(
                color=disnake.Color.green(),
                title="Успех",
                description=f"Сервер {inter.guild.name} зарегистрирован как официальная структура.",
            ).add_field(
                name="guild data",
                value=f"""
            `alias`: {guild.alias}
            `player_role`: {guild.player_role_id}
            `head_role`: {guild.head_role_id}
            `public_chat`: {guild.public_chat_channel_id}
            `logs_channel`: {guild.logs_channel_id}
            """,
            ),
            ephemeral=True,
        )

    @commands.is_owner()
    @commands.guild_only()
    @commands.slash_command()
    @commands.default_member_permissions(administrator=True)
    @checks.blocked_users_slash_command_check()
    async def wipe_guild(self, inter: ApplicationCommandInteraction):
        """
        Удалить сервер из базы данных
        """
        guild = await database.guilds.get_guild(inter.guild.id)
        if guild is None:
            await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description="Сервер не зарегистрирован как официальная структура.\n",
                ),
                ephemeral=True,
            )
            return

        projects = await database.projects.get_projects(guild.id)
        roles = await database.roles.get_roles(guild.id)
        [await project.delete() for project in projects]
        [await role.delete() for role in roles]
        await guild.delete()
        await inter.send(
            embed=disnake.Embed(
                color=disnake.Color.green(),
                title="Успех",
                description=f"Сервер {inter.guild.name} и все привязанные к нему проекты и роли "
                f"удалены из БД **PlasmoTools.**",
            ),
            ephemeral=True,
        )

    @commands.guild_only()
    @commands.slash_command()
    @commands.default_member_permissions(administrator=True)
    @checks.blocked_users_slash_command_check()
    async def get_guild_data(self, inter: ApplicationCommandInteraction):
        """
        Получить данные о сервере
        """
        guild = await database.guilds.get_guild(inter.guild.id)
        if guild is None:
            await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description="404, Not Found",
                ),
                ephemeral=True,
            )
            return
        await inter.send(
            embed=disnake.Embed(
                color=disnake.Color.green(),
                title="Успех",
                description=f"Сервер {inter.guild.name} зарегистрирован как официальная структура.",
            ).add_field(
                name="guild data",
                value=f"""
            `alias`: {guild.alias}
            `player_role`: <@&{guild.player_role_id}> / {guild.player_role_id} 
            `head_role`: <@&{guild.head_role_id}> / {guild.head_role_id} 
            `public_chat`: <#{guild.public_chat_channel_id}> / {guild.public_chat_channel_id} 
            `logs_channel`: <#{guild.logs_channel_id}> / {guild.logs_channel_id} 
            """,
            ),
            ephemeral=True,
        )


def setup(bot: disnake.ext.commands.Bot):
    """
    Disnake internal setup function
    """
    bot.add_cog(AdminCommands(bot))
