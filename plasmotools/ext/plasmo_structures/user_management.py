import logging
from typing import Optional

import aiohttp
import disnake
from disnake import ApplicationCommandInteraction
from disnake.ext import commands

from plasmotools import settings
from plasmotools.utils.autocompleters import role_autocompleter
from plasmotools.utils.database import plasmo_structures as database

logger = logging.getLogger(__name__)


# TODO: Auto remove all roles, when user leaves plasmo rp


async def check_role(
    inter, guild: Optional[database.Guild], role: Optional[database.Role]
) -> bool:
    if guild is None:
        await inter.send(
            embed=disnake.Embed(
                color=disnake.Color.red(),
                title="Ошибка",
                description="Сервер не зарегистрирован как офицальная структура.\n"
                f"Если вы считаете что произошла ошибка - "
                f"обратитесь в [поддержку DDT]({settings.DevServer.support_invite})",
            ),
            ephemeral=True,
        )
        return False
    guild: database.Guild
    if role is None or role.guild_discord_id != guild.id:
        await inter.send(
            embed=disnake.Embed(
                color=disnake.Color.red(),
                title="Ошибка",
                description="Роль не найдена. Пожалуйста, выбирайте только из списка.",
            ),
            ephemeral=True,
        )
        return False
    role: database.Role
    if role.available is False:
        await inter.send(
            embed=disnake.Embed(
                color=disnake.Color.red(),
                title="Ошибка",
                description="Роль не доступна для выбора. ",
            ),
            ephemeral=True,
        )
        return False

    return True


