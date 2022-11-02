import logging
from typing import Optional

import disnake
from aiohttp import ClientSession
from disnake import ApplicationCommandInteraction
from disnake.ext import commands

from plasmotools import settings
from plasmotools.utils import formatters, autocompleters, api
from plasmotools.utils.api import bank
from plasmotools.utils.api.tokens import get_token_scopes
from plasmotools.utils.database import plasmo_structures as database

logger = logging.getLogger(__name__)


# todo: Rewrite with buttons


class Payouts(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    # TODO:  payouts statistics

    @commands.guild_only()
    @commands.slash_command(name="проекты", dm_permission=False)
    async def projects(self, inter: ApplicationCommandInteraction):
        """
        Помощь по проектам и выплатам
        """
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
        await inter.send(
            embed=disnake.Embed(
                color=disnake.Color.green(),
                description="Проекты в Plasmo Tools - это упрощение системы выплат. Создайте проект через "
                "/проекты-создать чтобы получить доступ к /выплата\n\n"
                f"**plasmo_token**: Чтобы получить токен плазмо - "
                f"откройте тикет в [дискорде DDT]({settings.DevServer.support_invite}). (Как только мне "
                f"будет не лень я сделаю адекватное автоматическое получение токена)",
            ),
            ephemeral=True,
        )

    @commands.guild_only()
    @commands.slash_command(name="проекты-создать", dm_permission=False)
    @commands.default_member_permissions(administrator=True)
    async def projects_create(
        self,
        inter: ApplicationCommandInteraction,
        name: str,
        webhook_url: str,
        plasmo_bearer_token: str,
        from_card: int = commands.Param(gt=0, lt=10000),
    ):
        """
        Зарегистрировать проект

        Parameters
        ----------
        name: Название проекта, например "Интерпол"
        webhook_url: Ссылка на вебхук для отправки уведомлений (в формате https://discord.com/api/webhooks/...)
        from_card: Номер карты, с которой будет производиться выплата
        plasmo_bearer_token: Токен плазмо, используйте /проекты, чтобы узнать как его получить
        """
        # todo: autocomplete for from_card
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
        await inter.response.defer(ephemeral=True)
        await inter.edit_original_message(
            embed=disnake.Embed(
                color=disnake.Color.dark_green(),
                title="Верифицирую токен...",
            ),
        )
        scopes = await get_token_scopes(plasmo_bearer_token)
        if "bank:transfer" not in scopes and "bank:manage" not in scopes:
            await inter.edit_original_message(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description="Указан неправильный токен. ||Missing bank:manage / bank:transfer scopes||\n"
                    f"Получите новый в [поддержке DDT]({settings.DevServer.support_invite})",
                ),
            )
            return
        await inter.edit_original_message(
            embed=disnake.Embed(
                color=disnake.Color.dark_green(),
                title="Регистрирую проект...",
            ),
        )
        db_project = await database.register_project(
            name=name,
            guild_discord_id=inter.guild.id,
            is_active=True,
            webhook_url=webhook_url,
            from_card=from_card,
            plasmo_bearer_token=plasmo_bearer_token,
        )
        await inter.edit_original_message(
            embed=disnake.Embed(
                color=disnake.Color.green(),
                title="Проект успешно зарегистрирован",
                description=f"Проект: {name}\n"
                f"Вебхук: {webhook_url}\n"
                f"Карта: {from_card}\n"
                f"Токен: ||{plasmo_bearer_token[:-5]}\\*\\*\\*\\*||\n"
                f"ID: {db_project.id}",
            ),
        )

    @commands.guild_only()
    @commands.slash_command(name="проекты-редактировать", dm_permission=False)
    @commands.default_member_permissions(administrator=True)
    async def projects_edit(
        self,
        inter: ApplicationCommandInteraction,
        project_id: int,
        name: Optional[str] = None,
        webhook_url: Optional[str] = None,
        is_active: Optional[bool] = None,
        from_card: Optional[int] = commands.Param(default=None),
        plasmo_bearer_token: Optional[str] = None,
    ):
        """
        Редактировать проект в базе данных

        Parameters
        ----------
        project_id: Айди проекта
        webhook_url: Ссылка на вебхук для отправки уведомлений (https://discordapp.com/api/webhooks/{id}/{token})
        is_active: Доступен ли проект
        name: Название проекта, например "Интерпол" или "Постройка суда"
        from_card: Номер карты, с которой будет производиться выплата
        plasmo_bearer_token: Токен плазмо, используйте /проекты, чтобы узнать как его получить
        """
        await inter.response.defer(ephemeral=True)
        db_project = await database.get_project(project_id)
        if db_project is None:
            await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description="Проект не найден",
                ),
                ephemeral=True,
            )
            return
        await db_project.edit(
            name=name,
            is_active=is_active,
            webhook_url=webhook_url,
            from_card=from_card,
            plasmo_bearer_token=plasmo_bearer_token,
        )

        await inter.send(
            embed=disnake.Embed(
                color=disnake.Color.green(),
                title="Проект отредактирован",
            ),
            ephemeral=True,
        )

    @commands.guild_only()
    @commands.slash_command(name="проекты-удалить", dm_permission=False)
    @commands.default_member_permissions(administrator=True)
    async def projects_delete(
        self,
        inter: ApplicationCommandInteraction,
        project_id: int,
    ):
        """
        Удалить проект из базы данных

        Parameters
        ----------
        project_id: Айди проекта

        """
        await inter.response.defer(ephemeral=True)
        db_project = await database.get_project(project_id)
        if db_project is None:
            await inter.edit_original_message(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description="Проект не найден",
                ),
            )
            return
        await db_project.delete()

        await inter.edit_original_message(
            embed=disnake.Embed(
                color=disnake.Color.green(),
                title="Проект удален",
            ),
        )

    @commands.guild_only()
    @commands.slash_command(name="проекты-список", dm_permission=False)
    @commands.default_member_permissions(administrator=True)
    async def roles_list(self, inter: ApplicationCommandInteraction):
        """
        Получить список проектов на сервере
        """
        await inter.response.defer(ephemeral=True)
        projects = await database.get_projects(guild_discord_id=inter.guild.id)
        embed = disnake.Embed(
            color=disnake.Color.green(),
            title=f"Все проекты {inter.guild.name}",
        ).set_footer(
            text="[Пока не доступно] Используйте /статистика, чтобы просмотреть статистику по проекту",
        )
        if len(projects) == 0:
            embed.add_field(
                name="Проекты не найдены",
                value="Создайте первый через `/проекты-создать`",
            )
        else:
            embed.add_field(
                name="[Доступность] Название проекта",
                value="Айди / Карта / Токен \nВебхук",
            )
            for project in projects:
                project: database.Project
                embed.add_field(
                    name=f"{project.name} - {'Активен' if project.is_active else 'Неактивен'}  ",
                    value=f"{project.id} / {formatters.format_bank_card(project.from_card)} / "
                          f"||{project.plasmo_bearer_token[:-5]}\\*\\*\\*\\*||\n"
                    f"||{project.webhook_url}||",
                    inline=False,
                )

        await inter.edit_original_message(embed=embed)

    async def payout(
        self,
        interaction: disnake.Interaction,
        user: disnake.Member,
        amount: int,
        project: database.Project,
        message: str,
    ) -> bool:
        guild = await database.get_guild(interaction.guild.id)
        if guild is None:
            await interaction.edit_original_message(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description="Сервер не зарегистрирован как офицальная структура.\n"
                    "Если вы считаете что это ошибка - обратитесь в "
                    f"[поддержку digital drugs technologies]({settings.DevServer.support_invite})",
                ),
            )
            return False
        await interaction.edit_original_message(
            embed=disnake.Embed(
                color=disnake.Color.yellow(), description="Проверяю игрока..."
            )
        )

        if not settings.DEBUG:
            plasmo_user = self.bot.get_guild(settings.PlasmoRPGuild.guild_id).get_member(
                user.id
            )

            if (
                user.bot
                or plasmo_user is None
                or plasmo_user.guild.get_role(settings.PlasmoRPGuild.player_role_id)
                not in plasmo_user.roles
            ):
                await interaction.edit_original_message(
                    embed=disnake.Embed(
                        color=disnake.Color.red(),
                        title="Ошибка",
                        description="Невозможно выплатить этому пользователю",
                    ),
                )
                return False
            await interaction.edit_original_message(
                embed=disnake.Embed(
                    color=disnake.Color.yellow(), description="Получаю карту для выплаты..."
                )
            )
        else:
            plasmo_user = user
        from_card = project.from_card

        user_card = await database.get_saved_card(user.id)
        if user_card is None:
            user_cards = sorted(
                [
                    card
                    for card in await bank.search_cards(
                        token=project.plasmo_bearer_token,
                        query=plasmo_user.display_name,
                    )
                    if card["id"] != from_card
                    and card["holder_type"] == 0
                    and card["holder"] == plasmo_user.display_name
                ],
                key=lambda card: card["value"],
                reverse=True,
            )

            if len(user_cards) == 0:
                await interaction.edit_original_message(
                    embed=disnake.Embed(
                        color=disnake.Color.red(),
                        title="Ошибка",
                        description="Не удалось найти карту для выплаты, Plasmo Tools уведомит игрока об этом",
                    ),
                )
                try:
                    await user.send(
                        embed=disnake.Embed(
                            color=disnake.Color.red(),
                            title="⚠ Plasmo Tools не смог произвести выплату",
                            description="Не удалось найти карту для выплаты, чтобы в дальнейшем получать выплаты от "
                            "структур оформите карту на свой аккаунт или укажите любую карту через "
                            "/установить-карту-для-выплат",
                        )
                    )
                except disnake.Forbidden:
                    await interaction.send(
                        embed=disnake.Embed(
                            color=disnake.Color.red(),
                            title="Ошибка",
                            description=f"У {user.mention} закрыты личные сообщения,"
                                        f" вам придется лично попросить игрока "
                            f"установить карту через /установить-карту-для-выплат",
                        ),
                        ephemeral=True,
                    )
                return False

            user_card: int = user_cards[0]["id"]
            try:
                await user.send(
                    embed=disnake.Embed(
                        color=disnake.Color.red(),
                        title="⚠ У вас не установлена карта для выплат",
                        description=f"Вы не установили карту для выплат. Бот установил карту "
                        f"**{formatters.format_bank_card(user_card)}** как основную.\n\n"
                        f"Воспользуйтесь **/установить-карту-для-выплат**, если хотите получать выплаты "
                        f"на другую карту",
                    )
                )
            except disnake.Forbidden:
                pass
            await database.set_saved_card(user.id, user_card)

        await interaction.edit_original_message(
            embed=disnake.Embed(
                color=disnake.Color.yellow(), description="Перевожу алмазы..."
            )
        )
        if from_card == user_card:
            await interaction.edit_original_message(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description="Невозможно первести алмазы на эту карту",
                ),
            )
            return False
        status, error_message = await bank.transfer(
            token=project.plasmo_bearer_token,
            from_card=from_card,
            to_card=user_card,
            amount=amount,
            message=message,
        )
        if not status:
            await interaction.edit_original_message(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description="API вернуло ошибку: **" + error_message + "**",
                ),
            )
            return False
        await interaction.edit_original_message(
            embed=disnake.Embed(
                color=disnake.Color.yellow(),
                description="Отправляю оповещение о выплате...",
            )
        )

        embed = disnake.Embed(
            color=disnake.Color.green(),
            description=f"{user.mention} получает выплату в размере **{amount}** алм. ",
        ).set_author(
            name=plasmo_user.display_name,
            icon_url="https://rp.plo.su/avatar/" + plasmo_user.display_name,
        )
        if message != "":
            embed.add_field(name="Комментарий", value=message)

        async with ClientSession() as session:
            webhook = disnake.Webhook.from_url(project.webhook_url, session=session)
            try:
                await webhook.send(
                    content=user.mention,
                    embed=embed,
                )
            except disnake.errors.NotFound:

                await interaction.edit_original_message(
                    embed=disnake.Embed(
                        color=disnake.Color.red(),
                        title="Ошибка",
                        description="Не удалось получить доступ к вебхуку. Оплата прошла, но игрок не был оповещен",
                    ),
                )

        await self.bot.get_channel(guild.logs_channel_id).send(
            embed=embed.add_field("Выплатил", interaction.author.mention, inline=False)
            .add_field("Проект", project.name, inline=False)
            .add_field("С карты", formatters.format_bank_card(from_card), inline=False)
            .add_field(
                "На карту",
                formatters.format_bank_card(user_card),
                inline=False,
            )
        )

        await interaction.edit_original_message(
            embed=disnake.Embed(
                color=disnake.Color.green(),
                title="Успех",
                description=f"{user.mention} получил выплату в размере **{amount}** {settings.Emojis.diamond} на "
                f"карту {formatters.format_bank_card(user_card)}",
            ),
        )
        # todo: save failed payments and retry them later
        await database.register_payout_entry(
            project_id=project.id,
            user_id=user.id,
            amount=amount,
            message=message,
            from_card=from_card,
            to_card=user_card,
            is_payed=True,
        )
        await self.bot.get_channel(settings.DevServer.transactions_channel_id).send(
            embed=disnake.Embed(
                description=f"{formatters.format_bank_card(from_card)} -> "
                f"{amount} {settings.Emojis.diamond} -> "
                f"{formatters.format_bank_card(user_card)}\n"
                f" {message}",
            )
        )
        return True

    @commands.guild_only()
    @commands.slash_command(name="выплата", dm_permission=False)
    @commands.default_member_permissions(administrator=True)
    async def payout_command(
        self,
        inter: ApplicationCommandInteraction,
        user: disnake.Member,
        amount: int,
        project: str = commands.Param(
            autocomplete=autocompleters.payouts_projects_autocompleter
        ),
        message: str = "",
    ):
        """
        Выплатить игроку алмазы

        Parameters
        ----------
        user: Игрок, которому нужно выплатить алмазы
        amount: Количество алмазов, которое нужно выплатить
        project: Проект, от имени которого производится выплата
        message: Сообщение, которое будет отправлено игроку
        """
        await inter.response.defer(ephemeral=True)
        try:
            db_project = await database.get_project(int(project))
            if db_project is None:
                raise ValueError("Проект не найден")
        except ValueError:
            await inter.edit_original_message(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description="Проект не найден",
                ),
            )
            return
        await self.payout(inter, user, amount, db_project, message)

    @commands.slash_command(name="установить-карту-для-выплат")
    async def set_saved_card(
        self,
        inter: disnake.ApplicationCommandInteraction,
        card: str = commands.Param(
            autocomplete=autocompleters.search_bank_cards_autocompleter,
        ),
    ):
        """
        Установить карту для выплат гос. структур

        Parameters
        ----------
        card: Номер карты в формате 9000 или EB-9000. EB-0142 -> 142. EB-3666 -> 3666
        """
        await inter.response.defer(ephemeral=True)
        await inter.edit_original_message(
            embed=disnake.Embed(
                color=disnake.Color.yellow(), description="Валидирую данные..."
            )
        )
        try:
            card_id = int(card.replace(" ", "").replace("EB-", "").replace("ЕВ-", ""))
            if card_id < 0 or card_id > 9999:
                raise ValueError
        except ValueError:
            await inter.edit_original_message(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description="Не удалось распознать номер карты",
                ),
            )
            return

        await inter.edit_original_message(
            embed=disnake.Embed(
                color=disnake.Color.yellow(), description="Получаю данные о карте..."
            )
        )

        api_card = await api.bank.get_card_data(card_id)
        if api_card is None:
            await inter.edit_original_message(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description="Не удалось получить данные о карте",
                ),
            )
            return

        await inter.edit_original_message(
            embed=disnake.Embed(
                color=disnake.Color.yellow(),
                description="Сохраняю карту в базу данных...",
            )
        )

        await database.set_saved_card(
            user_id=inter.author.id,
            card_id=card_id,
        )
        await inter.edit_original_message(
            embed=disnake.Embed(
                color=disnake.Color.green(),
                title="Успех",
                description="Карта для выплат успешно установлена\n"
                f" {formatters.format_bank_card(card_id)} - {api_card['name']}\n"
                f"Принадлежит {api_card['holder']}",
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
    bot.add_cog(Payouts(bot))
