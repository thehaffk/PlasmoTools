import asyncio
import logging
from typing import Optional

import aiohttp
import disnake
from disnake import ApplicationCommandInteraction, Webhook
from disnake.ext import commands

from plasmotools import checks, settings
from plasmotools.checks import is_guild_registered
from plasmotools.utils import models
from plasmotools.utils.autocompleters.plasmo_structures import \
    role_autocompleter
from plasmotools.utils.embeds import build_simple_embed

logger = logging.getLogger(__name__)


# TODO: Auto remove all roles, when user leaves plasmo rp


async def check_role(inter, guild, role) -> bool:
    if role is None or role.guild_discord_id != guild.discord_id:
        await inter.send(
            embed=build_simple_embed(
                "Роль не найдена. Пожалуйста, выбирайте только из списка", failure=True
            ),
            ephemeral=True,
        )
        return False
    if role.is_available is False:
        await inter.send(
            embed=build_simple_embed("Роль не доступна для выбора", failure=True),
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
    @checks.blocked_users_slash_command_check()
    async def roles_list(self, inter: ApplicationCommandInteraction):
        """
        Получить список ролей в сервере
        """
        roles = await models.StructureRole.objects.filter(
            guild_discord_id=inter.guild.id
        ).all()
        embed = disnake.Embed(
            color=disnake.Color.dark_green(),
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
                    value=f"{settings.Emojis.enabled if role.is_available else settings.Emojis.disabled} "
                    f"<@&{role.role_discord_id}> / `{role.role_discord_id}` \n ||{role.webhook_url}||",
                    inline=False,
                )

        await inter.send(embed=embed, ephemeral=True)

    @commands.guild_only()
    @commands.slash_command(name="роли-добавить", dm_permission=False)
    @commands.default_member_permissions(administrator=True)
    @is_guild_registered()
    @checks.blocked_users_slash_command_check()
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
        inter
        role: Роль
        webhook_url: Ссылка на вебхук для отправки уведомлений (в формате https://discord.com/api/webhooks/...)
        available: Доступна ли роль для найма и снятия
        name: Название роли, например "Интерпол"

        """

        db_guild = await models.StructureGuild.objects.get(discord_id=inter.guild.id)
        if role.id in [db_guild.player_role_id, db_guild.head_role_id]:
            await inter.send(
                embed=build_simple_embed(
                    "Эта роль не может быть закреплена как нанимаемая\n"
                    "Если вы считаете что это ошибка - обратитесь в "
                    f"[поддержку digital drugs technologies]{settings.DevServer.support_invite}",
                    failure=True,
                ),
                ephemeral=True,
            )
            return
        await inter.response.defer(ephemeral=True)
        async with aiohttp.ClientSession() as session:  # todo: create method to check webhooks (dry)
            webhook = Webhook.from_url(webhook_url, session=session)
            if webhook is None:
                await inter.send(
                    embed=build_simple_embed(
                        "Не удалось получить вебхук. Проверьте правильность ссылки.",
                        failure=True,
                    ),
                    ephemeral=True,
                )
                return

        await models.StructureRole.objects.update_or_create(
            role_discord_id=role.id,
            defaults={
                "guild_discord_id": inter.guild.id,
                "name": name,
                "webhook_url": webhook_url,
                "is_available": available,
            },
        )
        await inter.edit_original_message(
            embed=build_simple_embed(
                f"Роль `{name}` обновлена",
            ),
        )

    @commands.guild_only()
    @commands.slash_command(name="роли-удалить", dm_permission=False)
    @commands.default_member_permissions(administrator=True)
    @is_guild_registered()
    @checks.blocked_users_slash_command_check()
    async def roles_delete(
        self,
        inter: ApplicationCommandInteraction,
        role: disnake.Role,
    ):
        """
        Удалить роль из базы данных
        """
        await inter.response.defer(ephemeral=True)
        await models.StructureRole.objects.filter(
            role_discord_id=role.id, guild_discord_id=inter.guild_id
        ).delete()
        await inter.edit_original_message(
            embed=build_simple_embed(
                "Роль удалена",
            )
        )

    @commands.guild_only()
    @commands.slash_command(name="роли-редактировать", dm_permission=False)
    @commands.default_member_permissions(administrator=True)
    @is_guild_registered()
    @checks.blocked_users_slash_command_check()
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
        inter
        role: Роль
        webhook_url: Ссылка на вебхук для отправки уведомлений (https://discord.com/api/webhooks/...)
        available: Доступна ли роль для найма и снятия
        name: Название роли, например "Интерпол"

        """
        db_role = await models.StructureRole.objects.filter(
            role_discord_id=role.id, guild_discord_id=inter.guild_id
        ).first()
        if db_role is None:
            return await inter.send(
                embed=build_simple_embed("Роль не найдена", failure=True),
                ephemeral=True,
            )

        if webhook_url is not None:
            async with aiohttp.ClientSession() as session:
                webhook = Webhook.from_url(webhook_url, session=session)
                if webhook is None:
                    await inter.send(
                        embed=build_simple_embed(
                            "Не удалось получить вебхук. Проверьте правильность ссылки",
                            failure=True,
                        ),
                        ephemeral=True,
                    )
                    return
                elif webhook.guild_id != inter.guild.id:
                    await inter.send(
                        embed=build_simple_embed(
                            "Вебхук не принадлежит этому серверу.", failure=True
                        ),
                        ephemeral=True,
                    )
                    return

        await db_role.update(
            name=name if name is not None else db_role.name,
            webhook_url=webhook_url if webhook_url is not None else db_role.webhook_url,
            is_available=available if available is not None else db_role.is_available,
        )

        await inter.send(
            embed=build_simple_embed(
                "Роль отредактирована",
            ),
            ephemeral=True,
        )

    @commands.slash_command(
        name="hire",
        dm_permission=False,
    )
    @commands.guild_only()
    @commands.default_member_permissions(manage_roles=True)
    @is_guild_registered()
    @checks.blocked_users_slash_command_check()
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
        Hire user. {{HIRE_COMMAND}}

        Parameters
        ----------
        inter
        user: Player {{HIRE_PLAYER}}
        role: Role [⚠ Choose from list!] {{HIRE_ROLE}}
        comment: Comment  {{HIRE_REASON}}
        """
        await inter.response.defer(ephemeral=True)
        try:
            role = int(role)
        except ValueError:
            return await inter.send(
                settings.Gifs.v_durku,
                ephemeral=True,
            )
        db_role = await models.StructureRole.objects.filter(
            guild_discord_id=inter.guild.id, role_discord_id=int(role)
        ).first()
        db_guild = await models.StructureGuild.objects.filter(
            discord_id=inter.guild.id
        ).first()

        if not await check_role(inter, db_guild, db_role):
            return

        plasmo_guild = self.bot.get_guild(settings.PlasmoRPGuild.guild_id)
        plasmo_user = plasmo_guild.get_member(user.id) if plasmo_guild else None
        structure_role = inter.guild.get_role(db_role.role_discord_id)
        if structure_role is None:
            await inter.send(
                embed=build_simple_embed("Роль не найдена", failure=True),
                ephemeral=True,
            )
            await db_role.update(is_available=False)
            return
        if (
            user.bot
            or inter.guild.get_role(db_guild.player_role_id) not in user.roles
            or (plasmo_user is None and not settings.DEBUG)
        ):
            return await inter.send(
                embed=build_simple_embed(
                    "Вы не можете нанять этого пользователя.", failure=True
                ),
                ephemeral=True,
            )
        hire_anyway = False
        if db_role.role_discord_id in [role.id for role in user.roles]:
            await inter.edit_original_message(
                embed=build_simple_embed(
                    f"У пользователя уже есть роль <@&{db_role.role_discord_id}>",
                    failure=True,
                ),
                components=[
                    disnake.ui.Button(
                        label="Просто отправить уведомление",
                        style=disnake.ButtonStyle.gray,
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
                embed=build_simple_embed(
                    "Вы не можете управлять этой ролью", failure=True
                ),
                ephemeral=True,
            )

        plasmo_user: disnake.Member
        embed = disnake.Embed(
            color=disnake.Color.dark_green(),
            description=f"{user.mention} принят на должность **{db_role.name}**",  # todo: gender things
        ).set_author(
            name=plasmo_user.display_name if plasmo_user else user.display_name,
            icon_url="https://rp.plo.su/avatar/"
            + (plasmo_user.display_name if plasmo_user else user.display_name),
        )
        if comment is not None and comment.strip() != "":
            embed.add_field(name="Комментарий", value=comment)

        rrs_cog = None
        if not hire_anyway:
            if (rrs_cog := self.bot.get_cog("RRSCore")) is not None:
                await inter.edit_original_message(
                    embed=build_simple_embed(
                        description="Проверка правил RRS...",
                        without_title=True,
                    )
                )
                rrs_result = await rrs_cog.process_UM_structure_role_change(
                    member=user,
                    role=structure_role,
                    author=inter.author,
                    role_is_added=True,
                )
                if rrs_result is False:
                    return await inter.edit_original_message(
                        embed=build_simple_embed("Операция отклонена RRS", failure=True)
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
                embed=build_simple_embed(
                    "У бота нет прав на выдачу этой роли", failure=True
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
                    reason="Unexpected error",
                )
                return await inter.edit_original_message(
                    embed=build_simple_embed(
                        "Не удалось получить вебхук для отправки уведомления",
                        failure=True,
                    ),
                )

        await self.bot.get_channel(db_guild.logs_channel_id).send(
            embed=embed.add_field("Called by", inter.author.mention)
        )

        await inter.edit_original_message(
            embed=build_simple_embed(
                "User was successfully hired.",
            ),
        )

    @commands.guild_only()
    @commands.default_member_permissions(manage_roles=True)
    @is_guild_registered()
    @commands.slash_command(
        name="fire",
        dm_permission=False,
    )
    @checks.blocked_users_slash_command_check()
    async def fire_user_command(
        self,
        inter: ApplicationCommandInteraction,
        user: disnake.Member = commands.Param(),
        role: str = commands.Param(
            autocomplete=role_autocompleter,
        ),
        reason: Optional[str] = commands.Param(
            default="",
        ),
    ):
        """
        Fire user. {{FIRE_COMMAND}}

        Parameters
        ----------
        inter
        user: Player {{FIRE_PLAYER}}
        role: Role [⚠ Choose from autocomplete!] {{FIRE_ROLE}}
        reason: Reason {{FIRE_REASON}}
        """
        await inter.response.defer(ephemeral=True)
        if not role.isdigit():
            return await inter.edit_original_message(
                settings.Gifs.v_durku,
            )
        db_role = await models.StructureRole.objects.filter(
            guild_discord_id=inter.guild_id, role_discord_id=role
        ).first()
        db_guild = await models.StructureGuild.objects.filter(
            discord_id=inter.guild_id
        ).first()

        if not await check_role(inter, db_guild, db_role):
            return
        plasmo_guild = self.bot.get_guild(settings.PlasmoRPGuild.guild_id)
        if plasmo_guild is None and not settings.DEBUG:
            logger.critical("Plasmo RP guild not found")
            return
        plasmo_user = plasmo_guild.get_member(user.id) if plasmo_guild else None
        structure_role = inter.guild.get_role(db_role.role_discord_id)
        if structure_role is None:
            await inter.edit_original_message(
                embed=build_simple_embed("Роль не найдена", failure=True),
            )
            await db_role.update(is_available=False)
            return
        if (
            user.bot
            or inter.guild.get_role(db_guild.player_role_id) not in user.roles
            or (plasmo_user is None and not settings.DEBUG)
        ):
            return await inter.edit_original_message(
                embed=build_simple_embed(
                    "Вы не можете увольнять этого пользователя", failure=True
                ),
            )

        fire_anyway = False
        if db_role.role_discord_id not in [role.id for role in user.roles]:
            await inter.edit_original_message(
                embed=build_simple_embed(
                    f"У пользователя нет роли <@&{db_role.role_discord_id}>",
                    failure=True,
                ),
                components=[
                    disnake.ui.Button(
                        label="Просто отправить уведомление",
                        style=disnake.ButtonStyle.gray,
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
                embed=build_simple_embed(
                    "Вы не можете управлять этой ролью", failure=True
                ),
                ephemeral=True,
            )

        plasmo_user: disnake.Member

        embed = disnake.Embed(
            color=disnake.Color.dark_red(),
            description=f"{user.mention} уволен с должности **{db_role.name}**",
        ).set_author(
            name=plasmo_user.display_name if plasmo_user else user.display_name,
            icon_url="https://rp.plo.su/avatar/"
            + (plasmo_user.display_name if plasmo_user else user.display_name),
        )
        if reason is not None and reason.strip() != "":
            embed.add_field(name="Причина", value=reason)

        rrs_cog = None
        if not fire_anyway:
            rrs_cog = self.bot.get_cog("RRSCore")
            if rrs_cog is not None:
                await inter.edit_original_message(
                    embed=build_simple_embed(
                        description="Проверка правил RRS...",
                        without_title=True,
                    )
                )
                rrs_result = await rrs_cog.process_UM_structure_role_change(
                    member=user,
                    role=structure_role,
                    author=inter.author,
                    role_is_added=False,
                )
                if rrs_result is False:
                    return await inter.edit_original_message(
                        embed=build_simple_embed(
                            "Операция была отменена RRS", failure=True
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
                embed=build_simple_embed(
                    "У бота нет прав снимать эту роль", failure=True
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
                    reason="Unexpected error",
                )
                return await inter.edit_original_message(
                    embed=build_simple_embed(
                        "Не удалось получить доступ к вебхуку", failure=True
                    ),
                )

        await self.bot.get_channel(db_guild.logs_channel_id).send(
            embed=embed.add_field("Called by", inter.author.mention)
        )

        await inter.edit_original_message(
            embed=build_simple_embed("The user was successfully fired"),
        )

    async def cog_load(self):
        """
        Called when disnake bot object is ready
        """

        logger.info("%s loaded", __name__)


def setup(bot: disnake.ext.commands.Bot):
    """
    Disnake internal setup function
    """
    bot.add_cog(UserManagement(bot))
