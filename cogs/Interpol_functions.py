import disnake
from disnake.ext import commands
import settings
import requests


class InterpolFunctions(commands.Cog):
    def __init__(self, bot):
        self.log_channel = None
        self.interpol_guild = None
        self.bot = bot

    @commands.has_role(settings.interpol['interpol'])
    @commands.slash_command(name='снять-штрафы-забаненным', guild_ids=[settings.interpol['id']])
    async def clear_penalties(self,
                              inter: disnake.ApplicationCommandInteraction):

        """
        Пробегается по всем штрафам и снимает.

        Parameters
        ----------

        """

        await inter.response.defer(ephemeral=True)
        counter = 0
        for tab in ['active', 'check', 'expired']:
            penalties = requests.get(f'https://rp.plo.su/api/bank/penalties/helper?tab={tab}&from=0',
                                     cookies={'rp_token': settings.plasmo_token}).json()
            if not penalties['status']:
                return await inter.response.send_message(
                    f'Что-то пошло не так, не смог получить нормальный ответ от Plasmo', ephemeral=True)
            penalties = penalties['data']

            for i in range(0, penalties['total'], 25):
                penalties = requests.get(f'https://rp.plo.su/api/bank/penalties/helper?tab={tab}&from={i}',
                                         cookies={'rp_token': settings.plasmo_token}).json()['data']['all']['list']
                for penalty in penalties:
                    try:
                        if requests.get(f'https://rp.plo.su/api/user/profile'
                                        f'?nick={penalty["user"]}').json()['data']['banned']:
                            penalty_embed = disnake.Embed(title='Штраф снят',
                                                          description=f'Штраф игроку [{penalty["user"]}](https://rp.plo.su/u/{penalty["user"]}), выданный {penalty["helper"]}, \
                            был снят системой автоматической отмены штрафов',
                                                          color=disnake.Color.red())
                            penalty_embed.set_footer(text='Проверку запустил ' + inter.author.display_name,
                                                     icon_url=f'https://rp.plo.su/avatar/{inter.author.display_name}')

                            penalty_embed.add_field(name='Информация о штрафе',
                                                    value=f'**ID**: {penalty["id"]} **Amount**: {penalty["amount"]} \n **Message**: \n {penalty["message"]}')

                            print(requests.delete('https://rp.plo.su/api/bank/penalty',
                                                  cookies={'rp_token': settings.plasmo_token},
                                                  data={"penalty": penalty['id']}).json())
                            counter += 1

                            await self.log_channel.send(embed=penalty_embed)
                    except KeyError:
                        pass
                    except ConnectionError:
                        pass
        return await inter.edit_original_message(
            embed=disnake.Embed(title=f'Штрафов отменено: {counter}', color=disnake.Color.green()))

    @commands.is_owner()
    @commands.slash_command(name='синхронизировать-баны', guild_ids=[828683007635488809])
    async def ban_all(self,
                      inter: disnake.ApplicationCommandInteraction):

        """
        Банит всех забаненных на плазмо на сервере где вызван

        Parameters
        ----------

        """

        await inter.response.defer(ephemeral=True)
        print(len(select(table='users', columns='discord_id', where='banned=1')))
        for user in select(table='users', columns='discord_id', where='banned=1'):
            user = disnake.Object(user[0])
            await inter.guild.ban(user, reason='Забанен на плазме((')
        return await inter.edit_original_message(
            embed=disnake.Embed(title=f'Заебись', color=disnake.Color.green()))

    @commands.Cog.listener()
    async def on_ready(self):
        self.interpol_guild = self.bot.get_guild(settings.interpol['id'])
        self.log_channel = self.interpol_guild.get_channel(settings.interpol['logs'])


def setup(client):
    client.add_cog(InterpolFunctions(client))


import mysql.connector
from mysql.connector import Error

HOST = '54.37.129.120'
PORT = 3306
USER = 'pepega'
PASSWORD = 'hRLxsXQwk0REGuf2'
DATABASE = 'plasmo_rp'
debug = True

'''conn = pymysql.connect(host=HOST,
                       port=PORT,
                       user=USER,
                       passwd=PASSWORD,
                       db=DATABASE)
'''


def create_connection(host_name, user_name, user_password):
    connection = None

    try:
        connection = mysql.connector.connect(
            host=host_name,
            user=user_name,
            passwd=user_password,
            database='plasmo_rp',
            use_pure=True
        )
        print("Connection to MySQL DB successful")
    except Error as e:
        print(f"The error '{e}' occurred")
    return connection


def recon():
    global conn
    conn = create_connection(HOST, USER, PASSWORD)


recon()


def select(table='parliament_votes', columns='*', where='', args='', always_return_all=False, return_list=False,
           return_matrix=False, retry=False):
    try:
        if where != '' and 'WHERE' not in where:
            where = 'WHERE ' + where
        request = f'SELECT {columns} FROM {table} {where} {args}'
        if debug:
            print(request)
        cur = conn.cursor(buffered=True)
        cur.execute(request)
        fetchall = cur.fetchall()
        cur.close()

        if return_list:
            response = []
            if len(fetchall):
                for elem in fetchall:
                    response.append(elem[0])
                return response
            else:
                return []
        elif return_matrix:
            response = []
            if len(fetchall):
                for elem in fetchall:
                    response.append([elem[1], int(elem[0])])
                print(response)
                return response
            return []
        if len(fetchall) <= 1 and not always_return_all:
            return fetchall[0]
        else:
            return fetchall
    except IndexError:
        return None
    except Exception as err:
        print(err)
        recon()
        if not retry:
            return select(table=table,
                          columns=columns,
                          where=where,
                          args=args,
                          always_return_all=always_return_all,
                          return_list=return_list,
                          return_matrix=return_matrix,
                          retry=True)
        else:
            return None
