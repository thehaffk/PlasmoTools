import logging

import disnake
from disnake import ApplicationCommandInteraction
from disnake.ext import commands

from plasmotools import checks
from plasmotools.utils import models

logger = logging.getLogger(__name__)


# todo: Rewrite with buttons


class AdminCommands(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    @commands.is_owner()
    @commands.guild_only()
    @commands.slash_command(
        name="register-guild",
    )
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
        db_guild = await models.StructureGuild.objects.update_or_create(
            discord_id=inter.guild.id,
            defaults={
                "alias": alias,
                "player_role_id": player_role.id,
                "head_role_id": head_role.id,
                "public_chat_channel_id": public_chat.id,
                "logs_channel_id": logs_channel.id,
            }
        )
        await inter.send(
            embed=disnake.Embed(
                color=disnake.Color.dark_green(),
                title="Успех",
                description=f"Сервер {inter.guild.name} отредактирован в базе данных",
            ).add_field(
                name="guild data",
                value=f"""
            `alias`: {db_guild.alias}
            `player_role`: {db_guild.player_role_id}
            `head_role`: {db_guild.head_role_id}
            `public_chat`: {db_guild.public_chat_channel_id}
            `logs_channel`: {db_guild.logs_channel_id}
            """,
            ),
            ephemeral=True,
        )

    @commands.is_owner()
    @commands.guild_only()
    @commands.slash_command(
        name="wipe-guild",
    )
    @commands.default_member_permissions(administrator=True)
    async def wipe_guild(self, inter: ApplicationCommandInteraction):
        """
        Удалить сервер из базы данных
        """
        # todo: add confirmation
        # todo: send some kind of logs or smth

        await models.StructureGuild.objects.filter(discord_id=inter.guild.id).delete()
        await models.StructureProject.objects.filter(guild_discord_id=inter.guild.id).delete()
        await models.StructureRole.objects.filter(guild_discord_id=inter.guild.id).delete()

        await inter.send(
            embed=disnake.Embed(
                color=disnake.Color.dark_green(),
                title="Успех",
                description=f"Сервер {inter.guild.name} и все привязанные к нему проекты и роли "
                "удалены из базы данных",
            ),
            ephemeral=True,
        )

    @commands.guild_only()
    @commands.slash_command(
        name="get-guild-data",
    )
    @commands.default_member_permissions(administrator=True)
    @checks.blocked_users_slash_command_check()
    async def get_guild_data(self, inter: ApplicationCommandInteraction):
        """
        Получить данные о сервере
        """
        db_guild = await models.StructureGuild.objects.filter(discord_id=inter.guild.id).first()
        if db_guild is None:
            return await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.dark_red(),
                    title="Ошибка",
                    description="Сервер не зарегистрирован как официальная структура"
                ),
                ephemeral=True,
            )

        await inter.send(
            embed=disnake.Embed(
                color=disnake.Color.dark_green(),
                title=f"Данные о {inter.guild.name}",
            ).add_field(
                name="guild data",
                value=f"""
            `alias`: {db_guild.alias}
            `player_role`: <@&{db_guild.player_role_id}> / {db_guild.player_role_id} 
            `head_role`: <@&{db_guild.head_role_id}> / {db_guild.head_role_id} 
            `public_chat`: <#{db_guild.public_chat_channel_id}> / {db_guild.public_chat_channel_id} 
            `logs_channel`: <#{db_guild.logs_channel_id}> / {db_guild.logs_channel_id} 
            """,
            ),
            ephemeral=True,
        )


def setup(bot: disnake.ext.commands.Bot):
    """
    Disnake internal setup function
    """
    bot.add_cog(AdminCommands(bot))
