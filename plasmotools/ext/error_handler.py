import logging

import disnake
from disnake import InteractionTimedOut
from disnake.ext import commands
from disnake.ext.commands.errors import (CheckFailure, MissingPermissions,
                                         MissingRole, NoPrivateMessage,
                                         NotOwner)

from plasmotools import settings
from plasmotools.utils.embeds import build_simple_embed

logger = logging.getLogger(__name__)


class GuildIsNotRegistered(commands.CheckFailure):
    pass


class BankAPIError(Exception):
    pass


class ErrorHandler(commands.Cog):
    """
    Handler for disnake errors
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_slash_command_error(
        self, inter: disnake.ApplicationCommandInteraction, error
    ):
        if isinstance(error, MissingRole):
            return await inter.send(
                embed=disnake.Embed(
                    title="У Вас недостаточно прав.",
                    description="Вам нужно "
                    f"иметь роль <@&{error.missing_role}> для использования этой команды.",
                    color=disnake.Color.dark_red(),
                ),
                ephemeral=True,
            )
        elif isinstance(error, MissingPermissions):
            return await inter.send(
                embed=disnake.Embed(
                    title="У Вас недостаточно прав.",
                    description="Вам нужно "
                    f"иметь пермишен **{error.missing_permissions[0]}** для использования этой команды.",
                    color=disnake.Color.dark_red(),
                ),
                ephemeral=True,
            )
        elif isinstance(error, NotOwner):
            return await inter.send(
                embed=disnake.Embed(
                    title="У Вас недостаточно прав.",
                    description="Вам нужно быть "
                    "администратором Plasmo или разработчиком бота для использования этой функции.",
                    color=disnake.Color.dark_red(),
                ),
                ephemeral=True,
            )
        elif isinstance(error, NoPrivateMessage):
            return await inter.send(
                embed=disnake.Embed(
                    title="Команда недоступна.",
                    description="`This command cannot be used in private messages.`",
                    color=disnake.Color.dark_red(),
                ),
                ephemeral=True,
            )
        elif isinstance(error, GuildIsNotRegistered):
            await inter.send(
                embed=build_simple_embed(
                    "Сервер не зарегистрирован как официальная структура.\n"
                    "Если вы считаете что это ошибка - обратитесь в "
                    f"[поддержку digital drugs technologies]({settings.DevServer.support_invite})",
                    failure=True,
                ),
                ephemeral=True,
            )
            return
        elif isinstance(error, CheckFailure):
            await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.dark_red(),
                    title="Ой, а що трапилось?",
                    description="Ви були заблокованi. Мабуть зробили щось не те"
                    f"\n\n[digital drugs technologies]({settings.DevServer.support_invite})",
                ),
                ephemeral=True,
            )
            return
        elif isinstance(error, disnake.errors.NotFound):
            await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.dark_red(),
                    title="Попробуйте еще раз",
                ),
                ephemeral=True,
            )
            return
        elif isinstance(error, InteractionTimedOut):
            logger.error(error)
        elif isinstance(error, disnake.HTTPException):
            logger.error(error)  # todo: ебучий 401 unauthorized
            print(error.__str__())
            raise error
        else:
            logger.error(error)
            try:
                await inter.send(
                    embed=disnake.Embed(
                        title="Error",
                        description=f"Возникла неожиданная ошибка.\n\n`{error}`"
                        f"\n\nРепортить баги можно тут - {settings.DevServer.support_invite}",
                        color=disnake.Color.dark_red(),
                    ),
                    ephemeral=True,
                )
            except disnake.HTTPException:
                pass
            await self.bot.get_channel(settings.DevServer.errors_channel_id).send(
                embed=disnake.Embed(
                    title="⚠⚠⚠",
                    description=f"Возникла неожиданная ошибка.\n\n"
                    f"[digital drugs technologies]({settings.DevServer.support_invite})\n\n"
                    f"`{str(error)[:900]}`",
                    color=disnake.Color.brand_green(),
                ).add_field(
                    name="inter data",
                    value=f"{inter.__dict__}"[:1000],
                )
            )
            raise error

    @commands.Cog.listener()
    async def on_command_error(self, ctx: disnake.ext.commands.Context, error):
        if isinstance(error, disnake.ext.commands.errors.CommandNotFound):
            await ctx.message.add_reaction("❓")
        elif isinstance(error, disnake.ext.commands.errors.NotOwner):
            await ctx.message.add_reaction("📷")
            await ctx.message.add_reaction("🤓")
        else:
            logger.error(error)
            await ctx.message.add_reaction("⚠")
            await ctx.send(
                embed=disnake.Embed(
                    title="Error",
                    description=f"Возникла неожиданная ошибка.\n\n`{error}`"
                    f"\n\nРепортить баги можно тут - {settings.DevServer.support_invite}",
                    color=disnake.Color.dark_red(),
                ),
                delete_after=10,
            )
            if isinstance(error, disnake.ext.commands.errors.NotOwner):
                return
            await self.bot.get_channel(settings.DevServer.errors_channel_id).send(
                embed=disnake.Embed(
                    title="⚠⚠⚠",
                    description=f"Возникла неожиданная ошибка.\n\n`{str(error)[:900]}`",
                    color=disnake.Color.brand_green(),
                ).add_field(
                    name="inter data",
                    value=f"{ctx.__dict__}"[:1000],
                )
            )
            raise error


def setup(client):
    client.add_cog(ErrorHandler(client))
