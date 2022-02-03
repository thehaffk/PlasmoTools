# API Wrapper for Plasmo
# Alpha Version


from typing import List
from requests import post, get
import requests

api_link = 'https://rp.plo.su/api'


class ResponseError(Exception):
    def __init__(self, reason):
        self.reason = reason

    def __str__(self):
        return self.reason


class Bank:
    def __init__(self, token):
        self.cookies = {
            'rp_token': token
        }
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/x-www-form-urlencoded"
        }

    @property
    def cards(self):
        response = get(api_link + '/bank/cards',
                       cookies=self.cookies,
                       headers=self.headers).json()
        if response['status']:
            return [BankCard(self, i['id']) for i in response['data']['cards']]
        else:
            raise ResponseError(response['error']['msg'])

    @property
    def cardDesigns(self):
        response = get(api_link + f'/bank/cards/designs',
                       cookies=self.cookies,
                       headers=self.headers).json()
        if response['status']:
            return response['data']
        else:
            raise ResponseError(response['error']['msg'])

    def searchCards(self, value: str):
        response = get(api_link + f'/bank/search/cards?value={value}',
                       cookies=self.cookies,
                       headers=self.headers).json()

        if response['status']:
            return [BankCard(self, i['id']) for i in response['data']]
        else:
            raise ResponseError(response['error']['msg'])

    def searchPlayers(self, value: str, teams: bool = False):
        response = post(api_link + f'/bank/search/players',
                        cookies=self.cookies,
                        headers=self.headers,
                        data={"value": value,
                              "teams": teams}
                        ).json()

        if response['status']:
            print(response['data'])
            resp = []
            for i in response['data']:
                if not i['type']:
                    resp.append(UserProfile(user_id=i['id']))
                else:
                    resp.append(Team(id=i['id']))

            return [UserProfile(user_id=i['id']) if not i['type'] else Team(id=i['id']) for i in response['data']]
        else:
            raise ResponseError(response['error']['msg'])

    def setActiveCard(self, card: str):

        card = 'EB-' + ('0' * (4 - len(str(card)))) + str(card)
        response = requests.patch(api_link + '/bank/cards/active',
                                  cookies=self.cookies,
                                  headers=self.headers,
                                  data={
                                      'card': card
                                  }).json()

        if response['status']:
            return True
        else:
            raise ResponseError(response['error']['msg'])

    def getCardsById(self, ids: List):
        ids2 = []
        for card_id in ids:
            ids2.append('EB-' + ('0' * (4 - len(str(card_id)))) + str(card_id))
        response = get(api_link + f'/bank/cards?ids={",".join(ids2)}',
                       cookies=self.cookies,
                       headers=self.headers).json()

        if response['status']:
            return response['data']
        else:
            raise ResponseError(response['error']['msg'])


class Bill:
    def __init__(self, card, id: int, to=None, amount=None, message=None, date=None):
        self.link = api_link + f'/bank/cards/{card}/bill/{id}'
        self.AuthorCard = card
        self.id = id
        self._from = card.id
        self.to = to
        self.amount = amount
        self.message = message
        self.date = date

    def __str__(self):
        return f'Bill ({self.id}) from {self._from} to {self.to} for {self.amount} with message {self.message}'

    @property
    def status(self):
        print(self.link + f'/status')
        response = get(self.link + f'/status',
                       headers=self.AuthorCard.headers,
                       cookies=self.AuthorCard.cookies).json()
        if response['status']:
            return response['data']['status']  # "WAIT" | "PAID" | "DECLINED" | "CANCELLED"
        else:
            raise ResponseError(response['error']['msg'])

    @property
    def is_paid(self):
        print(self.link + f'/status')
        response = get(self.link + f'/status',
                       headers=self.AuthorCard.headers,
                       cookies=self.AuthorCard.cookies).json()
        if response['status']:
            return True if response['data']['status'] == 'PAID' else False
        else:
            raise ResponseError(response['error']['msg'])

    def cancel(self):
        response = post(self.link + f'/cancel',
                        headers=self.AuthorCard.headers,
                        cookies=self.AuthorCard.cookies).json()
        if response['status']:
            return True
        else:
            raise ResponseError(response['error']['msg'])


