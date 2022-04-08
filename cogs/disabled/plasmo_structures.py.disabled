import logging
import sqlite3

import disnake
import requests
from aiohttp.client import ClientSession
from disnake.ext import commands

import plasmoapi
import settings

logger = logging.getLogger(__name__)


async def autocomplete_bank_card_for_user(
    inter: disnake.ApplicationCommandInteraction, user_input: str
):
    if len(user_input) < 2:
        return await autocomplete_amount(
            inter=inter, user_input=inter.author.display_name
        )

    return await autocomplete_amount(inter=inter, user_input=user_input)


async def autocomplete_bank_card(
    inter: disnake.ApplicationCommandInteraction, user_input: str
):
    if len(user_input) < 2:
        return ["Чтобы вывести подсказки, запрос должен быть длиннее 2х символов"]
    try:
        cards_request = requests.get(
            url=f"https://rp.plo.su/api/bank/search/cards",
            cookies={"rp_token": settings.plasmo_token},
            params={"value": user_input},
        )
        if cards_request.status_code != 200 or not cards_request.json()["status"]:
            return ["Cards not found"]
    except Exception as e:
        logger.warning(e)
        return ["Произошла какая-то ошибка"]
    if cards_request.json()["data"]:
        all_cards = cards_request.json()["data"][:25]
        formatted_cards = []
        for card in all_cards:
            formatted_cards.append(
                f'EB-{"0" * (4 - len(str(card["id"])))}{card["id"]} '
                f'{card["holder"]} - {card["name"]}'
            )
        return formatted_cards
    else:
        return ["Not found"]


