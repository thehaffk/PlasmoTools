import logging

import disnake
from disnake import ApplicationCommandInteraction
from disnake.ext import commands

from plasmotools import settings
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
        guild: database.Guild = await database.get_guild(inter.guild.id)
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
        guild: database.Guild = await database.register_guild(
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
                description=f"Сервер {inter.guild.name} зарегистрирован как офицальная структура.",
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
    async def wipe_guild(self, inter: ApplicationCommandInteraction):
        """
        Удалить сервер из базы данных
        """
        guild = await database.get_guild(inter.guild.id)
        if guild is None:
            await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description="Сервер не зарегистрирован как офицальная структура.\n",
                ),
                ephemeral=True,
            )
            return

        projects = await database.get_projects(guild.id)
        roles = await database.get_roles(guild.id)
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
    async def get_guild_data(self, inter: ApplicationCommandInteraction):
        """
        Получить данные о сервере
        """
        guild = await database.get_guild(inter.guild.id)
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
                description=f"Сервер {inter.guild.name} зарегистрирован как офицальная структура.",
            ).add_field(
                name="guild data",
                value=f"""
            `alias`: {guild.alias}
            `player_role`: <@&{guild.player_role_id}> / {guild.player_role_id} 
            `head_role`: <@&{guild.head_role_id}> /{guild.head_role_id} 
            `public_chat`: <#{guild.public_chat_channel_id}> /{guild.public_chat_channel_id} 
            `logs_channel`: <#{guild.logs_channel_id}> /{guild.logs_channel_id} 
            """,
            ),
            ephemeral=True,
        )

    @commands.guild_only()
    @commands.default_member_permissions(administrator=True)
    @commands.slash_command(name="роли")
    async def roles_placeholder(self, inter: ApplicationCommandInteraction):
        ...

    @commands.guild_only()
    @roles_placeholder.sub_command(name="список")
    async def roles_list(self, inter: ApplicationCommandInteraction):
        """
        Получить список ролей в сервере
        """
        roles = await database.get_roles(inter.guild.id)
        embed = disnake.Embed(
            color=disnake.Color.green(),
            title=f"Все роли {inter.guild.name}",
        )
        for role in roles:
            embed.add_field(
                name=f"{role.name}",
                value=f"{settings.Emojis.enabled if role.available else settings.Emojis.disabled} "
                      f"<@&{role.role_discord_id}> / {role.role_discord_id} \n ||{role.webhook_url}||",
                inline=False,
            )

        await inter.send(embed=embed, ephemeral=True)

    @commands.guild_only()
    @roles_placeholder.sub_command(name="добавить")
    async def roles_add(
            self,
            inter: ApplicationCommandInteraction,
            role: disnake.Role,
            name: str,
            webhook_url: str,
            available: bool = True,
    ):
        """
        Добавить роль в базу данных

        Parameters
        ----------
        role: Роль
        webhook_url: Ссылка на вебхук для отправки уведомлений (https://discordapp.com/api/webhooks/{id}/{token})
        available: Доступна ли роль для найма и снятия
        name: Название роли, например "Интерпол"

        """
        guild = await database.get_guild(inter.guild.id)
        if guild is None:
            await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description="Сервер не зарегистрирован как офицальная структура.\n"
                                "Если вы считаете что это ошибка - обратитесь в "
                                f"[поддержку digital drugs technologies]({settings.DevServer.invite_url})",
                ),
                ephemeral=True,
            )
            return

        if role.id == guild.player_role_id or role.id == guild.head_role_id:
            await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description="Эта роль не может быть закреплена как нанимаемая\n"
                                "Если вы считаете что это ошибка - обратитесь в "
                                f"[поддержку digital drugs technologies]{settings.DevServer.invite_url}",
                ),
                ephemeral=True,
            )
            return

        db_role = await database.get_role(role.id)
        if db_role is not None:
            await db_role.edit(
                name=name,
                webhook_url=webhook_url,
                available=available,
            )
        else:
            await database.add_role(
                guild_discord_id=inter.guild.id,
                role_discord_id=role.id,
                name=name,
                webhook_url=webhook_url,
                available=available,
            )

    @commands.guild_only()
    @roles_placeholder.sub_command(name="удалить")
    async def roles_delete(
            self,
            inter: ApplicationCommandInteraction,
            role: disnake.Role,
    ):
        """
        Удалить роль из базы данных
        """
        db_role = await database.get_role(role.id)
        if db_role is None:
            await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description="Роль не найдена в базе данных",
                ),
                ephemeral=True,
            )
            return
        await db_role.delete()

        await inter.send(
            embed=disnake.Embed(
                color=disnake.Color.green(),
                title="Роль удалена",
            ),
            ephemeral=True,
        )

    @commands.guild_only()
    @roles_placeholder.sub_command(name="редактировать")
    async def roles_edit(
            self,
            inter: ApplicationCommandInteraction,
            role: disnake.Role,
            name: str = None,
            webhook_url: str = None,
            available: bool = None,
    ):
        """
        Редактировать роль в базе данных

        Parameters
        ----------
        role: Роль
        webhook_url: Ссылка на вебхук для отправки уведомлений (https://discordapp.com/api/webhooks/{id}/{token})
        available: Доступна ли роль для найма и снятия
        name: Название роли, например "Интерпол"

        """
        db_role = await database.get_role(role.id)
        if db_role is None:
            await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description="Роль не найдена в базе данных",
                ),
                ephemeral=True,
            )
            return
        await db_role.edit(
            name=name,
            webhook_url=webhook_url,
            available=available,
        )

        await inter.send(
            embed=disnake.Embed(
                color=disnake.Color.green(),
                title="Роль отредактирована",
            ),
            ephemeral=True,
        )

    async def cog_load(self):
        """
        Called when disnake bot object is ready
        """

        logger.info("%s Ready", __name__)


def setup(bot: disnake.ext.commands.Bot):
    """
    Disnake internal setup function
    """
    bot.add_cog(AdminCommands(bot))
