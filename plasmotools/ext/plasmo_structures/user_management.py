import asyncio
import logging
from typing import Optional

import aiohttp
import disnake
from disnake import ApplicationCommandInteraction, Webhook, Localized
from disnake.ext import commands

from plasmotools import settings
from plasmotools.ext.error_handler import GuildIsNotRegistered
from plasmotools.ext.reverse_role_sync import core
from plasmotools.utils.autocompleters import role_autocompleter
from plasmotools.utils.database import plasmo_structures as database

logger = logging.getLogger(__name__)


# TODO: Auto remove all roles, when user leaves plasmo rp


def is_guild_registered():
    async def predicate(inter):
        if (await database.get_guild(inter.guild.id)) is None:
            raise GuildIsNotRegistered()
        return True

    return commands.check(predicate)


async def check_role(
    inter, guild: database.Guild, role: Optional[database.Role]
) -> bool:
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
    @is_guild_registered()
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
    @is_guild_registered()
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

        guild = await database.get_guild(inter.guild.id)
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
        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url(webhook_url, session=session)
            if webhook is None:
                await inter.send(
                    embed=disnake.Embed(
                        color=disnake.Color.red(),
                        title="Ошибка",
                        description="Не удалось получить вебхук. Проверьте правильность ссылки.",
                    ),
                    ephemeral=True,
                )
                return
            elif webhook.guild_id != inter.guild.id:
                await inter.send(
                    embed=disnake.Embed(
                        color=disnake.Color.red(),
                        title="Ошибка",
                        description="Вебхук не принадлежит этому серверу.",
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
    @is_guild_registered()
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
        if db_role.guild_discord_id != inter.guild.id:
            await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description="Роль не приналежит этому серверу",
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
    @is_guild_registered()
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
        webhook_url: Ссылка на вебхук для отправки уведомлений (https://discord.com/api/webhooks/...)
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
        if db_role.guild_discord_id != inter.guild.id:
            await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description="Роль не приналежит этому серверу",
                ),
                ephemeral=True,
            )
            return

        if webhook_url is not None:
            async with aiohttp.ClientSession() as session:
                webhook = Webhook.from_url(webhook_url, session=session)
                if webhook is None:
                    await inter.send(
                        embed=disnake.Embed(
                            color=disnake.Color.red(),
                            title="Ошибка",
                            description="Не удалось получить вебхук. Проверьте правильность ссылки.",
                        ),
                        ephemeral=True,
                    )
                    return
                elif webhook.guild_id != inter.guild.id:
                    await inter.send(
                        embed=disnake.Embed(
                            color=disnake.Color.red(),
                            title="Ошибка",
                            description="Вебхук не принадлежит этому серверу.",
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

    @commands.slash_command(
        name=Localized("hire", key="HIRE_COMMAND_NAME"),
        description=Localized(key="HIRE_COMMAND_DESCRIPTION"),
        dm_permission=False,
    )
    @commands.guild_only()
    @commands.default_member_permissions(manage_roles=True)
    @is_guild_registered()
    async def hire_user_command(
        self,
        inter: ApplicationCommandInteraction,
        user: disnake.Member = commands.Param(
            name=Localized("player", key="PLAYER_PARAM"),
            description=Localized(key="HIRE_PLAYER_DESCRIPTION"),
        ),
        role: str = commands.Param(
            name=Localized(key="HIRE_ROLE_NAME"),
            description=Localized(key="HIRE_ROLE_DESCRIPTION"),
            autocomplete=role_autocompleter,
        ),
        comment: Optional[str] = None,
    ):
        """
        Hire user.

        Parameters
        ----------
        user: Player
        role: Role [⚠ Choose from list!]
        comment: Comment
        """
        await inter.response.defer(ephemeral=True)
        try:
            role = int(role)
        except ValueError:
            return await inter.send(
                settings.Gifs.v_durku,
                ephemeral=True,
            )
        guild, db_role = await database.get_guild(
            inter.guild.id
        ), await database.get_role(role_discord_id=int(role))
        if not await check_role(inter, guild, db_role):
            return
        plasmo_guild = self.bot.get_guild(settings.PlasmoRPGuild.guild_id)
        plasmo_user = plasmo_guild.get_member(user.id) if plasmo_guild else None
        structure_role = inter.guild.get_role(db_role.role_discord_id)
        if structure_role is None:
            await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Error",
                    description="Role not found.",
                ),
                ephemeral=True,
            )
            await db_role.edit(available=False)
            return
        if (
            user.bot
            or inter.guild.get_role(guild.player_role_id) not in user.roles
            or (plasmo_user is None and not settings.DEBUG)
        ):
            return await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Error",
                    description="You cannot hire this user.",
                ),
                ephemeral=True,
            )
        hire_anyway = False
        if db_role.role_discord_id in [role.id for role in user.roles]:
            await inter.edit_original_message(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Error",
                    description=f"User already has <@&{db_role.role_discord_id}> role.",
                ),
                components=[
                    disnake.ui.Button(
                        label="Просто отправить уведомление",
                        style=disnake.ButtonStyle.red,
                        custom_id=f"hire_anyway.{user.id}.{db_role.role_discord_id}",
                    )
                ],
            )
            try:

                await self.bot.wait_for(
                    "button_click",
                    check=lambda i: (
                        i.component.custom_id
                        == f"hire_anyway.{user.id}.{db_role.role_discord_id}"
                    ),
                    timeout=300,
                )
            except asyncio.TimeoutError:
                return await inter.edit_original_message(components=[])
            hire_anyway = True
            await inter.edit_original_message(components=[])

        # Check for permissions
        if inter.author.top_role.position <= structure_role.position:
            return await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Error",
                    description="You cannot manage this role.",
                ),
                ephemeral=True,
            )

        plasmo_user: disnake.Member
        embed = disnake.Embed(
            color=disnake.Color.green(),
            description=f"{user.mention} был принят на должность **{db_role.name}**",
        ).set_author(
            name=plasmo_user.display_name if plasmo_user else user.display_name,
            icon_url="https://rp.plo.su/avatar/"
            + (plasmo_user.display_name if plasmo_user else user.display_name),
        )
        if comment is not None and comment.strip() != "":
            embed.add_field(name="Комментарий", value=comment)

        rrs_cog: Optional[core.RRSCore] = None
        if not hire_anyway:
            rrs_cog: Optional[core.RRSCore] = self.bot.get_cog("RRSCore")
            if rrs_cog is not None:
                await inter.edit_original_message(
                    embed=disnake.Embed(
                        color=disnake.Color.green(),
                        description="Проверка правил RRS...",
                    )
                )
                rrs_result = await rrs_cog.process_structure_role_change(
                    member=user,
                    role=structure_role,
                    operation_author=inter.author,
                    role_is_added=True,
                )
                if rrs_result is False:
                    return await inter.edit_original_message(
                        embed=disnake.Embed(
                            color=disnake.Color.red(),
                            title="Error",
                            description="Operation was cancelled by RRS.",
                        )
                    )

        try:
            await user.add_roles(
                structure_role,
                reason=f"Hired "
                f"[by {inter.author.display_name} / {inter.author} / {inter.author.id}]"
                + (" | RRSNR" if rrs_cog is not None else ""),
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
                    structure_role,
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

    @commands.guild_only()
    @commands.default_member_permissions(manage_roles=True)
    @is_guild_registered()
    @commands.slash_command(
        name=Localized("fire", key="FIRE_COMMAND_NAME"),
        description=Localized(key="FIRE_COMMAND_DESCRIPTION"),
        dm_permission=False,
    )
    async def fire_user_command(
        self,
        inter: ApplicationCommandInteraction,
        user: disnake.Member = commands.Param(
            name=Localized("player", key="PLAYER_PARAM"),
            description=Localized(key="FIRE_PLAYER_DESCRIPTION"),
        ),
        role: str = commands.Param(
            name=Localized(key="FIRE_ROLE_NAME"),
            description=Localized(key="FIRE_ROLE_DESCRIPTION"),
            autocomplete=role_autocompleter,
        ),
        reason: Optional[str] = commands.Param(
            name=Localized(key="FIRE_REASON_NAME"),
            description=Localized(key="FIRE_REASON_DESCRIPTION"),
            default="",
        ),
    ):
        """
        Fire user.

        Parameters
        ----------
        reason: Reason
        user: Player
        role: Role [⚠ Choose from autocomplete!]
        """
        await inter.response.defer(ephemeral=True)
        try:
            guild, db_role = await database.get_guild(
                inter.guild.id
            ), await database.get_role(role_discord_id=int(role))
        except ValueError:
            return await inter.edit_original_message(
                settings.Gifs.v_durku,
            )
        if not await check_role(inter, guild, db_role):
            return
        plasmo_guild = self.bot.get_guild(settings.PlasmoRPGuild.guild_id)
        if plasmo_guild is None and not settings.DEBUG:
            raise RuntimeError("Plasmo RP guild not found")
        plasmo_user = plasmo_guild.get_member(user.id) if plasmo_guild else None
        structure_role = inter.guild.get_role(db_role.role_discord_id)
        if structure_role is None:
            await inter.edit_original_message(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Error",
                    description="Role not found.",
                ),
            )
            await db_role.edit(available=False)
            return
        if (
            user.bot
            or inter.guild.get_role(guild.player_role_id) not in user.roles
            or (plasmo_user is None and not settings.DEBUG)
        ):
            return await inter.edit_original_message(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Error",
                    description="You cant fire this user.",
                ),
            )

        fire_anyway = False
        if db_role.role_discord_id not in [role.id for role in user.roles]:
            await inter.edit_original_message(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Error",
                    description=f"User does not have <@&{db_role.role_discord_id}> role.",
                ),
                components=[
                    disnake.ui.Button(
                        label="Просто отправить уведомление",
                        style=disnake.ButtonStyle.red,
                        custom_id=f"fire_anyway.{user.id}.{db_role.role_discord_id}",
                    )
                ],
            )
            try:

                await self.bot.wait_for(
                    "button_click",
                    check=lambda i: (
                        i.component.custom_id
                        == f"fire_anyway.{user.id}.{db_role.role_discord_id}"
                    ),
                    timeout=60,
                )
            except asyncio.TimeoutError:
                return await inter.edit_original_message(components=[])
            fire_anyway = True
            await inter.edit_original_message(components=[])
        # Check for permissions
        if inter.author.top_role.position <= structure_role.position:
            return await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Error",
                    description="You cannot manage this role.",
                ),
                ephemeral=True,
            )

        plasmo_user: disnake.Member

        embed = disnake.Embed(
            color=disnake.Color.dark_red(),
            description=f"{user.mention} был уволен с должности **{db_role.name}**",
        ).set_author(
            name=plasmo_user.display_name if plasmo_user else user.display_name,
            icon_url="https://rp.plo.su/avatar/"
            + (plasmo_user.display_name if plasmo_user else user.display_name),
        )
        if reason is not None and reason.strip() != "":
            embed.add_field(name="Причина", value=reason)

        rrs_cog: Optional[core.RRSCore] = None
        if not fire_anyway:
            rrs_cog: Optional[core.RRSCore] = self.bot.get_cog("RRSCore")
            if rrs_cog is not None:
                await inter.edit_original_message(
                    embed=disnake.Embed(
                        color=disnake.Color.green(),
                        description="Проверка правил RRS...",
                    )
                )
                rrs_result = await rrs_cog.process_structure_role_change(
                    member=user,
                    role=structure_role,
                    operation_author=inter.author,
                    role_is_added=False,
                )
                if rrs_result is False:
                    return await inter.edit_original_message(
                        embed=disnake.Embed(
                            color=disnake.Color.red(),
                            title="Error",
                            description="Operation was cancelled by RRS.",
                        )
                    )

        try:
            await user.remove_roles(
                structure_role,
                reason=f"Fired "
                f"[by {inter.author.display_name} / {inter.author} / {inter.author.id}]"
                + (" | RRSNR" if rrs_cog is not None else ""),
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
                    structure_role,
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