class PlasmoStructures(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # async def log_payout(
    #     self,
    #     status: bool,
    #     sender: disnake.User,
    #     user: disnake.User,
    #     amount: int,
    #     message: str,
    #     payout_id: int = None,
    #     error=None,
    #     card=None,
    # ):
    #     if not payout_id:
    #         message = message.replace('"', "'")
    #         self.cursor.execute(
    #             "INSERT INTO payouts "
    #             "(discord_id, sender_id, message, amount, date, card, paid, canceled) "
    #             "VALUES "
    #             f'({user.id}, {sender.id}, "{message}", {amount}, datetime(), {card}, {status}, False)'
    #         )
    #         self.conn.commit()
    #         payout_id = self.cursor.lastrowid
    #     else:
    #         message = message.replace('"', "'")
    #         self.cursor.execute(
    #             f"UPDATE payouts SET "
    #             f"discord_id={user.id}, "
    #             f"sender_id={sender.id}, "
    #             f'message="{message}", '
    #             f"amount={amount}, "
    #             f"date=datetime(), "
    #             f"card={card}, "
    #             f"paid={status},"
    #             f"canceled=False "
    #             f"WHERE id = {payout_id}"
    #         )
    #         self.conn.commit()
    #
    #     if error == "LOWBALANCE":
    #         await self.interpol_guild.get_channel(
    #             settings.interpol["payout_logs"]
    #         ).send(
    #             content=f'<@&{settings.interpol["interpol_head"]}>',
    #             embed=disnake.Embed(
    #                 title="На карте интерпола недостаточно средств",
    #                 description=f"Не удалось выплатить счет на сумму {amount}<:DIAMOND:931501976448012308> игроку"
    #                 f" {user.display_name}",
    #                 color=disnake.Color.red(),
    #             ),
    #         )
    #     elif error == "CARDNOTFOUND":
    #         try:
    #             await user.send(
    #                 content=user.mention,
    #                 embed=disnake.Embed(
    #                     title="Карта не указана",
    #                     description=f"Не удалось выплатить премию в {amount}<:DIAMOND:931501976448012308> потому что "
    #                     f"карта для выплат не указана. \n"
    #                     f"Воспользуйтесь /установить-карту чтобы указать карту для выплат",
    #                     color=disnake.Color.red(),
    #                 ),
    #             )
    #         except Exception as e:
    #             logger.warning(e)
    #             await self.interpol_guild.get_channel(settings.interpol["logs"]).send(
    #                 content=user.mention,
    #                 embed=disnake.Embed(
    #                     title="Карта не указана",
    #                     description=f"Не удалось выплатить премию в {amount}<:DIAMOND:931501976448012308> потому что "
    #                     f"карта для выплат не указана. \n"
    #                     f"Воспользуйтесь /установить-карту в дискорде интерпола чтобы указать карту для "
    #                     f"выплат",
    #                     color=disnake.Color.red(),
    #                 ),
    #             )
    #     elif error:
    #         pass
    #
    #     if status:
    #         async with ClientSession() as session:
    #             webhook = disnake.Webhook.from_url(
    #                 settings.interpol_announcements_webhook_url, session=session
    #             )
    #             log_embed = disnake.Embed(
    #                 description=f"{user.mention} получает выплату в {amount}<:DIAMOND:931501976448012308>\n\n"
    #                 f"Сообщение: {message}",
    #                 color=disnake.Color.red(),
    #             ).set_author(
    #                 name=user.display_name,
    #                 icon_url=f"https://rp.plo.su/avatar/" f"{user.display_name}",
    #             )
    #             log_embed.set_footer(
    #                 text="Выплатил " + sender.display_name,
    #                 icon_url=f"https://rp.plo.su/avatar/{sender.display_name}",
    #             )
    #             await webhook.send(content=user.mention, embed=log_embed)
    #
    #     else:
    #         await self.interpol_guild.get_channel(
    #             settings.interpol["payout_logs"]
    #         ).send(
    #             content="",
    #             embed=disnake.Embed(
    #                 title=f"[{payout_id}] Выплата не удалась",
    #                 description=f"Выплата на сумму {amount}<:DIAMOND:931501976448012308> игроку"
    #                 f" {user.mention} не была закончена\n"
    #                 f"Сообщение: {message}\n"
    #                 f"Выплатил: {sender.mention}",
    #                 color=disnake.Color.red(),
    #             ),
    #         )
    #
    # async def payout(
    #     self,
    #     sender: disnake.User,
    #     user: disnake.User,
    #     amount: int,
    #     message: str,
    #     payout_id=None,
    # ):
    #     payout_card = self.cursor.execute(
    #         f"SELECT card FROM payout_cards WHERE discord_id = {user.id}"
    #     ).fetchone()[0]
    #     if not payout_card:
    #         await self.log_payout(
    #             status=False,
    #             sender=sender,
    #             user=user,
    #             amount=amount,
    #             message=message,
    #             error="CARDNOTFOUND",
    #             payout_id=payout_id,
    #         )
    #         return False
    #
    #     interpol_card = plasmoapi.BankCard(
    #         Bank=self.bank, card_id=settings.interpol["card"]
    #     )
    #     try:
    #         balance = interpol_card.balance
    #     except plasmoapi.ResponseError:
    #         return False  # TODO: Add error logger
    #     if balance < amount:
    #         await self.log_payout(
    #             status=False,
    #             sender=sender,
    #             user=user,
    #             amount=amount,
    #             message=message,
    #             card=int(payout_card.replace("EB-", "")),
    #             error="LOWBALANCE",
    #             payout_id=payout_id,
    #         )
    #         return False
    #
    #     try:
    #         interpol_card.transfer(to=payout_card, amount=amount, message=message)
    #     except plasmoapi.ResponseError:
    #         return False  # TODO: Add logger
    #
    #     await self.log_payout(  # Successful payout
    #         status=True,
    #         sender=sender,
    #         user=user,
    #         amount=amount,
    #         message=message,
    #         card=int(payout_card.replace("EB-", "")),
    #         payout_id=payout_id,
    #     )
    #     return True
    #
    # @commands.slash_command(
    #     name="установить-карту", guild_ids=[settings.interpol["id"]]
    # )
    # async def setcard(
    #     self,
    #     inter: disnake.ApplicationCommandInteraction,
    #     card: str = commands.Param(autocomplete=autocomplete_card),
    # ):
    #     """
    #     Установить карту для выплат Интерпола.
    #
    #     Parameters
    #     ----------
    #     card: Карта для выплат. Найдите карту или введите в формате 3666. Не успевает прогрузить - добавьте пробел
    #     """
    #     if (
    #         self.player not in inter.author.roles
    #         or card == "Not Found"
    #         or card == "An error occurred"
    #     ):
    #         return await inter.response.send_message(
    #             f"Умный дохуя? Пошел нахуй", ephemeral=True
    #         )
    #     await inter.response.defer(ephemeral=True)
    #
    #     if not card.startswith("EB-"):
    #         card = "EB-" + card[:4]
    #     plasmo_card = requests.get(
    #         f"https://rp.plo.su/api/bank/cards?ids={card}",
    #         cookies={"rp_token": settings.plasmo_token},
    #     ).json()
    #     if not plasmo_card["status"] or not plasmo_card["data"]:
    #         return await inter.response.send_message(
    #             embed=disnake.Embed(
    #                 title="Карта не найдена", colour=disnake.Color.red()
    #             ),
    #             ephemeral=True,
    #         )
    #     plasmo_card = (
    #         "EB-"
    #         + "0" * (4 - len(str(plasmo_card["data"][0]["id"])))
    #         + str(plasmo_card["data"][0]["id"])
    #     )
    #     self.cursor: sqlite3.Cursor
    #     if self.cursor.execute(
    #         f"SELECT * FROM payout_cards WHERE discord_id = {inter.author.id}"
    #     ).fetchone():
    #         self.cursor.execute(
    #             f'UPDATE payout_cards SET card = "{plasmo_card}" WHERE discord_id = {inter.author.id}'
    #         )
    #     else:
    #         self.cursor.execute(
    #             f'INSERT INTO payout_cards VALUES ({inter.author.id}, "{plasmo_card}")'
    #         )
    #
    #     self.conn.commit()
    #
    #     return await inter.edit_original_message(
    #         embed=disnake.Embed(
    #             title=f"Card {plasmo_card} was set as a payout card",
    #             colour=disnake.Color.green(),
    #         )
    #     )
    #
    # @commands.has_permissions(manage_roles=True)
    # @commands.slash_command(name="выплата", guild_ids=[settings.interpol["id"]])
    # async def force_payout(
    #     self,
    #     inter: disnake.ApplicationCommandInteraction,
    #     user: disnake.User,
    #     amount: int = commands.Param(autocomplete=autocomplete_amount),
    #     message: str = commands.Param(autocomplete=autocomplete_payout_message),
    # ):
    #     """
    #     Выплатить игроку.
    #
    #     Parameters
    #     ----------
    #     user: Участник сервера для найма.
    #     amount: Количество алмазов
    #     message: Сообщение
    #     """
    #     if self.player not in user.roles:
    #         return await inter.response.send_message(
    #             f"Умный дохуя? Пошел нахуй", ephemeral=True
    #         )
    #     await inter.response.defer(ephemeral=True)
    #     await self.payout(
    #         sender=inter.author,
    #         user=user,
    #         message=message,
    #         amount=amount,
    #     )
    #     await inter.edit_original_message(
    #         embed=disnake.Embed(title="Дело сделано", color=disnake.Color.green())
    #     )
    #
    # """
    # @commands.Cog.listener()
    # async def on_message(self, message: disnake.Message):
    #     if message.channel.id != settings.interpol['payouts']:
    #         return
    #     message: disnake.Message
    #
    #     for word in settings.interpol['event_keywords']:
    #         if word in message.content:
    #             await message.add_reaction(emoji=settings.interpol['event_reaction'])
    #             return
    #
    #     await message.add_reaction(emoji=settings.interpol['fake_call_reaction'])
    # """
    # """
    # @commands.Cog.listener()
    # async def on_raw_reaction_add(self, reaction: disnake.Reaction, user: disnake.Member):
    #     if reaction.message.channel.id != settings.interpol['payouts'] or user.bot:
    #         return
    #     if not (reaction.emoji == settings.interpol['fake_call_reaction'] or
    #             reaction.emoji == settings.interpol['event_reaction']):
    #         return
    #
    #     if not (user.id in self.bot.owner_ids or self.deputy_role in user.roles or self.head_role in user.roles):
    #         await reaction.remove(user)
    #         try:
    #             await user.send(embed=disnake.Embed(title='Вы не можете подтверждать выплаты',
    #                                                 color=disnake.Color.dark_red()))
    #         except Exception as e:
    #             logger.warning(e)
    #         return
    # """

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info("Ready")


def setup(client):
    client.add_cog(PlasmoStructures(client))
    pass  # TODO: Remake