class IncomingBill:

    def __init__(self, billDict, authorCard, CardBank):
        self.CardBank = CardBank
        self.to = authorCard
        self.id = billDict['id']
        self._from = BankCard(CardBank, billDict['card']['id'])
        self.amount = billDict['amount']
        self.message = billDict['message']
        self.date = billDict['date']
        self.link = api_link + f'/bank/cards/{authorCard}/bill/{id}'

    def __str__(self):
        return f'Bill ({self.id}) from {self._from} for {self.amount} diamonds with message {self.message} ' \
               f'since {self.date}'

    def decline(self):
        response = post(self.link + f'/decline',
                        headers=self.CardBank.headers,
                        cookies=self.CardBank.cookies).json()

        if response['status']:
            return response
        else:
            raise ResponseError(response['error']['msg'])

    def pay(self):
        response = post(self.link + f'/pay',
                        headers=self.CardBank.headers,
                        cookies=self.CardBank.cookies).json()

        if response['status']:
            return response
        else:
            raise ResponseError(response['error']['msg'])


class BankCard:
    def __init__(self, Bank, card_id):
        self.CardBank = Bank
        self.cookies = Bank.cookies
        self.headers = Bank.headers
        self.card = 'EB-' + ('0' * (4 - len(str(card_id)))) + str(card_id)
        self.id = card_id
        self.link = api_link + f'/bank/cards/{self.card}'

    def __str__(self):
        return self.card

    def __get_card_data__(self, arg):
        response = get(api_link + f'/bank/cards?ids={self.card}',
                       cookies=self.cookies,
                       headers=self.headers).json()

        if response['status']:
            return response['data'][0][arg]
        else:
            raise ResponseError(response['error']['msg'])

    @property
    def name(self):
        return self.__get_card_data__('name')

    @property
    def balance(self):
        return self.__get_card_data__('value')

    @property
    def holder(self):
        holder = self.__get_card_data__('holder_id')
        holder_is_team = bool(self.__get_card_data__('holder_type'))
        return UserProfile(user_id=holder) if holder_is_team else Team(id=holder)

    @property
    def design(self):
        return self.__get_card_data__('design')

    def bill(self, to, amount, message='Call me /h'):
        if type(to) == int or type(to) == str:
            to = f"EB-{('0' * (4 - len(str(to)))) + str(to)}"
        else:
            to = to.card

        response = post(api_link + '/bank/bill',
                        cookies=self.cookies,
                        headers=self.headers,
                        data={"from": self.card,
                              "to": to,
                              "amount": amount,
                              "message": message}).json()
        if response['status']:
            return Bill(card=self,
                        id=response['data'],
                        to=to,
                        amount=amount,
                        message=message)
        else:
            raise ResponseError(response['error']['msg'])

    def transfer(self, to, amount, message='Call me /h'):
        if type(to) == int or type(to) == str:
            to = f"EB-{('0' * (4 - len(str(to)))) + str(to)}"
        else:
            to = to.card
        response = post(f'{api_link}/bank/transfer',
                        cookies=self.cookies,
                        headers=self.headers,
                        data={"from": f"{self.card}",
                              "to": to,
                              "amount": amount,
                              "message": message}).json()
        if response['status']:
            return f'Transfered {amount} diamonds to {to}'
        else:
            raise ResponseError(response['error']['msg'])

    def delete(self):
        response = requests.delete(api_link + '/bank/cards/' + self.card,
                                   cookies=self.cookies,
                                   headers=self.headers).json()

        if response['status']:
            return True
        else:
            raise ResponseError(response['error']['msg'])

    def updateHolder(self, holderId: int, permissions: List):
        perms = {
            'OWNER': 1,
            'MANAGE': 2,
            'BILL': 4,
            'TRANSFER': 8,
            'HISTORY': 16
        }
        if 'OWNER' in permissions:
            raise AttributeError('Чтобы установить владельца воспользуйтесь BankCard.updateOwner')
        for perm in range(len(permissions)):
            permissions[perm] = perms[permissions[perm]]

        response = requests.patch(self.link + '/holder',
                                  data={
                                      'holder_id': holderId,
                                      'permissions': sum(permissions)
                                  },
                                  cookies=self.cookies,
                                  headers=self.headers).json()

        if response['status']:
            return True
        else:
            raise ResponseError(response['error']['msg'])

    def updateInfo(self, name: str = None, design: int = None, valueHidden: bool = None):
        args = {}
        if name is not None:
            args['name'] = name
        if design is not None:
            args['design'] = design
        if valueHidden is not None:
            args['valueHidden'] = valueHidden
        response = requests.patch(self.link,
                                  json={'name': '123'},
                                  cookies=self.cookies,
                                  headers=self.headers).json()

        if response['status']:
            return True
        else:
            return False, response

    def updateOwner(self, holderId: int, holderType: int = 0):
        response = requests.patch(self.link + '/owner',
                                  data={
                                      'holder_id': holderId,
                                      'holder_type': holderType
                                  },
                                  cookies=self.cookies,
                                  headers=self.headers).json()

        if response['status']:
            return True
        else:
            raise ResponseError(response['error']['msg'])

    @property
    def bills(self):
        response = get(api_link + f'/bank/cards/{self.card}/bills',
                       cookies=self.cookies,
                       headers=self.headers).json()

        if not response['status']:
            raise ResponseError(response['error']['msg'])

        return [IncomingBill(incomingbill, self.card, self.CardBank) for incomingbill in response['data']]

    def getCardHistory(self, _from=0):
        response = get(self.link + f'/history',
                       data={'from': _from},
                       cookies=self.cookies,
                       headers=self.headers).json()
        if response['status']:
            return response['data']
        else:
            raise ResponseError(response['error']['msg'])

    @property
    def holders(self):
        response = get(self.link + '/holders',
                       cookies=self.cookies,
                       headers=self.headers).json()
        if response['status']:
            return response['data']
        else:
            raise ResponseError(response['error']['msg'])

    @property
    def invoices(self):
        response = get(self.link + '/invoices',
                       cookies=self.cookies,
                       headers=self.headers).json()
        if response['status']:
            return [Bill(card=self,
                         id=i["id"],
                         amount=i["amount"],
                         message=i["message"],
                         date=i["date"]) for i in response['data']]
        else:
            raise ResponseError(response['error']['msg'])

    def search_card_history(self, value: str, _from: int = 0):
        response = get(self.link + f'/history/search?value={value}&from={_from}',
                       cookies=self.cookies,
                       headers=self.headers).json()
        if response['status']:
            return response['data']
        else:
            raise ResponseError(response['error']['msg'])
        pass