class UserManagement(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    @commands.guild_only()
    @commands.slash_command(name="роли-список", dm_permission=False)
    @commands.default_member_permissions(administrator=True)
    async def roles_list(self, inter: ApplicationCommandInteraction):
        """
        Получить список ролей в сервере
        """
        roles = await database.get_roles(inter.guild.id)
        embed = disnake.Embed(
            color=disnake.Color.green(),
            title=f"Все роли {inter.guild.name}",
        )
        if len(roles) == 0:
            embed.add_field(
                name="Роли не найдены",
                value="Добавьте через `/роли-добавить`",
            )
        else:
            embed.add_field(
                name="Название роли",
                value="[Доступна ли роль] Пинг роли / Айди роли\nВебхук",
            )
            for role in roles:
                embed.add_field(
                    name=f"{role.name}",
                    value=f"{settings.Emojis.enabled if role.available else settings.Emojis.disabled} "
                    f"<@&{role.role_discord_id}> / `{role.role_discord_id}` \n ||{role.webhook_url}||",
                    inline=False,
                )

        await inter.send(embed=embed, ephemeral=True)

    @commands.guild_only()
    @commands.slash_command(name="роли-добавить", dm_permission=False)
    @commands.default_member_permissions(administrator=True)
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
        webhook_url: Ссылка на вебхук для отправки уведомлений (в формате https://discord.com/api/webhooks/...)
        available: Доступна ли роль для найма и снятия
        name: Название роли, например "Интерпол"

        """
        # TODO: Check webhook url with regex
        guild = await database.get_guild(inter.guild.id)
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

        if role.id == guild.player_role_id or role.id == guild.head_role_id:
            await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description="Эта роль не может быть закреплена как нанимаемая\n"
                    "Если вы считаете что это ошибка - обратитесь в "
                    f"[поддержку digital drugs technologies]{settings.DevServer.support_invite}",
                ),
                ephemeral=True,
            )
            return
        await inter.response.defer(ephemeral=True)
        db_role = await database.get_role(role.id)
        if db_role is not None:
            await db_role.edit(
                name=name,
                webhook_url=webhook_url,
                available=available,
            )
            await inter.edit_original_message(
                embed=disnake.Embed(
                    color=disnake.Color.green(),
                    title="Роль обновлена",
                    description=f"Роль `{name}` обновлена",
                ),
            )
        else:
            await database.add_role(
                guild_discord_id=inter.guild.id,
                role_discord_id=role.id,
                name=name,
                webhook_url=webhook_url,
                available=available,
            )
            await inter.edit_original_message(
                embed=disnake.Embed(
                    color=disnake.Color.green(),
                    title="Роль создана",
                    description=f"Роль `{name}` зарегистрирована",
                ),
            )

    @commands.guild_only()
    @commands.slash_command(name="роли-удалить", dm_permission=False)
    @commands.default_member_permissions(administrator=True)
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
    @commands.slash_command(name="роли-редактировать", dm_permission=False)
    @commands.default_member_permissions(administrator=True)
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
        webhook_url: Ссылка на вебхук для отправки уведомлений (https://discordapp.com/api/webhooks/{project_id}/{token})
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

    @commands.slash_command(name="нанять", dm_permission=False)
    @commands.guild_only()
    @commands.default_member_permissions(manage_roles=True)
    async def hire_user_command(
        self,
        inter: ApplicationCommandInteraction,
        user: disnake.Member,
        role: str = commands.Param(
            autocomplete=role_autocompleter,
        ),
        comment: Optional[str] = None,
    ):
        """
        Hire user.

        Parameters
        ----------
        user: Player
        role: Role [⚠ Choose from autocomplete!]
        comment: Comment for hiring

        """
        try:
            guild, db_role = await database.get_guild(
                inter.guild.id
            ), await database.get_role(role_discord_id=int(role))
        except ValueError:
            return await inter.send(
                "https://tenor.com/view/%D0%B2%D0%B4%D1%83%D1%80%D0%BA%D1%83"
                "-%D0%B4%D1%83%D1%80%D0%BA%D0%B0-%D0%BA%D0%BE%D1%82-%D0%BA%D0%BE%D1%82%D1%8D-gif-25825159",
                ephemeral=True,
            )
        if not await check_role(inter, guild, db_role):
            return
        plasmo_guild = self.bot.get_guild(settings.PlasmoRPGuild.guild_id)
        if plasmo_guild is None:
            raise RuntimeError("Plasmo RP guild not found")
        plasmo_user = plasmo_guild.get_member(user.id)
        if (
            user.bot
            or inter.guild.get_role(guild.player_role_id) not in user.roles
            or plasmo_user is None
        ):
            return await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Error",
                    description="You cannot hire this user.",
                ),
                ephemeral=True,
            )
        if db_role.role_discord_id in [role.id for role in user.roles]:
            return await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Error",
                    description=f"This user already has <@&{db_role.role_discord_id}> role.",
                ),
                ephemeral=True,
            )

        plasmo_user: disnake.Member
        await inter.response.defer(ephemeral=True)
        embed = disnake.Embed(
            color=disnake.Color.green(),
            description=f"{user.mention} был принят на должность **{db_role.name}**",
        ).set_author(
            name=plasmo_user.display_name,
            icon_url="https://rp.plo.su/avatar/" + plasmo_user.display_name,
        )
        if comment is not None:
            embed.add_field(name="Комментарий", value=comment)

        try:
            await user.add_roles(
                inter.guild.get_role(db_role.role_discord_id),
                reason=f"Hired " f"[by {inter.author.display_name} / {inter.author} / {inter.author.id}]",
            )
        except disnake.Forbidden:
            return await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Error",
                    description="Unable to fire this user. Bot has no permissions to add this role.",
                ),
                ephemeral=True,
            )

        async with aiohttp.ClientSession() as session:
            webhook = disnake.Webhook.from_url(db_role.webhook_url, session=session)
            try:
                await webhook.send(
                    content=user.mention,
                    embed=embed,
                )
            except disnake.errors.NotFound:
                await user.remove_roles(
                    inter.guild.get_role(db_role.role_discord_id),
                    reason=f"Unexpected error",
                )
                return await inter.edit_original_message(
                    embed=disnake.Embed(
                        color=disnake.Color.red(),
                        title="Error",
                        description="Unable to access webhook.",
                    ),
                )

        await self.bot.get_channel(guild.logs_channel_id).send(
            embed=embed.add_field("Called by", inter.author.mention)
        )

        await inter.edit_original_message(
            embed=disnake.Embed(
                color=disnake.Color.green(),
                title="Done",
                description="User was successfully hired.",
            ),
        )

    @commands.slash_command(name="уволить", dm_permission=False)
    @commands.guild_only()
    @commands.default_member_permissions(manage_roles=True)
    async def fire_user_command(
        self,
        inter: ApplicationCommandInteraction,
        user: disnake.Member,
        role: str = commands.Param(autocomplete=role_autocompleter),
        reason: Optional[str] = None,
    ):
        """
        Fire user.

        Parameters
        ----------
        reason: Reason
        user: Player
        role: Role [⚠ Choose from autocomplete!]
        """
        try:
            guild, db_role = await database.get_guild(
                inter.guild.id
            ), await database.get_role(role_discord_id=int(role))
        except ValueError:
            return await inter.send(
                "https://tenor.com/view/%D0%B2%D0%B4%D1%83%D1%80%D0%BA%D1%83"
                "-%D0%B4%D1%83%D1%80%D0%BA%D0%B0-%D0%BA%D0%BE%D1%82-%D0%BA%D0%BE%D1%82%D1%8D"
                "-gif-25825159",
                ephemeral=True,
            )
        if not await check_role(inter, guild, db_role):
            return
        plasmo_guild = self.bot.get_guild(settings.PlasmoRPGuild.guild_id)
        if plasmo_guild is None:
            raise RuntimeError("Plasmo RP guild not found")
        plasmo_user = plasmo_guild.get_member(user.id)
        if (
            user.bot
            or inter.guild.get_role(guild.player_role_id) not in user.roles
            or plasmo_user is None
        ):
            return await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Error",
                    description="You cant fire this user.",
                ),
                ephemeral=True,
            )
        if db_role.role_discord_id not in [role.id for role in user.roles]:
            return await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Error",
                    description=f"User does not have <@&{db_role.role_discord_id}> role.",
                ),
                ephemeral=True,
            )

        plasmo_user: disnake.Member
        await inter.response.defer(ephemeral=True)
        embed = disnake.Embed(
            color=disnake.Color.dark_red(),
            description=f"{user.mention} был уволен с должности **{db_role.name}**",
        ).set_author(
            name=plasmo_user.display_name,
            icon_url="https://rp.plo.su/avatar/" + plasmo_user.display_name,
        )
        if reason is not None:
            embed.add_field(name="Причина", value=reason)

        try:
            await user.remove_roles(
                inter.guild.get_role(db_role.role_discord_id),
                reason=f"Fired " f"[by {inter.author.display_name} / {inter.author} / {inter.author.id}]",
            )
        except disnake.Forbidden:
            return await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Error",
                    description="Unable to fire this user. Bot has no permissions to remove this role.",
                ),
                ephemeral=True,
            )
        async with aiohttp.ClientSession() as session:
            webhook = disnake.Webhook.from_url(db_role.webhook_url, session=session)
            try:
                await webhook.send(
                    content=user.mention,
                    embed=embed,
                )
            except disnake.errors.NotFound:
                await user.add_roles(
                    inter.guild.get_role(db_role.role_discord_id),
                    reason=f"Unexpected error",
                )
                return await inter.edit_original_message(
                    embed=disnake.Embed(
                        color=disnake.Color.red(),
                        title="Error",
                        description="Unable to access webhook.",
                    ),
                )

        await self.bot.get_channel(guild.logs_channel_id).send(
            embed=embed.add_field("Called by", inter.author.mention)
        )

        await inter.edit_original_message(
            embed=disnake.Embed(
                color=disnake.Color.green(),
                title="Done",
                description="The user was successfully fired.",
            ),
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
    bot.add_cog(UserManagement(bot))
