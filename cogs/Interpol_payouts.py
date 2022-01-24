import sqlite3
import disnake
import requests
from disnake.ext import commands

import settings


async def autocomplete_card(inter: disnake.ApplicationCommandInteraction, user_input: str):
    if len(user_input) < 2:
        return ['Запрос должен быть длиннее двух символов((']
    try:
        cards_request = requests.get(url=f'https://rp.plo.su/api/bank/search/cards?value={user_input}',
                                     cookies={'rp_token': settings.plasmo_token})
        if cards_request.status_code != 200 or not cards_request.json()['status']:
            return ['Cards not found']
    except Exception as e:
        print(e)
        return ['(']
    if cards_request.json()['data']:
        all_cards = cards_request.json()['data'][:25]
        formatted_cards = []
        for card in all_cards:
            formatted_cards.append(f'EB-{"0" * (4 - len(str(card["id"])))}{card["id"]} '
                                   f'{card["holder"]} - {card["name"]}')
        return formatted_cards
    else:
        return ['(']


async def autocomplete_amount(inter, user_input):
    return [2, 10]


async def autocomplete_payout_message(inter, user_input: str):
    return [message for message in ['За работу на ивенте', 'За ложный вызов'] if user_input.lower() in message]


class InterpolPayouts(commands.Cog):
    def __init__(self, bot):
        self.cursor = None
        self.interpol_guild = None
        self.conn = None
        self.player = None
        self.bot = bot

    async def payout(self):
        pass

    @commands.slash_command(name='установить-карту', guild_ids=[settings.interpol['id']])
    async def setcard(self,
                      inter: disnake.ApplicationCommandInteraction,
                      card: str = commands.Param(autocomplete=autocomplete_card),
                      ):
        """
        Установить карту для выплат Интерпола.

        Parameters
        ----------
        card: Карта для выплат. Найдите карту или введите в формате 3666. Не успевает прогрузить - добавьте пробел
        """
        if self.player not in inter.author.roles:
            return await inter.response.send_message(f'Умный дохуя? Пошел нахуй', ephemeral=True)
        await inter.response.defer(ephemeral=True)

        if not card.startswith('EB-'):
            card = 'EB-' + card[:4]
        plasmo_card = requests.get(f'https://rp.plo.su/api/bank/cards?ids={card}',
                                   cookies={'rp_token': settings.plasmo_token}).json()
        if not plasmo_card['status'] or not plasmo_card['data']:
            return await inter.response.send_message(embed=disnake.Embed(title='Карта не найдена',
                                                                         colour=disnake.Color.red()), ephemeral=True)
        plasmo_card = 'EB-' + '0' * (4 - len(str(plasmo_card['data'][0]['id']))) + str(plasmo_card['data'][0]['id'])
        self.cursor: sqlite3.Cursor
        if self.cursor.execute(f'SELECT * FROM payout_cards WHERE discord_id = {inter.author.id}').fetchone():
            self.cursor.execute(f'UPDATE payout_cards SET card = "{plasmo_card}" WHERE discord_id = {inter.author.id}')
        else:
            self.cursor.execute(f'INSERT INTO payout_cards VALUES ({inter.author.id}, "{plasmo_card}")')

        self.conn.commit()

        return await inter.edit_original_message(embed=disnake.Embed(
            title=f'Card {plasmo_card} was set as a payout card',
            colour=disnake.Color.green()))

    @commands.has_permissions(manage_roles=True)
    @commands.slash_command(name='выплата', guild_ids=[settings.interpol['id']])
    async def force_payout(self,
                           inter: disnake.ApplicationCommandInteraction,
                           user: disnake.User,
                           amount: int = commands.Param(autocomplete=autocomplete_amount),
                           message: str = commands.Param(autocomplete=autocomplete_payout_message)

                           ):
        """
        Выплатить игроку.

        Parameters
        ----------
        user: Участник сервера для найма.
        amount: Количество алмазов
        message: Сообщение
        """
        if self.player not in user.roles:
            return await inter.response.send_message(f'Умный дохуя? Пошел нахуй', ephemeral=True)

    @commands.Cog.listener()
    async def on_ready(self):
        self.interpol_guild = self.bot.get_guild(settings.interpol['id'])
        self.player = self.interpol_guild.get_role(settings.interpol['player'])
        self.conn = sqlite3.connect('interpol.db')
        self.cursor = self.conn.cursor()

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if message.channel.id != settings.interpol['id']:
            pass


def setup(client):
    client.add_cog(InterpolPayouts(client))