class Team:
    def __init__(self, id):
        self.id = id
        self.link = api_link + f'/teams/{self.id}'
        try:
            response = get(self.link).json()['data']
        except KeyError:
            raise AttributeError('Община по такому id не найдена')
        self.name = response['name']
        self.description = response['description']
        self.banner = 'https://www.planetminecraft.com/banner/?e=' + response['banner']
        self.recruit = response['recruit']
        self.info = response['info']
        self.discord = response['discord']
        self.tier = response['tier']
        self.images = response['images']
        self.members = response['members']
        self.marxs = response['marxs']  # TODO: Change from dict to plasmo.Marx object

    def refresh(self):
        self.__init__(self.id)


class UserProfile:

    def __init__(self, user_id):
        self.id = user_id
        self.link = api_link + f'/user/profile?id={self.id}'
        try:
            response = get(self.link + '&fields=characters,warns,marx,teams,skin_format').json()['data']
        except KeyError:
            raise AttributeError('Пользователь по такому id не найден')
        self.discord_id = response['discord_id']
        self.nick = response['nick']
        self.uuid = response['uuid']
        self.fusion = response['fusion']
        self.on_guild = response['on_server']
        self.roles = response['roles']
        self.characters = response['characters']
        self.warns = response['warns']
        self.marks = response['marks']
        self.teams = response['teams']
        self.skin_format = response['skin_format']

    def refresh(self):
        self.__init__(self.id)

    def get_stats(self):
        return get(self.link + '&fields=stats').json()['data']['stats']
