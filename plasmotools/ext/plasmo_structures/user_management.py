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

    @commands.slash_command(name="нанять")
    @commands.guild_only()
    @commands.default_member_permissions(manage_roles=True)
    async def hire_user_command(
            self,
            inter: ApplicationCommandInteraction,
            user: disnake.Member,
            role_discord_id: str = commands.Param(
                autocomplete=role_autocompleter,
            ),
            comment: Optional[str] = None,
    ):
        """
        Нанять пользователя в структуру.

        Parameters
        ----------
        comment: Комментарий к нанятию
        user: Игрок
        role_discord_id: Роль
        """
        guild, role = await database.get_guild(inter.guild.id), await database.get_role(
            role_discord_id=int(role_discord_id)
        )
        if not await check_role(inter, guild, role):
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
                    title="Ошибка",
                    description="Вы не можете нанять этого пользователя.",
                ),
                ephemeral=True,
            )
        if role.role_discord_id in [role.id for role in user.roles]:
            return await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description=f"У пользователя уже есть роль <@&{role.role_discord_id}>.",
                ),
                ephemeral=True,
            )

        plasmo_user: disnake.Member
        await inter.response.defer(ephemeral=True)
        embed = disnake.Embed(
            color=disnake.Color.green(),
            description=f"{user.mention} был принят на должность **{role.name}**",
        ).set_author(
            name=plasmo_user.display_name,
            icon_url="https://rp.plo.su/avatar/" + plasmo_user.display_name,
        )
        if comment is not None:
            embed.add_field(name="Комментарий", value=comment)

        try:
            await user.add_roles(
                inter.guild.get_role(role.role_discord_id),
                reason=f"Нанят в структуру "
                       f"[by {inter.author.display_name} / {inter.author}]",
            )
        except disnake.Forbidden:
            return await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description="Не удалось нанять пользователя. У бота нет прав выдавать эту роль.",
                ),
                ephemeral=True,
            )

        async with aiohttp.ClientSession() as session:
            webhook = disnake.Webhook.from_url(role.webhook_url, session=session)
            try:
                await webhook.send(
                    content=user.mention,
                    embed=embed,
                )
            except disnake.errors.NotFound:
                await user.remove_roles(
                    inter.guild.get_role(role.role_discord_id),
                    reason=f"Произошла ошибка при логировании нанятия",
                )
                return await inter.edit_original_message(
                    embed=disnake.Embed(
                        color=disnake.Color.red(),
                        title="Ошибка",
                        description="Не удалось получить доступ к вебхуку.",
                    ),
                )

        await self.bot.get_channel(guild.logs_channel_id).send(
            embed=embed.add_field("Вызвано пользователем", inter.author.mention)
        )

        await inter.edit_original_message(
            embed=disnake.Embed(
                color=disnake.Color.green(),
                title="Успех",
                description="Пользователь был успешно нанят.",
            ),

        )

    @commands.slash_command(name="уволить")
    @commands.guild_only()
    @commands.default_member_permissions(manage_roles=True)
    async def fire_user_command(
            self,
            inter: ApplicationCommandInteraction,
            user: disnake.Member,
            role_discord_id: str = commands.Param(autocomplete=role_autocompleter),
            reason: Optional[str] = None,
    ):
        """
        Уволить пользователя из структуры.

        Parameters
        ----------
        reason: Причина
        user: Игрок
        role_discord_id: Роль
        """
        guild, role = await database.get_guild(inter.guild.id), await database.get_role(
            role_discord_id=int(role_discord_id)
        )
        if not await check_role(inter, guild, role):
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
                    title="Ошибка",
                    description="Вы не можете снять этого пользователя.",
                ),
                ephemeral=True,
            )
        if role.role_discord_id not in [role.id for role in user.roles]:
            return await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description=f"У пользователя нет роли <@&{role.role_discord_id}>.",
                ),
                ephemeral=True,
            )

        plasmo_user: disnake.Member
        await inter.response.defer(ephemeral=True)
        embed = disnake.Embed(
            color=disnake.Color.dark_red(),
            description=f"{user.mention} был уволен с должности **{role.name}**",
        ).set_author(
            name=plasmo_user.display_name,
            icon_url="https://rp.plo.su/avatar/" + plasmo_user.display_name,
        )
        if reason is not None:
            embed.add_field(name="Причина", value=reason)

        try:
            await user.remove_roles(
                inter.guild.get_role(role.role_discord_id),
                reason=f"Уволен с должнrости "
                       f"[by {inter.author.display_name} / {inter.author}]",
            )
        except disnake.Forbidden:
            return await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description="Не удалось снять пользователя. У бота нет прав снимать эту роль.",
                ),
                ephemeral=True,
            )
        async with aiohttp.ClientSession() as session:
            webhook = disnake.Webhook.from_url(role.webhook_url, session=session)
            try:
                await webhook.send(
                    content=user.mention,
                    embed=embed,
                )
            except disnake.errors.NotFound:
                await user.add_roles(
                    inter.guild.get_role(role.role_discord_id),
                    reason=f"Произошла ошибка при логировании увольнения",
                )
                return await inter.edit_original_message(
                    embed=disnake.Embed(
                        color=disnake.Color.red(),
                        title="Ошибка",
                        description="Не удалось получить доступ к вебхуку.",
                    ),
                )

        await self.bot.get_channel(guild.logs_channel_id).send(
            embed=embed.add_field("Вызвано пользователем", inter.author.mention)
        )

        await inter.edit_original_message(
            embed=disnake.Embed(
                color=disnake.Color.green(),
                title="Успех",
                description="Пользователь был успешно снят.",
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
