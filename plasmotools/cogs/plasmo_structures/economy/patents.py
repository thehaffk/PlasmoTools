import asyncio
import datetime
import logging
import re
from typing import List, Optional

import disnake
from disnake import (ApplicationCommandInteraction, Localized,
                     MessageInteraction)
from disnake.ext import commands

from plasmotools import formatters, models, settings
from plasmotools.cogs.error_handler import BankAPIError
from plasmotools.embeds import build_simple_embed
from plasmotools.plasmo_api import bank as bank_api
from plasmotools.plasmo_api.messenger import send_mc_message

logger = logging.getLogger(__name__)


# note: Это один большой монолитный прикол, который в теории можно разбить на кучу микрофункций, но я не вижу
# в этом как такового смысла


class PatentTypeView(disnake.ui.View):
    def __init__(
        self,
    ):
        super().__init__(timeout=600)
        self.is_mapart = None

    @disnake.ui.button(label="Мапарт", style=disnake.ButtonStyle.green, emoji="🗾")
    async def mapart_button(
        self, _: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        self.is_mapart = True
        await interaction.response.defer(ephemeral=True)
        self.stop()

    @disnake.ui.button(label="Другое", style=disnake.ButtonStyle.green, emoji="💡")
    async def other_button(
        self, _: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        self.is_mapart = False
        await interaction.response.defer(ephemeral=True)
        self.stop()

    @disnake.ui.button(
        label="Отменить", style=disnake.ButtonStyle.gray, emoji="❌", row=1
    )
    async def cancel_button(
        self, _: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        self.is_mapart = None
        await interaction.response.send_message(
            embed=build_simple_embed("Создание патента отменено"), ephemeral=True
        )
        self.stop()

    async def on_timeout(self) -> None:
        self.stop()


class MapsCountView(disnake.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=1200)
        self.bot = bot
        self.maps_count = None

    @disnake.ui.button(style=disnake.ButtonStyle.green, emoji="1️⃣")
    async def one_map_button(
        self, _: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        await interaction.response.defer(ephemeral=True)
        self.maps_count = 1
        self.stop()

    @disnake.ui.button(style=disnake.ButtonStyle.green, emoji="2️⃣")
    async def two_maps_button(
        self, _: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        await interaction.response.defer(ephemeral=True)
        self.maps_count = 2
        self.stop()

    @disnake.ui.button(style=disnake.ButtonStyle.green, emoji="4️⃣")
    async def four_maps_button(
        self, _: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        await interaction.response.defer(ephemeral=True)
        self.maps_count = 4
        self.stop()

    @disnake.ui.button(style=disnake.ButtonStyle.green, emoji="6️⃣")
    async def six_maps_button(
        self, _: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        await interaction.response.defer(ephemeral=True)
        self.maps_count = 6
        self.stop()

    @disnake.ui.button(
        label="Ввести вручную", style=disnake.ButtonStyle.green, emoji="✏️", row=0
    )
    async def specify_count_button(
        self, _: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        await interaction.response.send_modal(
            title="Создание патента",
            custom_id="specify_maps_count_modal",
            components=[
                disnake.ui.TextInput(
                    label="Количество карт",
                    placeholder="2",
                    custom_id="map_count",
                    style=disnake.TextInputStyle.short,
                    min_length=1,
                    max_length=3,
                ),
            ],
        )

        try:
            modal_inter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=lambda i: i.custom_id == "specify_maps_count_modal"
                and i.author.id == interaction.author.id,
                timeout=600,
            )
        except asyncio.TimeoutError:
            self.maps_count = None
            self.stop()
            return

        await modal_inter.response.defer(ephemeral=True)

        if not modal_inter.text_values["map_count"].isdigit():
            await modal_inter.edit_original_message(
                embed=build_simple_embed(
                    "Неправильный формат количества карт. Пример: `4`", failure=True
                )
            )
            await asyncio.sleep(5)
            return await modal_inter.delete_original_message()
        self.maps_count = int(modal_inter.text_values["map_count"])

        if self.maps_count < 0 or self.maps_count > 128:
            await modal_inter.edit_original_message(
                embed=build_simple_embed(
                    "Количество карт должно варьироваться в диапазоне `1-128`",
                    failure=True,
                )
            )
            await asyncio.sleep(5)
            return await modal_inter.delete_original_message()

        await modal_inter.delete_original_response()
        self.stop()

    @disnake.ui.button(
        label="Отменить", style=disnake.ButtonStyle.gray, emoji="❌", row=1
    )
    async def cancel_button(
        self, _: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        self.maps_count = None
        await interaction.response.send_message(
            embed=build_simple_embed("Создание патента отменено"), ephemeral=True
        )
        self.stop()

    async def on_timeout(self) -> None:
        self.stop()


class ClientSelectView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=1200)
        self.client = None

    @disnake.ui.user_select(max_values=1)
    async def user_select(
        self, select: disnake.ui.UserSelect, interaction: disnake.MessageInteraction
    ):
        if len(select.values) != 1:
            await interaction.send(
                embed=build_simple_embed("Выберите одного пользователя", failure=True),
                ephemeral=True,
            )
            await asyncio.sleep(5)
            return await interaction.delete_original_message()

        user = select.values[0]
        if user == interaction.author:
            await interaction.send(
                embed=build_simple_embed(
                    "Нельзя оформлять патенты самому себе", failure=True
                ),
                ephemeral=True,
            )
            await asyncio.sleep(5)
            return await interaction.delete_original_message()
        if user.bot:
            await interaction.send("https://imgur.com/FzWuyfU.mp4", ephemeral=True)
            await asyncio.sleep(5)
            return await interaction.delete_original_message()

        await interaction.response.defer(ephemeral=True)
        self.client = user
        self.stop()

    @disnake.ui.button(
        label="Отменить", style=disnake.ButtonStyle.gray, emoji="❌", row=1
    )
    async def cancel(
        self, _: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        self.client = None
        await interaction.response.send_message(
            embed=build_simple_embed("Создание патента отменено"), ephemeral=True
        )
        self.stop()

    async def on_timeout(self) -> None:
        self.client = None
        self.stop()


class ConfirmationView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=1200)
        self.decision = None

    @disnake.ui.button(
        label="Подтвердить", style=disnake.ButtonStyle.green, emoji="✅", row=0
    )
    async def confirm_button(
        self, _: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        await interaction.response.defer(ephemeral=True)
        self.decision = True
        self.stop()

    @disnake.ui.button(
        label="Отменить", style=disnake.ButtonStyle.gray, emoji="❌", row=1
    )
    async def cancel_button(
        self, _: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        await interaction.response.send_message(
            embed=build_simple_embed("Создание патента отменено"), ephemeral=True
        )
        self.decision = False
        self.stop()

    async def on_timeout(self) -> None:
        self.decision = False
        self.stop()


class PatentOwnersView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=1200)
        self.patent_owners = None

    @disnake.ui.user_select(
        max_values=16, min_values=1, placeholder="Выберите владельцев патента", row=0
    )
    async def user_select(
        self, select: disnake.ui.UserSelect, interaction: disnake.MessageInteraction
    ):
        self.patent_owners = [user for user in select.values if not user.bot]
        if len(self.patent_owners) < 1:
            await interaction.send(
                embed=build_simple_embed(
                    "Выберите хотя бы одного пользователя. Боты автоматически убираются из списка",
                    failure=True,
                ),
                ephemeral=True,
            )
            await asyncio.sleep(5)
            return await interaction.delete_original_message()

        await interaction.send(
            embed=build_simple_embed(
                description="Выбрано:"
                + ", ".join([user.mention for user in self.patent_owners])
                + "\n\nНажмите "
                "**✅ Все владельцы выбраны**"
                " если выбраны все владельцы патента",
                without_title=True,
            ),
            ephemeral=True,
        )

        await asyncio.sleep(5)
        return await interaction.delete_original_message()

    @disnake.ui.button(
        label="Все владельцы выбраны", style=disnake.ButtonStyle.green, emoji="✅", row=1
    )
    async def confirm(
        self, _: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        await interaction.response.defer(ephemeral=True)
        if len(self.patent_owners) < 1:
            await interaction.send(
                embed=build_simple_embed(
                    "Выберите хотя бы одного владельца патента", failure=True
                ),
                ephemeral=True,
            )
            await asyncio.sleep(3)
            return await interaction.delete_original_message()

        self.stop()

    @disnake.ui.button(
        label="Отменить", style=disnake.ButtonStyle.gray, emoji="❌", row=2
    )
    async def cancel(
        self, _: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        self.patent_owners = None
        await interaction.response.send_message(
            embed=build_simple_embed("Создание патента отменено"), ephemeral=True
        )
        self.stop()

    async def on_timeout(self) -> None:
        self.patent_owners = None
        self.stop()


class PatentNameView(disnake.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=1200)
        self.bot = bot
        self.patent_name = None

    @disnake.ui.button(
        label="Ввести название", style=disnake.ButtonStyle.green, emoji="✏️", row=0
    )
    async def specify_name_button(
        self, _: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        await interaction.response.send_modal(
            title="Создание патента",
            custom_id="specify_name_modal",
            components=[
                disnake.ui.TextInput(
                    label="Название патента",
                    placeholder="Ушние капли",
                    custom_id="patent_name",
                    style=disnake.TextInputStyle.short,
                    min_length=1,
                    max_length=64,
                ),
            ],
        )

        try:
            modal_inter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=lambda i: i.custom_id == "specify_name_modal"
                and i.author.id == interaction.author.id,
                timeout=600,
            )
        except asyncio.TimeoutError:
            self.patent_name = None
            self.stop()
            return
        try:
            await modal_inter.response.defer(ephemeral=True)
        except disnake.HTTPException:
            return  # ????????
        self.patent_name = modal_inter.text_values["patent_name"]
        await modal_inter.delete_original_response()
        self.stop()

    @disnake.ui.button(
        label="Отменить", style=disnake.ButtonStyle.gray, emoji="❌", row=1
    )
    async def cancel_button(
        self, _: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        self.patent_name = None
        await interaction.response.send_message(
            embed=build_simple_embed("Создание патента отменено"), ephemeral=True
        )
        self.stop()

    async def on_timeout(self) -> None:
        self.stop()


class BankCardSelectionView(disnake.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=1200)
        self.bot = bot
        self.bank_code = "EB"
        self.card_id = None
        self.card_api_data = None

    @disnake.ui.button(
        label="Ввести номер карты", style=disnake.ButtonStyle.green, emoji="✏️", row=0
    )
    async def specify_card_button(
        self, _: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        await interaction.response.send_modal(
            title="Создание патента",
            custom_id="specify_card_modal",
            components=[
                disnake.ui.TextInput(
                    label="Номер карты",
                    placeholder="Без EB-",
                    custom_id="bank_card",
                    style=disnake.TextInputStyle.short,
                    min_length=1,
                    max_length=4,
                ),
            ],
        )

        try:
            modal_inter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=lambda i: i.custom_id == "specify_card_modal"
                and i.author.id == interaction.author.id,
                timeout=600,
            )
        except asyncio.TimeoutError:
            self.stop()
            return
        try:
            await modal_inter.response.defer(ephemeral=True)
        except disnake.HTTPException:
            return  # ????????

        if not modal_inter.text_values["bank_card"].isdigit():
            await modal_inter.edit_original_message(
                embed=build_simple_embed(
                    "Номер карты должен состоять только из цифр", failure=True
                ),
            )

            await asyncio.sleep(3)
            return await modal_inter.delete_original_response()

        self.card_id = int(modal_inter.text_values["bank_card"])

        if self.card_id < 1 or self.card_id > 9999:
            await modal_inter.response.send_message(
                embed=build_simple_embed(
                    "Номер карты должен быть от 1 до 9999", failure=True
                ),
                ephemeral=True,
            )
            await asyncio.sleep(3)
            return await modal_inter.delete_original_response()

        api_card = await bank_api.get_card_data(
            card_str=formatters.format_bank_card(
                self.card_id, bank_prefix=self.bank_code
            ),
            supress_warnings=True,
        )
        if api_card is None:
            await modal_inter.edit_original_message(
                embed=build_simple_embed("Карта не найдена", failure=True),
            )
            await asyncio.sleep(5)
            await modal_inter.delete_original_response()
            return
        self.card_api_data = api_card

        await modal_inter.delete_original_response()
        self.stop()

    @disnake.ui.button(
        label="Отменить", style=disnake.ButtonStyle.gray, emoji="❌", row=1
    )
    async def cancel_button(
        self, _: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        self.card_id = None
        await interaction.response.send_message(
            embed=build_simple_embed("Создание патента отменено"), ephemeral=True
        )
        self.stop()

    async def on_timeout(self) -> None:
        self.stop()


class ConfirmOrDenyView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=1200)
        self.accepted = None

    @disnake.ui.button(
        label="Подтвердить", style=disnake.ButtonStyle.green, emoji="✅", row=0
    )
    async def confirm_button(
        self, _: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        await interaction.response.defer(ephemeral=True)

        self.accepted = True
        self.stop()

    @disnake.ui.button(
        label="Отказаться", style=disnake.ButtonStyle.gray, emoji="❌", row=0
    )
    async def deny_button(
        self, _: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        await interaction.response.defer(ephemeral=True)

        self.accepted = False
        self.stop()

    async def on_timeout(self) -> None:
        self.stop()


class SpecifyMapNumberView(disnake.ui.View):
    def __init__(self, bot, map_index: int, selected_maps: List[int]):
        super().__init__(timeout=1200)
        self.map_index = map_index
        self.bot = bot
        self.map_number = None
        self.selected_maps = selected_maps
        self.specify_map_button.label = f"Ввести номер карты {self.map_index}"

    @disnake.ui.button(style=disnake.ButtonStyle.green, emoji="✏️", row=0)
    async def specify_map_button(
        self, _: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        await interaction.response.send_modal(
            title="Создание патента",
            custom_id="specify_map_number_modal",
            components=[
                disnake.ui.TextInput(
                    label="Номер карты",
                    placeholder="Без #",
                    custom_id="map_number",
                    style=disnake.TextInputStyle.short,
                    min_length=1,
                    max_length=4,
                ),
            ],
        )

        try:
            modal_inter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=lambda i: i.custom_id == "specify_map_number_modal"
                and i.author.id == interaction.author.id,
                timeout=600,
            )
        except asyncio.TimeoutError:
            self.map_number = None
            self.stop()
            return
        try:
            await modal_inter.response.defer(ephemeral=True)
        except disnake.HTTPException:
            return  # ????????

        if not modal_inter.text_values["map_number"].isdigit():
            await modal_inter.edit_original_message(
                embed=build_simple_embed(
                    "Номер карты должен состоять только из цифр", failure=True
                ),
            )

            await asyncio.sleep(3)
            return await modal_inter.delete_original_response()

        self.map_number = int(modal_inter.text_values["map_number"])

        if self.map_number < 1:
            await modal_inter.response.send_message(
                embed=build_simple_embed(
                    "Номер карты должен быть больше 1", failure=True
                ),
                ephemeral=True,
            )
            await asyncio.sleep(3)
            return await modal_inter.delete_original_response()

        if self.map_number in self.selected_maps:
            await modal_inter.edit_original_response(
                embed=build_simple_embed("Вы уже указали эту карту", failure=True),
            )
            await asyncio.sleep(3)
            return await modal_inter.delete_original_response()

        await modal_inter.delete_original_response()
        self.stop()

    @disnake.ui.button(
        label="Отменить", style=disnake.ButtonStyle.gray, emoji="❌", row=1
    )
    async def cancel_button(
        self, _: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        self.map_number = None
        await interaction.response.send_message(
            embed=build_simple_embed("Создание патента отменено"), ephemeral=True
        )
        self.stop()

    async def on_timeout(self) -> None:
        self.stop()


async def _get_patent_embed(
    patent_id: int, for_internal_use: bool = False
) -> disnake.Embed:
    db_patent = await models.Patent.objects.filter(id=patent_id).first()
    if db_patent is None:
        return build_simple_embed(
            f"Патент {formatters.format_patent_number(patent_id)} не найден",
            failure=True,
        )

    if for_internal_use:
        patent_embed = disnake.Embed(
            title="Патент " + formatters.format_patent_number(patent_id),
            color=disnake.Color.yellow(),
        ).set_footer(text="Для служебного использования")
        patent_embed.description = f"""\
`Субъект:` {db_patent.subject}
`Тип:` {'арт' if db_patent.is_art else 'другое'}
`Номера карт:` {', '.join([f'#{map_number}' for map_number in db_patent.map_ids.split(";")])
        if db_patent.map_ids else 'нет'}
`Владельцы:` {', '.join([f'<@{owner}>' for owner in db_patent.owner_ids.split(";")])}
`Зарегистрирован:` GMT+3 {db_patent.registration_date} 
`Банкир:` <@{db_patent.banker_id}>
`Модератор:` {('<@' + str(db_patent.moderator_id) + '>') if db_patent.moderator_id else 'Нет'}
`Message ID:` https://discord.com/channels/{settings.economy_guild.discord_id}\
/{settings.ECONOMY_PATENTS_PUBLIC_CHANNEL_ID}/{db_patent.message_id}
`Разделение цен:` {db_patent.price_breakdown}
`Холд на счете DD Банка:` {db_patent.is_payment_on_hold}
`Карта оплаты:` {db_patent.from_card_str}
`Оформлен возврат:` {db_patent.is_refunded}
`Ламинирование:` {not db_patent.is_lamination_skipped if db_patent.is_lamination_skipped is not None else 'Не нужно'}

`Статус:` {db_patent.status}               
        """
        return patent_embed

    if not for_internal_use:
        if db_patent.status in ["APPROVED", "AUTOAPPROVED"]:
            patent_color = disnake.Color.green()
        elif db_patent.status in "REJECTED":
            patent_color = disnake.Color.dark_red()
        else:
            patent_color = disnake.Color.dark_gray()

        patent_embed = disnake.Embed(
            title="Патент №" + formatters.format_patent_number(patent_id),
            color=patent_color,
        )

        patent_embed.description = f"`Субъект:` {db_patent.subject}\n"
        if db_patent.is_art:
            if db_patent.map_ids is not None:
                map_numbers = [
                    ("#" + str(map_number))
                    for map_number in db_patent.map_ids.split(";")
                ]
            else:
                map_numbers = []
            if len(map_numbers) == 1:
                patent_embed.description += f"`Номер карты:` {map_numbers[0]}\n"
            else:
                patent_embed.description += f"`Номера карт:` {', '.join(map_numbers)}\n"

        patent_embed.description += "\n"

        owner_ids = [owner for owner in db_patent.owner_ids.split(";")]
        if len(owner_ids) == 1:
            patent_embed.description += f"`Владелец:` <@{owner_ids[0]}>\n"
        else:
            patent_embed.description += (
                f"`Владельцы:` {', '.join([f'<@{owner}>' for owner in owner_ids])}\n"
            )

        patent_statuses = {
            "WAIT": "⏳ Ожидает рассмотрения",
            "APPROVED": "✅ Активен",
            "REJECTED": "❌ Отклонен",
            "AUTOAPPROVED": "✅ Активен",
        }
        patent_embed.description += f"\n**{patent_statuses[db_patent.status]}**\n"

        return patent_embed


class BankerPatents(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    @commands.default_member_permissions(administrator=True)
    @commands.slash_command(
        name="patent",
        dm_permission=False,
        guild_ids=[
            settings.PlasmoRPGuild.guild_id,
            settings.DevServer.guild_id,
            settings.economy_guild.discord_id,
        ],
    )
    async def patent_slash_command(self, inter: ApplicationCommandInteraction):
        """
        Start registering new patent  {{PATENT_COMMAND}}
        """
        await inter.response.defer(ephemeral=True)

        # Проверка на наличие роли банкира
        if not settings.DEBUG:
            plasmo_guild = self.bot.get_guild(settings.PlasmoRPGuild.guild_id)
            plasmo_banker_role = plasmo_guild.get_role(
                settings.PlasmoRPGuild.banker_role_id
            )
            plasmo_inter_author = plasmo_guild.get_member(inter.author)

            if (
                not plasmo_inter_author
                or plasmo_banker_role not in plasmo_inter_author.roles
            ):
                await inter.edit_original_message(
                    embed=build_simple_embed(
                        description="Вам нужно быть банкиром для использования этой команды",
                        failure=True,
                    )
                )
                return
        patent_preview_embed = disnake.Embed(
            title="Патент XXXX",
            description=f"`Банкир:`{inter.author.mention}",
            color=disnake.Color.yellow(),
        ).set_footer(text="Превью")

        # Выбор клиента
        patent_helper_embed = disnake.Embed(
            color=disnake.Color.dark_green(),
        )
        patent_helper_embed.title = "Выбор клиента"
        patent_helper_embed.description = """
Укажите дискорд аккаунт **КЛИЕНТА**. 

Нужно указать именно того человека, который пришел оформлять патент, независимо от того кто будет указан \
как владелец свидетельства
"""
        if inter.guild_id != settings.PlasmoRPGuild.guild_id:
            patent_helper_embed.description += (
                "\n\n"
                "⚠️**Вы оформляете патент не в дискорде Plasmo. Клиента может не"
                " быть на этом сервере. В таком случае вам придется пригласить его"
                " вручную**"
            )
        client_select_view = ClientSelectView()
        await inter.edit_original_message(
            embeds=[patent_preview_embed, patent_helper_embed],
            view=client_select_view,
        )
        await client_select_view.wait()
        if client_select_view.client is None:
            return await inter.delete_original_response()
        client: disnake.Member = client_select_view.client
        del client_select_view
        patent_preview_embed.description += f"\n`Клиент:`{client.mention}"

        # Тип патента
        patent_helper_embed.title = "Тип патента"
        patent_helper_embed.description = """\
Прочитайте вслух или отправьте в чат текст
```
Для начала нужно указать тип: вы собираетесь патентовать мапарт или что-то другое?
```
        
**Выберите тип патента**
        """
        patent_type_view = PatentTypeView()
        await inter.edit_original_message(
            embeds=[patent_preview_embed, patent_helper_embed], view=patent_type_view
        )
        await patent_type_view.wait()
        if patent_type_view.is_mapart is None:
            return await inter.delete_original_response()
        is_mapart = patent_type_view.is_mapart
        del patent_type_view
        patent_preview_embed.description += (
            f"\n`Тип:` {'Мапарт' if is_mapart else 'Другое'}"
        )

        # Базовая цена для обычных патентов
        patent_price_for_economy = 10
        patent_price_for_moderator = 5
        patent_price_for_banker = 10

        maps_count: Optional[int] = None
        # Для мапартов: количество карт, клиент, номера, передача артов банкиру, наличие лицензии артодела
        if is_mapart:
            # Подтверждение наличия карт на руках
            patent_helper_embed.title = "Подтверждение наличия карт"
            patent_helper_embed.description = """
            Прочитайте вслух или отправьте в чат текст.
            ```Чтобы запатентовать арт, нужно иметь с собой оригиналы всех карт. Они сейчас у вас на руках?```

            **Укажите ответ клиента**"""
            patent_price_confirm_view = ConfirmationView()
            await inter.edit_original_message(
                embeds=[patent_preview_embed, patent_helper_embed],
                view=patent_price_confirm_view,
            )
            await patent_price_confirm_view.wait()
            if (
                patent_price_confirm_view.decision is None
                or patent_price_confirm_view.decision is False
            ):
                return await inter.delete_original_response()
            if not patent_price_confirm_view.decision:
                return await inter.delete_original_response()

            # Количество карт в арте
            patent_helper_embed.title = "Количество карт в арте"
            patent_helper_embed.description = """

Прочитайте вслух или отправьте в чат текст
```
Цена за патент на мапарт формируется из количества карт, сколько карт в арте, который вы патентуете?
```

**Укажите количество карт**
            """
            maps_count_view = MapsCountView(bot=self.bot)
            await inter.edit_original_message(
                embeds=[patent_preview_embed, patent_helper_embed], view=maps_count_view
            )
            await maps_count_view.wait()
            if maps_count_view.maps_count is None:
                return await inter.delete_original_response()
            maps_count = maps_count_view.maps_count
            del maps_count_view
            patent_preview_embed.description += f"\n`Количество карт:` {maps_count}"

            # Формирование цены
            patent_price_for_economy = 15
            patent_price_for_moderator = 0
            if maps_count < 3:
                patent_price_for_banker = 5
            elif maps_count < 6:
                patent_price_for_banker = 10
            elif maps_count < 11:
                patent_price_for_banker = 15
            else:
                patent_price_for_banker = 20

            # Проверка на наличие лицензии артодела
            has_license = False
            economy_guild = self.bot.get_guild(settings.economy_guild.discord_id)
            if not economy_guild:
                raise RuntimeError("Economy guild not found, unable to register patent")
            economy_guild_member = economy_guild.get_member(client.id)
            if economy_guild_member:
                economy_guild_license_role = economy_guild.get_role(
                    settings.ECONOMY_ARTODEL_LICENSE_ROLE_ID
                )
                if economy_guild_license_role in economy_guild_member.roles:
                    has_license = True
            patent_preview_embed.description += "\n`Лицензия артодела:` " + (
                "найдена" if has_license else "не найдена"
            )
            if has_license:
                patent_price_for_economy -= 10
                patent_preview_embed.description += "\n`Скидка по лицензии:` 10"

        patent_preview_embed.description += (
            f"\n`Распределение цены:` E{patent_price_for_economy}"
            f"M{patent_price_for_moderator}B{patent_price_for_banker}"
        )
        total_patent_price = sum(
            [
                patent_price_for_economy,
                patent_price_for_moderator,
                patent_price_for_banker,
            ]
        )
        patent_preview_embed.description += "\n`Стоимость:`" + str(total_patent_price)

        # Подтверждение цены
        patent_helper_embed.title = "Подтверждение цены"
        patent_helper_embed.description = f"""
Прочитайте вслух или отправьте в чат текст
```Цена за оформление патента составит \
{sum([patent_price_for_economy, patent_price_for_moderator, patent_price_for_banker])} алм. Вы хотите продолжить?```

**Укажите решение клиента**"""
        patent_price_confirm_view = ConfirmationView()
        await inter.edit_original_message(
            embeds=[patent_preview_embed, patent_helper_embed],
            view=patent_price_confirm_view,
        )
        await patent_price_confirm_view.wait()
        if (
            patent_price_confirm_view.decision is None
            or patent_price_confirm_view.decision is False
        ):
            return await inter.delete_original_response()
        if not patent_price_confirm_view.decision:
            return await inter.delete_original_response()

        if is_mapart:
            # Получение карт на руки
            patent_helper_embed.title = "Получение карт"
            patent_helper_embed.description = f"""
            Прочитайте вслух или отправьте в чат текст
            ```Пожалуйста, передайте мне все части вашего арта```

            **Подтвердите получение карт от клиента в количестве {maps_count} шт.**"""
            confirm_view = ConfirmationView()
            await inter.edit_original_message(
                embeds=[patent_preview_embed, patent_helper_embed], view=confirm_view
            )
            await confirm_view.wait()
            if confirm_view.decision is None or confirm_view.decision is False:
                return await inter.delete_original_response()

        # Указание названия
        patent_helper_embed.title = "Название патента"
        if is_mapart:
            patent_helper_embed.description = """
Прочитайте вслух или отправьте в чат текст
```
Как называется арт, который вы патентуете?
```

⚠️ **Учтите что "арт" в название подставится автоматически. Вам нужно указать только название арта.**
`Пример:` Арт называется "Прогресс невозможнен без пива". Вам нужно написать только "Прогресс невозможен без пива". \
Патент будет называться «арт "Прогресс невозможен без пива"»
    
**Укажите название арта**"""
        else:
            patent_helper_embed.description = """
Прочитайте вслух или отправьте в чат текст
```
Как будет называться ваш патент?
```

`Пример 1:` Патент называется "Патент на комара". Вам нужно написать "Комар"
 
`Пример 2:` Патент называется "Патент на то, чтобы создавать баннеры из баннеров".\
 Вам нужно написать "Создание баннеров из баннеров" 

**Укажите название патента**"""
        patent_name_view = PatentNameView(bot=self.bot)
        await inter.edit_original_message(
            embeds=[patent_preview_embed, patent_helper_embed],
            view=patent_name_view,
        )
        await patent_name_view.wait()
        if patent_name_view.patent_name is None:
            return await inter.delete_original_response()
        if is_mapart:
            patent_name = f'арт "{patent_name_view.patent_name}"'
        else:
            patent_name = patent_name_view.patent_name
        del patent_name_view
        patent_preview_embed.description = (
            f"`Субъект:` {patent_name}\n" + patent_preview_embed.description
        )

        # Выбор владельцев
        patent_helper_embed.title = "Выбор владельцев"
        patent_helper_embed.description = """
Прочитайте вслух или отправьте в чат текст
```Нужно выбрать владельцев патента. Свой ник указывать необязательно, но необходимо, если вы хотите быть в списке.\
 Можно выбрать от одного до 16 игроков```

Клиент не подставляется в список владельцев автоматически!

**Выберите всех владельцев патента в селекте и нажмите кнопку чтобы подтверить выбор**"""
        if inter.guild_id != settings.PlasmoRPGuild.guild_id:
            patent_helper_embed.description += (
                "\n\n"
                "⚠️**Вы оформляете патент не в дискорде Plasmo. Владельцев может не"
                " быть на этом сервере. В таком случае вам придется пригласить их"
                " вручную**"
            )
        patent_owners_view = PatentOwnersView()
        await inter.edit_original_message(
            embeds=[patent_preview_embed, patent_helper_embed],
            view=patent_owners_view,
        )
        await patent_owners_view.wait()
        if patent_owners_view.patent_owners is None:
            return await inter.delete_original_response()
        patent_owners = patent_owners_view.patent_owners
        del patent_owners_view
        patent_preview_embed.description += (
            "\n`Владел"
            + ("ец" if len(patent_owners) == 1 else "ьцы")
            + ":` "
            + ", ".join([user.mention for user in patent_owners])
        )

        # Выбор карты
        patent_helper_embed.title = "Стадия оплаты"
        patent_helper_embed.description = """
Прочитайте вслух или отправьте в чат текст
```Нужно оплатить создание патента. На какую карту вам выставить счет?```

**⚠️ Поддерживаются только карты Е-Банка**
`Пример 1:` Карта EB-5930, вы должны ввести 5930
`Пример 2:` Карта EB-0004, вы должны ввести 4 или 0004

**Введите номер карты, которую указал клиент **"""
        bank_card_selection_view = BankCardSelectionView(bot=self.bot)
        await inter.edit_original_message(
            embeds=[patent_preview_embed, patent_helper_embed],
            view=bank_card_selection_view,
        )
        await bank_card_selection_view.wait()
        if bank_card_selection_view.card_id is None:
            return await inter.delete_original_response()
        card_number = bank_card_selection_view.card_id
        card_bank = bank_card_selection_view.bank_code
        card_api_data = bank_card_selection_view.card_api_data
        del bank_card_selection_view

        patents_payout_project = await models.StructureProject.objects.filter(
            name="Патенты",
            guild_discord_id=settings.economy_guild.discord_id,
            from_card_str=settings.DD_BANK_PATENTS_CARD,
        ).first()
        if patents_payout_project is None:
            await self.bot.get_channel(settings.ECONOMY_DD_OPERATIONS_CHANNEL_ID).send(
                embed=build_simple_embed(
                    description="Unable to get project for payout", failure=True
                )
            )
            raise RuntimeError("Unable to get project for payout")

        await inter.edit_original_response(components=[])
        # todo: нормальная заглушка

        # Оплата
        try:
            bill_id = await bank_api.bill(
                from_card_str=settings.DD_BANK_PATENTS_CARD,
                to_card_str=formatters.format_bank_card(
                    card_api_data["id"], bank_prefix=card_bank
                ),
                amount=total_patent_price,
                message=f"Оплата патента на {patent_name}. Банкир {inter.author.display_name}",
                token=patents_payout_project.plasmo_bearer_token,
            )
        except BankAPIError as e:
            await inter.edit_original_message(
                embeds=[
                    patent_preview_embed,
                    build_simple_embed(
                        "Произошла неизвестная ошибка. Невозможно провести оплату патента:"
                        + str(e),
                        failure=True,
                    ),
                ]
            )
            return await self.bot.get_channel(
                settings.ECONOMY_DD_OPERATIONS_CHANNEL_ID
            ).send(
                embed=disnake.Embed(
                    description=f"{formatters.format_bank_card(number=4, bank_prefix='DD')}"
                    f" -> {formatters.format_bank_card(number=card_number, bank_prefix=card_bank)}\n"
                    f"Не удалось выставить счет. Ошибка: {e}\n"
                )
            )

        if bill_id is None:
            return await inter.edit_original_message(
                embeds=[
                    patent_preview_embed,
                    build_simple_embed(
                        "Произошла неизвестная ошибка. Невозможно провести оплату патента",
                        failure=True,
                    ),
                ]
            )
        await self.bot.get_channel(settings.ECONOMY_DD_OPERATIONS_CHANNEL_ID).send(
            embed=disnake.Embed(
                description=f"{settings.DD_BANK_PATENTS_CARD}"
                f" -> {formatters.format_bank_card(number=card_number, bank_prefix=card_bank)}\n"
                f"Счет {bill_id} на {total_patent_price} алм. выставлен на карту {card_number}\n"
                f"`Банкир:` {inter.author.mention}\n`Клиент:` {client.mention}\n"
                f"`Сообщение:` "
                + f"Оплата патента на {patent_name}. Банкир {inter.author.display_name}"
            )
        )
        patent_helper_embed.description = f"""Прочитайте вслух или отправьте в чат текст
```DD Bank выставил на карту \
{formatters.format_bank_card(number=card_api_data['id'], bank_prefix=card_api_data['bank_code'])} \
счет в размере {total_patent_price} алм. \
У вас есть 5 минут чтобы оплатить его```

**Ожидание оплаты...**"""
        await inter.edit_original_message(
            embeds=[patent_preview_embed, patent_helper_embed], components=[]
        )
        is_paid, bill_declined = await bank_api.wait_for_bill(
            card_str=settings.DD_BANK_PATENTS_CARD,
            bill_id=bill_id,
            token=patents_payout_project.plasmo_bearer_token,
            time=300,
        )
        if bill_declined:
            await inter.edit_original_message(
                embeds=[
                    patent_preview_embed,
                    build_simple_embed(
                        "Счет был отклонен. Невозможно провести оплату патента",
                        failure=True,
                    ),
                ]
            )
            return await self.bot.get_channel(
                settings.ECONOMY_DD_OPERATIONS_CHANNEL_ID
            ).send(embed=disnake.Embed(description=f"Счет {bill_id} отклонён"))
        if not is_paid:
            await inter.edit_original_message(
                embeds=[
                    patent_preview_embed,
                    build_simple_embed(
                        "Время ожидания оплаты истекло. Невозможно провести оплату патента",
                        failure=True,
                    ),
                ]
            )
            await self.bot.get_channel(settings.ECONOMY_DD_OPERATIONS_CHANNEL_ID).send(
                embed=disnake.Embed(
                    description=f"Счет {bill_id} истек или был отклонен DD банком вручную"
                )
            )
            return await bank_api.cancel_bill(
                card_str=settings.DD_BANK_PATENTS_CARD,
                bill_id=bill_id,
                token=patents_payout_project.plasmo_bearer_token,
            )
        await self.bot.get_channel(settings.ECONOMY_DD_OPERATIONS_CHANNEL_ID).send(
            embed=disnake.Embed(
                description=f"Счет {bill_id} на {total_patent_price} алм. оплачен"
            )
        )
        patent_helper_embed.description = """Прочитайте вслух или отправьте в чат текст
```Оплата прошла. Ваш патент регистрируется```

**Это сообщение пропадет через 10 секунд...**"""
        await inter.edit_original_message(
            embeds=[patent_preview_embed, patent_helper_embed], components=[]
        )

        # Регистрация патента в базе данных
        db_patent = await models.Patent.objects.create(
            subject=patent_name,
            is_art=is_mapart,
            owner_ids=";".join([str(owner.id) for owner in patent_owners]),
            registration_date=datetime.datetime.now(),
            banker_id=inter.author.id,
            status="WAIT",
            moderator_id=self.bot.user.id if is_mapart else None,
            message_id=None,
            price_breakdown=f"{patent_price_for_economy};{patent_price_for_moderator};{patent_price_for_banker}",
            is_payment_on_hold=True,
            from_card_str=formatters.format_bank_card(
                number=card_number, bank_prefix=card_bank
            ),
        )
        for owner in patent_owners:
            await send_mc_message(
                message=f"На ваше имя зарегистрирован патент {db_patent.id} - {db_patent.subject}",
                discord_id=owner.id,
                even_if_offline=False,
            )
        await self.bot.get_channel(settings.ECONOMY_PATENTS_NUMBERS_CHANNEL_ID).send(
            formatters.format_patent_number(db_patent.id)
        )
        await asyncio.sleep(10)

        patent_preview_embed.title = "Патент " + formatters.format_patent_number(
            db_patent.id
        )
        patent_preview_embed.description += "\n`Статус оплаты:` оплачено"

        is_map_lamination_skipped = None
        map_numbers = []
        if is_mapart:
            # Ламинирование карт
            patent_helper_embed.title = "Ламинирование карт"
            patent_helper_embed.description = """Прочитайте вслух или отправьте в чат текст
```Патент зарегистрирован. Ваш арт можно заламинировать. Ламинирование арта добавит в описание всех карт номер \
патента и уберет возможность копировать копии оригиналов карт. => вы сможете смело продавать копии арта и никто не \
сможет их скопировать. Ламинировать ваш арт?``` 

**Укажите ответ клиента**
   """
            aproval_view = ConfirmOrDenyView()
            await inter.edit_original_message(
                embeds=[patent_preview_embed, patent_helper_embed],
                view=aproval_view,
            )
            await aproval_view.wait()
            if aproval_view.accepted is True:
                is_map_lamination_skipped = False
                patent_preview_embed.description += (
                    "\n`Согласие на ламинирование:` есть"
                )
                mc_command_owner = "PlasmoTools"
                laminated_map_numbers = []
                for _ in range(maps_count):
                    patent_helper_embed.description = f"""Поочередно возьмите в основную руку все части арта \
и введите команду в чате игры

Команда: `/patent {mc_command_owner} {db_patent.id}`

Заламинированные карты: **{', '.join('#' + str(map_number) for map_number in laminated_map_numbers)
                    if laminated_map_numbers else 'не'}**

Бот автоматически поймет когда вы запатентовали карту и оповестит вас 
**У вас 180 секунд на каждую карту, в ином случае ламинация карт будет отменена**"""
                    await inter.edit_original_message(
                        embeds=[patent_preview_embed, patent_helper_embed],
                        view=None,
                    )

                    def patent_registration_message_check(message: disnake.Message):
                        if message.channel.id not in [
                            1137803532943233154,
                            951769772683587604,
                        ] or (
                            len(message.embeds) != 1
                            or message.embeds[0].description is None
                        ):
                            return False
                        results = re.findall(
                            r"<@!?(\d+)> запатентовал карту #([0-9]{1,5}) в ([a-zA-Z_]+) "
                            r"\(патент #([0-9]{1,5}), владелец: <@!?(\d+)>\)",
                            message.embeds[0].description,
                        )
                        if len(results) != 1:
                            return False
                        if results[0][3] != formatters.format_patent_number(
                            db_patent.id
                        ):
                            return False

                        if int(results[0][1]) in laminated_map_numbers:
                            return False

                        # result[0]: banker_id, card_number, world_name, patent_id, owner_id
                        laminated_map_numbers.append(int(results[0][1]))
                        return True

                    try:
                        await self.bot.wait_for(
                            "message",
                            check=patent_registration_message_check,
                            timeout=180,
                        )
                        continue
                    except asyncio.TimeoutError:
                        is_map_lamination_skipped = True
                        patent_preview_embed.description += (
                            "\n`Согласие на ламинирование:` отсутствует"
                        )
                        break
                map_numbers = laminated_map_numbers
                patent_helper_embed.description = """Прочитайте вслух или отправьте в чат текст
```Все карты успешно заламинированы. Вы можете забрать их. Регистрация патента завершена, если вам нужна физическая \
версия вашего патента, в виде подписанной главой экономики книги, вы всегда можете обратиться в тикеты в дискорде \
структуры```
 
 
 **Патент оформлен. Отдайте все части мапарта. Можете отпустить клиента**"""
            else:
                is_map_lamination_skipped = True
                patent_preview_embed.description += (
                    "\n`Согласие на ламинирование:` отсутствует"
                )

                # Получение номеров карт
                patent_helper_embed.title = "Получение номеров карт"
                for _ in range(maps_count):
                    patent_helper_embed.description = f"""
                            Введите номера карт в любом порядке.

                            Введено {len(map_numbers)} / {maps_count}

                            Указанные карты: {', '.join(map(str, map_numbers)) if map_numbers else 'нет'}

                            **Нажимайте 'Ввести номер карты N' и вводите номер карты по одному**"""
                    specify_card_number_view = SpecifyMapNumberView(
                        map_index=len(map_numbers) + 1,
                        bot=self.bot,
                        selected_maps=map_numbers,
                    )
                    await inter.edit_original_message(
                        embeds=[patent_preview_embed, patent_helper_embed],
                        view=specify_card_number_view,
                    )
                    await specify_card_number_view.wait()
                    if specify_card_number_view.map_number is None:
                        return await inter.delete_original_response()
                    map_numbers.append(specify_card_number_view.map_number)
                    del specify_card_number_view
                patent_helper_embed.description = """Прочитайте вслух или отправьте в чат текст
```Регистрация патента завершена, если вам нужна физическая версия вашего патента, в виде подписанной главой \
экономики книги, вы всегда можете обратиться в тикеты в дискорде структуры```

**Патент оформлен. Можете отпустить клиента**"""
            patent_preview_embed.description += (
                f"\n`Номера карт:` {', '.join(map(str, map_numbers))}"
            )
        else:
            patent_helper_embed.description = """Прочитайте вслух или отправьте в чат текст
```Регистрация патента завершена. Ваш патент отправлен на модерацию. Решение команды экономики \
можно будет узнать в дискорде структуры: https://discord.gg/6sKKGPuhRk```

**Патент оформлен. Можете отпустить клиента**"""

        patent_helper_embed.title = "Патент оформлен"
        await inter.edit_original_message(
            embeds=[patent_preview_embed, patent_helper_embed],
            view=None,
        )
        await models.Patent.objects.filter(id=db_patent.id).update(
            is_lamination_skipped=is_map_lamination_skipped,
            map_ids=";".join([str(map_number) for map_number in map_numbers])
            if is_mapart
            else None,
        )

        await self._moderate_patent(patent_id=db_patent.id)

    @commands.message_command(
        name=Localized("Reject Patent", key="REJECT_PATENT_MESSAGE_COMMAND_NAME"),
        guild_ids=[settings.economy_guild.discord_id],
    )
    @commands.default_member_permissions(administrator=True)
    async def reject_patent_message_command(
        self, inter: MessageInteraction, message: disnake.Message
    ):
        await inter.response.defer(ephemeral=True)
        if (
            message.channel.id != settings.ECONOMY_PATENTS_PUBLIC_CHANNEL_ID
            or message.author.id != self.bot.user.id
        ):
            await inter.edit_original_response(
                embed=build_simple_embed(
                    description="Невозможно отклонить этот патент", failure=True
                ),
            )
            return

        db_patent = await models.Patent.objects.filter(message_id=message.id).first()
        if db_patent is None:
            return await inter.edit_original_response(
                embed=build_simple_embed(description="Патент не найден", failure=True),
            )

        if db_patent.status == "REJECTED":
            return await inter.edit_original_response(
                embed=build_simple_embed(
                    description="Патент уже отклонён", failure=True
                ),
            )
        await models.Patent.objects.filter(id=db_patent.id).update(
            status="REJECTED",
            moderator_id=inter.author.id,
        )
        await self.bot.get_channel(settings.ECONOMY_PATENTS_MODERATOR_CHANNEL_ID).send(
            embeds=[
                await _get_patent_embed(patent_id=db_patent.id, for_internal_use=True),
                build_simple_embed(
                    description=f"Патент вручную отклонён модератором {inter.author.mention}\n"
                    f"Фича возврата денег за такие отмены не реализована"
                ),
            ],
        )
        await message.edit(
            embed=await _get_patent_embed(
                patent_id=db_patent.id, for_internal_use=False
            ),
        )
        await inter.edit_original_response(
            embed=build_simple_embed(description="Патент отклонён"),
        )

    async def _moderate_patent(self, patent_id: int):
        db_patent = await models.Patent.objects.get(id=patent_id)
        if db_patent.status != "WAIT":
            return False

        if db_patent.is_art:
            await models.Patent.objects.filter(id=db_patent.id).update(
                status="AUTOAPPROVED"
            )
            public_embed = await _get_patent_embed(
                patent_id=db_patent.id, for_internal_use=False
            )
            await models.Patent.objects.filter(id=db_patent.id).update(
                message_id=(
                    await self.bot.get_channel(
                        settings.ECONOMY_PATENTS_PUBLIC_CHANNEL_ID
                    ).send(
                        embed=public_embed,
                        content=", ".join(
                            [
                                ("<@" + owner_id + ">")
                                for owner_id in db_patent.owner_ids.split(";")
                            ]
                        ),
                    )
                ).id
            )
            internal_embed = await _get_patent_embed(
                patent_id=db_patent.id, for_internal_use=True
            )
            await self.bot.get_channel(
                settings.ECONOMY_PATENTS_MODERATOR_CHANNEL_ID
            ).send(embed=internal_embed)
            await self._payout_for_patent(patent_id=patent_id)
        else:
            internal_embed = await _get_patent_embed(
                patent_id=db_patent.id, for_internal_use=True
            )
            await self.bot.get_channel(
                settings.ECONOMY_PATENTS_MODERATOR_CHANNEL_ID
            ).send(
                content=f"<@&{settings.ECONOMY_PATENTS_MODERATOR_ROLE_ID}>",
                embed=internal_embed,
                components=[
                    disnake.ui.Button(
                        style=disnake.ButtonStyle.green,
                        label="Одобрить",
                        custom_id=f"patent_approve:{db_patent.id}",
                    ),
                    disnake.ui.Button(
                        style=disnake.ButtonStyle.red,
                        label="Отклонить",
                        custom_id=f"patent_reject:{db_patent.id}",
                    ),
                ],
            )

    async def _process_moderator_decision(
        self, patent_id: int, approoved: bool, moderator_id: int
    ):
        db_patent = await models.Patent.objects.get(id=patent_id)
        if db_patent.status != "WAIT":
            return False

        await models.Patent.objects.filter(id=db_patent.id).update(
            status="APPROVED" if approoved else "REJECTED",
            moderator_id=moderator_id,
        )

        patent_message = await self.bot.get_channel(
            settings.ECONOMY_PATENTS_PUBLIC_CHANNEL_ID
        ).send(
            embed=await _get_patent_embed(
                patent_id=db_patent.id, for_internal_use=False
            ),
            content=", ".join(
                [("<@" + owner_id + ">") for owner_id in db_patent.owner_ids.split(";")]
            ),
        )
        await models.Patent.objects.filter(id=db_patent.id).update(
            message_id=patent_message.id
        )

        await self._payout_for_patent(patent_id=patent_id)

    async def _payout_for_patent(self, patent_id: int):
        db_patent = await models.Patent.objects.get(id=patent_id)
        if (
            db_patent.status == "WAIT"
            or not db_patent.is_payment_on_hold
            or db_patent.is_refunded
        ):
            return False

        payouts_cog = self.bot.get_cog("Payouts")
        if payouts_cog is None:
            await self.bot.get_channel(settings.ECONOMY_DD_OPERATIONS_CHANNEL_ID).send(
                embed=build_simple_embed(
                    description="Unable to get Payments cog", failure=True
                )
            )
            raise RuntimeError("Payouts cog unavailable")

        patents_payout_project = await models.StructureProject.objects.filter(
            name="Патенты",
            guild_discord_id=settings.economy_guild.discord_id,
            from_card_str=settings.DD_BANK_PATENTS_CARD,
        ).first()
        if patents_payout_project is None:
            await self.bot.get_channel(settings.ECONOMY_DD_OPERATIONS_CHANNEL_ID).send(
                embed=build_simple_embed(
                    description="Unable to get projects for payout", failure=True
                )
            )
            raise RuntimeError("Unable to get projects for payout")

        if db_patent.status in ["APPROVED", "AUTOAPPROVED"]:
            economics_price, moderator_price, banker_price = tuple(
                map(int, db_patent.price_breakdown.split(";"))
            )

            if economics_price > 0:
                payment_status, _ = await bank_api.transfer(
                    from_card_str=settings.DD_BANK_PATENTS_CARD,
                    to_card_str=settings.ECONOMY_PATENTS_TREASURY_CARD,
                    amount=economics_price,
                    token=patents_payout_project.plasmo_bearer_token,
                    message=f"Налог за оформление патента {formatters.format_patent_number(db_patent.id)}",
                )
                await self.bot.get_channel(
                    settings.ECONOMY_DD_OPERATIONS_CHANNEL_ID
                ).send(
                    content=(
                        "<@&" + str(settings.ECONOMY_FAILED_PAYMENTS_ROLE_ID) + ">"
                    )
                    if not payment_status
                    else None,
                    embed=disnake.Embed(
                        description=f"{settings.DD_BANK_PATENTS_CARD} -> {settings.ECONOMY_PATENTS_TREASURY_CARD}\n"
                        f"`Amount:` {economics_price}\n`Message:` "
                        f"Налог за оформление патента {formatters.format_patent_number(db_patent.id)}\n"
                        f"`Статус:` {payment_status}"
                    ),
                )
            if moderator_price > 0:
                moderator = self.bot.get_guild(
                    settings.economy_guild.discord_id
                ).get_member(db_patent.moderator_id)
                if moderator is None or moderator.id == self.bot.user.id:
                    await self.bot.get_channel(
                        settings.ECONOMY_DD_OPERATIONS_CHANNEL_ID
                    ).send(
                        embed=build_simple_embed(
                            description=f"Unable to get moderator for patent {db_patent.id}",
                            failure=True,
                        )
                    )
                else:
                    payment_status = await payouts_cog.payout(
                        user=moderator,
                        amount=moderator_price,
                        project=patents_payout_project,
                        message="За модерацию патента",
                        transaction_message="За модерирование патента "
                        + formatters.format_patent_number(db_patent.id),
                        author=self.bot.get_guild(
                            settings.economy_guild.discord_id
                        ).get_member(self.bot.user.id),
                    )
                    await self.bot.get_channel(
                        settings.ECONOMY_DD_OPERATIONS_CHANNEL_ID
                    ).send(
                        content=(
                            "<@&" + str(settings.ECONOMY_FAILED_PAYMENTS_ROLE_ID) + ">"
                        )
                        if not payment_status
                        else None,
                        embed=disnake.Embed(
                            description=f"{settings.DD_BANK_PATENTS_CARD} -> {moderator.mention}\n"
                            f"`Amount:` {moderator_price}\n`Message:` "
                            f"За модерирование патента {formatters.format_patent_number(db_patent.id)}\n"
                            f"`Статус:` {payment_status}"
                        ),
                    )
            if banker_price > 0:
                banker = self.bot.get_guild(
                    settings.economy_guild.discord_id
                ).get_member(db_patent.banker_id)
                if banker is None or banker.id == self.bot.user.id:
                    await self.bot.get_channel(
                        settings.ECONOMY_DD_OPERATIONS_CHANNEL_ID
                    ).send(
                        embed=build_simple_embed(
                            description=f"Unable to get banker for patent {db_patent.id}",
                            failure=True,
                        )
                    )
                else:
                    payment_status = await payouts_cog.payout(
                        user=banker,
                        amount=banker_price,
                        project=patents_payout_project,
                        message="За оформление патента",
                        transaction_message="За оформление патента "
                        + formatters.format_patent_number(db_patent.id),
                        author=self.bot.get_guild(
                            settings.economy_guild.discord_id
                        ).get_member(self.bot.user.id),
                    )
                    await self.bot.get_channel(
                        settings.ECONOMY_DD_OPERATIONS_CHANNEL_ID
                    ).send(
                        content=(
                            "<@&" + str(settings.ECONOMY_FAILED_PAYMENTS_ROLE_ID) + ">"
                        )
                        if not payment_status
                        else None,
                        embed=disnake.Embed(
                            description=f"{settings.DD_BANK_PATENTS_CARD} -> {banker.mention}\n"
                            f"`Amount:` {banker_price}\n`Message:` "
                            f"За оформление патента {formatters.format_patent_number(db_patent.id)}\n"
                            f"`Статус:` {payment_status}"
                        ),
                    )

            await models.Patent.objects.filter(id=db_patent.id).update(
                is_payment_on_hold=False
            )

        if db_patent.status == "REJECTED":
            economics_price, moderator_price, banker_price = tuple(
                map(int, db_patent.price_breakdown.split(";"))
            )

            if banker_price > 0:
                banker = self.bot.get_guild(
                    settings.economy_guild.discord_id
                ).get_member(db_patent.banker_id)
                if banker is None or banker.id == self.bot.user.id:
                    await self.bot.get_channel(
                        settings.ECONOMY_DD_OPERATIONS_CHANNEL_ID
                    ).send(
                        embed=build_simple_embed(
                            description=f"Unable to get banker for patent {db_patent.id}",
                            failure=True,
                        )
                    )
                else:
                    payment_status = await payouts_cog.payout(
                        user=banker,
                        amount=banker_price,
                        project=patents_payout_project,
                        message="За оформление патента",
                        transaction_message="За оформление отклонённого патента "
                        + formatters.format_patent_number(db_patent.id),
                        author=self.bot.get_guild(
                            settings.economy_guild.discord_id
                        ).get_member(self.bot.user.id),
                    )
                    await self.bot.get_channel(
                        settings.ECONOMY_DD_OPERATIONS_CHANNEL_ID
                    ).send(
                        content=(
                            "<@&" + str(settings.ECONOMY_FAILED_PAYMENTS_ROLE_ID) + ">"
                        )
                        if not payment_status
                        else None,
                        embed=disnake.Embed(
                            description=f"{settings.DD_BANK_PATENTS_CARD} -> {banker.mention}\n"
                            f"`Amount:` {banker_price}\n`Message:` "
                            f"За оформление отклонённого патента"
                            f" {formatters.format_patent_number(db_patent.id)}\n"
                            f"`Статус:` {payment_status}"
                        ),
                    )
            payment_status, _ = await bank_api.transfer(
                from_card_str=settings.DD_BANK_PATENTS_CARD,
                to_card_str=db_patent.from_card_str,
                amount=economics_price + moderator_price,
                token=patents_payout_project.plasmo_bearer_token,
                message=f"Частичный возврат денег за патент {formatters.format_patent_number(db_patent.id)}",
            )
            await self.bot.get_channel(settings.ECONOMY_DD_OPERATIONS_CHANNEL_ID).send(
                content=("<@&" + str(settings.ECONOMY_FAILED_PAYMENTS_ROLE_ID) + ">")
                if not payment_status
                else None,
                embed=disnake.Embed(
                    description=f"{settings.DD_BANK_PATENTS_CARD} -> {settings.ECONOMY_PATENTS_TREASURY_CARD}\n"
                    f"`Amount:` {economics_price + moderator_price}\n`Message:` "
                    f"Частичный возврат денег за патент {formatters.format_patent_number(db_patent.id)}\n"
                    f"`Статус:` {payment_status}"
                ),
            )
            await models.Patent.objects.filter(id=db_patent.id).update(
                is_payment_on_hold=False,
                is_refunded=True,
            )

    @commands.Cog.listener("on_button_click")
    async def on_patent_review(self, inter: MessageInteraction):
        if (
            inter.channel.id != settings.ECONOMY_PATENTS_MODERATOR_CHANNEL_ID
            or not inter.component.custom_id.startswith("patent")
        ):
            return

        if inter.component.custom_id.startswith("patent_approve:"):
            await inter.response.defer(ephemeral=True)
            await inter.message.edit(components=[])
            await self._process_moderator_decision(
                patent_id=int(inter.component.custom_id.split(":")[1]),
                approoved=True,
                moderator_id=inter.author.id,
            )
        elif inter.component.custom_id.startswith("patent_reject:"):
            await inter.response.defer(ephemeral=True)
            await inter.message.edit(components=[])
            await self._process_moderator_decision(
                patent_id=int(inter.component.custom_id.split(":")[1]),
                approoved=False,
                moderator_id=inter.author.id,
            )
        else:
            return

        await inter.message.edit(
            embed=await _get_patent_embed(
                patent_id=int(inter.component.custom_id.split(":")[1]),
                for_internal_use=True,
            ),
            components=[],
        )

    @commands.slash_command(
        name="force-patent", guild_ids=[settings.economy_guild.discord_id]
    )
    @commands.default_member_permissions(administrator=True)
    @commands.is_owner()
    async def force_patent_command(
        self,
        inter: ApplicationCommandInteraction,
        subject: str,
        is_art: bool,
        owner_ids: str,
        banker_id: int,
        status: str,
        message_id: int,
        price_breakdown: str,
        is_payment_on_hold: bool,
        is_refunded: bool,
        from_card_str: str,
        patent_id: int,
        moderator_id: int = None,
        map_ids: str = None,
        is_lamination_skipped: bool = None,
        moderate: bool = False,
    ):
        """
        DEBUG COMMAND | Force patent registration/updating

        Parameters
        ----------
        inter: SlashInteraction
        subject: "арт Комар"
        is_art: true
        owner_ids: "123456789012345678;123456789012345678"
        banker_id: 123456789012345678
        status: "WAIT"
        message_id: 123456789012345678
        price_breakdown: "100;0;0"
        is_payment_on_hold: true
        is_refunded: false
        from_card_str: "EB-1234"
        patent_id: 4
        moderator_id: 123456789012345678
        map_ids: "1;2;3"
        is_lamination_skipped: false
        moderate: Whether to moderate patent after registration
        """
        await inter.response.defer(ephemeral=True)

        _, created = await models.Patent.objects.update_or_create(
            id=patent_id,
            defaults={
                "subject": subject,
                "is_art": is_art,
                "owner_ids": owner_ids,
                "banker_id": banker_id,
                "status": status,
                "message_id": message_id,
                "price_breakdown": price_breakdown,
                "is_payment_on_hold": is_payment_on_hold,
                "is_refunded": is_refunded,
                "from_card_str": from_card_str,
                "moderator_id": moderator_id,
                "map_ids": map_ids,
                "is_lamination_skipped": is_lamination_skipped,
            },
        )

        if moderate:
            await self._moderate_patent(patent_id=patent_id)

        await inter.edit_original_message(
            embed=build_simple_embed(description=f"Создан новый: {created}"),
        )

    async def cog_load(self):
        logger.info("%s loaded", __name__)

    # todo: /get-patent id:
    # todo: patents in profiles?
    # todo: (maybe) ability to pass payment part if user is bot owner


def setup(client):
    """
    Internal disnake setup function
    """
    client.add_cog(BankerPatents(client))
