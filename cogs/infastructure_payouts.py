import sqlite3
import logging

import disnake
from aiohttp.client import ClientSession
from disnake.ext import commands

import settings
import plasmoapi

logger = logging.getLogger(__name__)


async def autocomplete_card(inter: disnake.ApplicationCommandInteraction, user_input: str):
    if len(user_input) < 2:
        user_input = inter.author.display_name
    try:
        async with ClientSession() as session:
            async with session.get(url=f'https://rp.plo.su/api/bank/search/cards?value={user_input}',
                                   cookies={'rp_token': settings.plasmo_token}) as response:
                if response.status != 200 or not (await response.json())['status']:
                    return ['Cards not found']
    except Exception as e:
        print(e)
        return ['An error occurred']
    if (await response.json())['data']:
        all_cards = (await response.json())['data'][:25]
        formatted_cards = []
        for card in all_cards:
            formatted_cards.append(f'EB-{"0" * (4 - len(str(card["id"])))}{card["id"]} '
                                   f'{card["holder"]} - {card["name"]}')
        return formatted_cards
    else:
        return ['Not found']


class InfrastructurePayouts(commands.Cog):
    def __init__(self, bot):
        self.bank = None
        self.head_role = None
        self.deputy_role = None
        self.cursor = None
        self.infrastructure_guild = None
        self.conn = None
        self.player = None
        self.bot = bot

    async def log_payout(self,
                         status: bool,
                         sender: disnake.User,
                         user: disnake.User,
                         amount: int,
                         message: str,
                         payout_id: int = None,
                         error=None,
                         card=None):
        if not payout_id:
            message = message.replace('"', '\'')
            self.cursor.execute('INSERT INTO payouts '
                                '(discord_id, sender_id, message, amount, date, card, paid, canceled) '
                                'VALUES '
                                f'({user.id}, {sender.id}, "{message}", {amount}, datetime(), {card}, {status}, False)')
            self.conn.commit()
            payout_id = self.cursor.lastrowid
        else:
            message = message.replace('"', '\'')
            self.cursor.execute(f'UPDATE payouts SET '
                                f'discord_id={user.id}, '
                                f'sender_id={sender.id}, '
                                f'message="{message}", '
                                f'amount={amount}, '
                                f'date=datetime(), '
                                f'card={card}, '
                                f'paid={status},'
                                f'canceled=False '
                                f'WHERE id = {payout_id}')
            self.conn.commit()

        if error == 'LOWBALANCE':
            logger.warning(f'На карте инфраструктуры недостаточно средств [Amount: {amount}]')
            await self.infrastructure_guild.get_channel(settings.infrastructure['payout_logs']).send(
                content=f'<@&{settings.infrastructure["interpol_head"]}>',
                embed=disnake.Embed(
                    title='На карте интерпола недостаточно средств',
                    description=f'Не удалось выплатить счет на сумму {amount}<:DIAMOND:931501744108748832> игроку'
                                f' {user.display_name}',
                    color=disnake.Color.red()
                )
            )
        elif error == 'CARDNOTFOUND':
            try:
                await user.send(
                    content=user.mention,
                    embed=disnake.Embed(
                        title='[Инфраструктура] Карта не указана',
                        description=f'Выплата в {amount}<:DIAMOND:931501744108748832> была совершена на случайную '
                                    f'карту с вашим именем. \n'
                                    f'Воспользуйтесь /установить-карту чтобы указать другую карту для выплат',
                        color=disnake.Color.red()
                    )
                )
            except Exception as e:
                logger.warning(e)
        elif error:
            logger.warning(error)

        if status:
            logger.info(f'{user.mention}({user.display_name}) получает выплату в {amount} '
                                f'Сообщение: {message}')

            async with ClientSession() as session:
                webhook = disnake.Webhook.from_url(settings.infrastructure_announcements_webhook_url, session=session)
                log_embed = disnake.Embed(
                    description=f'{user.mention} получает выплату в {amount}<:DIAMOND:931501744108748832>\n\n'
                                f'Сообщение: {message}',
                    color=disnake.Color.dark_green()
                ).set_author(name=user.display_name,
                             icon_url=f'https://rp.plo.su/avatar/'
                                      f'{user.display_name}')
                log_embed.set_footer(text='Выплатил ' + sender.display_name,
                                     icon_url=f'https://rp.plo.su/avatar/{sender.display_name}'
                                     )
                await webhook.send(content=user.mention,
                                   embed=log_embed)

        else:
            await self.infrastructure_guild.get_channel(settings.infrastructure['payout_logs']).send(
                content="",
                embed=disnake.Embed(
                    title=f'[{payout_id}] Выплата не удалась',
                    description=f'Выплата на сумму {amount}<:DIAMOND:931501744108748832> игроку'
                                f' {user.mention} не была закончена\n'
                                f'Сообщение: {message}\n'
                                f'Выплатил: {sender.mention}',
                    color=disnake.Color.red(),

                )
            )

    async def payout(self,
                     sender: disnake.User,
                     user: disnake.User,
                     amount: int,
                     message: str,
                     payout_id=None):

        error = None
        payout_card = self.cursor.execute(f'SELECT card FROM payout_cards WHERE discord_id = {user.id}').fetchone()
        if payout_card is None:

            error = 'CARDNOTFOUND'
            async with ClientSession() as session:
                async with session.get(url=f'https://rp.plo.su/api/bank/search/cards?value={user.display_name}',
                                       cookies={'rp_token': settings.plasmo_token}) as response:
                    if response.status != 200 or not (await response.json())['status'] or not (await response.json())['data']:
                        return False

            card = (await response.json())['data'][0]
            payout_card = card['bank_code'] + '-' + str(card['id'])
        else:
            payout_card = payout_card[0]

        infrastructure_card = plasmoapi.BankCard(Bank=self.bank, card_id=settings.infrastructure['card'])
        try:
            balance = infrastructure_card.balance
        except plasmoapi.ResponseError:
            return False
        if balance < amount:
            await self.log_payout(
                status=False,
                sender=sender,
                user=user,
                amount=amount,
                message=message,
                card=int(payout_card.replace('EB-', '')),
                error='LOWBALANCE',
                payout_id=payout_id
            )
            return False

        try:
            infrastructure_card.transfer(to=payout_card,
                                         amount=amount,
                                         message=message)
        except plasmoapi.ResponseError:
            return False  # TODO: Add logger

        await self.log_payout(  # Successful payout
            status=True,
            sender=sender,
            user=user,
            amount=amount,
            error=error,
            message=message,
            card=int(payout_card.replace('EB-', '')),
            payout_id=payout_id
        )
        return True

    @commands.slash_command(name='установить-карту-для-выплат', guild_ids=[settings.infrastructure['id']])
    async def set_card(self,
                       inter: disnake.ApplicationCommandInteraction,
                       card: str = commands.Param(autocomplete=autocomplete_card),
                       ):
        """
        Установить карту для премий.

        Parameters
        ----------
        card: Карта для выплат. Найдите карту или введите в формате 3666. Не успевает прогрузить - добавьте пробел
        """
        if self.player not in inter.author.roles or card == 'Not Found' or card == 'An error occurred':
            return await inter.response.send_message(f'Умный дохуя? Пошел нахуй', ephemeral=True)
        await inter.response.defer(ephemeral=True)

        if not card.startswith('EB-'):
            card = 'EB-' + card[:4]
        async with ClientSession() as session:
            async with session.get(url=f'https://rp.plo.su/api/bank/cards?ids={card}',
                                   cookies={'rp_token': settings.plasmo_token}) as response:
                plasmo_card = await response.json()
                if response.status != 200 or not plasmo_card['data']:
                    return ['Cards not found']
        if not plasmo_card['status'] or not plasmo_card['data']:
            return await inter.edit_original_message(embed=disnake.Embed(title='Карта не найдена',
                                                                         colour=disnake.Color.red()))
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
    @commands.slash_command(name='выплата-за-постройку', guild_ids=[settings.infrastructure['id']])
    async def force_payout(self,
                           inter: disnake.ApplicationCommandInteraction,
                           user: disnake.User,
                           amount: int,
                           message: str

                           ):
        """
        Выплатить игроку.

        Parameters
        ----------
        user: Участник сервера для выплаты.
        amount: Количество алмазов
        message: Сообщение
        """
        if self.player not in user.roles:
            return await inter.response.send_message(f'Умный дохуя? Пошел нахуй', ephemeral=True)
        await inter.response.defer(ephemeral=True)
        if await self.payout(sender=inter.author,
                             user=user,
                             message=message,
                             amount=amount,
                             ):
            await inter.edit_original_message(
                embed=disnake.Embed(title='Дело сделано',
                                    color=disnake.Color.green())
            )
        else:
            await inter.edit_original_message(
                embed=disnake.Embed(title='Произошла какая-то ошибка',
                                    color=disnake.Color.dark_red())
            )

    @commands.Cog.listener()
    async def on_ready(self):
        self.infrastructure_guild = self.bot.get_guild(settings.infrastructure['id'])
        self.deputy_role = self.infrastructure_guild.get_role(settings.infrastructure['deputy'])
        self.player = self.infrastructure_guild.get_role(settings.infrastructure['player'])
        self.conn = sqlite3.connect('infrastructure.db')
        self.cursor = self.conn.cursor()
        self.bank = plasmoapi.Bank(token=settings.plasmo_token)

        logger.info('Ready')


def setup(client):
    client.add_cog(InfrastructurePayouts(client))
