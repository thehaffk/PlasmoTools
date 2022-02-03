import disnake
import requests
from disnake.ext import commands
import settings


class BACSynchronization(commands.Cog):
    def __init__(self, bot):
        self.bac_banned = None
        self.bac_nonpass = None
        self.bac_pass = None
        self.bac = None
        self.bot = bot

    async def sync(self, member):
        if member not in self.bac.members or member.bot:
            return False
        print(f'Syncing {member} ({member.display_name})')
        try:
            data = requests.get(f'https://rp.plo.su/api/user/profile?discord_id={member.id}').json()
        except ConnectionError:
            return False
        if not data['status']:
            return False

        data = data['data']
        bac_member = self.bac.get_member(member.id)

        try:
            await bac_member.edit(nick=data['nick'])
            if data['on_server']:
                await bac_member.add_roles(self.bac_pass)
                await bac_member.remove_roles(self.bac_nonpass)
            else:
                await bac_member.add_roles(self.bac_nonpass)
                await bac_member.remove_roles(self.bac_pass)
            if "banned" in data and data['banned']:
                await bac_member.add_roles(self.bac_banned)
            else:
                await bac_member.remove_roles(self.bac_banned)
        except Exception as e:
            print('BAC Sync', e)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if not before.guild.id == settings.plasmo_rp_guild:
            return False
        if before.display_name != after.display_name or before.roles != after.roles:
            await self.sync(after)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, member):
        if not guild.id == settings.plasmo_rp_guild:
            return False
        if member not in self.bac.members:
            try:
                await member.send(embed=disnake.Embed(title='Вы были забанены на Plasmo RP',
                                                      color=disnake.Color.red(),
                                                      description=f'Узнать причину бана, оспорить решение '
                                                                  f'администрации или разбаниться можно '
                                                                  f'только тут - {settings.bac["invite"]}'))
            except Exception as e:
                print(e)
        else:
            await self.sync(member)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, member):
        if not guild.id == settings.plasmo_rp_guild:
            return False
        try:
            await member.send(embed=disnake.Embed(title='Вас разбанили на Plasmo RP',
                                                  color=disnake.Color.green(),
                                                  description=f'Держите инвайт и не забывайте соблюдать '
                                                              f'правила сервера {settings.plasmo_rp["invite"]}'))
        except Exception as e:
            print(e)
        await self.sync(member)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if not member.guild.id == settings.bac['id']:
            return False
        await self.sync(member)

    @commands.Cog.listener()
    async def on_ready(self):
        print('BAC ready')
        self.bac = self.bot.get_guild(settings.bac['id'])
        self.bac_pass = self.bac.get_role(settings.bac['pass'])
        self.bac_nonpass = self.bac.get_role(settings.bac['no_pass'])
        self.bac_banned = self.bac.get_role(settings.bac['banned'])

    @commands.slash_command(name='everyone-sync', guild_ids=[settings.bac['id']])
    @commands.has_permissions(manage_roles=True)
    async def everyone_sync(self, inter: disnake.ApplicationCommandInteraction):

        """
        Синхронизировать всех пользователей на сервере.

        """

        members = inter.guild.members

        embed_counter = disnake.Embed(title=('Синхронизация | ' + str(inter.guild)), color=0xffff00)

        counter = 0
        embed_counter.add_field(name='Синхронизация', value=f'{counter} / {len(members)}')

        await inter.response.send_message(
            embed=embed_counter,
            ephemeral=True)

        for member in members:
            counter += 1
            embed_counter.clear_fields()
            embed_counter.add_field(name='Синхронизация', value=f'{counter} / {len(members)} \n {member}')
            await inter.edit_original_message(
                embed=embed_counter)
            await self.sync(member)

    @commands.slash_command(name='sync', guild_ids=[settings.bac['id']], auto_sync=False)
    @commands.has_permissions(manage_roles=True)
    async def sync_user(self, inter: disnake.ApplicationCommandInteraction, user: disnake.Member):

        """
        Синхронизировать пользователя.

        Parameters
        ----------
        user: Пользователь которого нужно синхронизировать

        """

        embed_counter = disnake.Embed(title=(f'Синхронизация {user} | ' + str(inter.guild)), color=0xffff00)
        await inter.response.send_message(
            embed=embed_counter,
            ephemeral=True)
        await self.sync(user)

    @disnake.ext.commands.message_command(name='Sync', default_permission=True,
                                          guild_ids=[settings.bac['id']])
    async def sync_button(self, inter: disnake.ApplicationCommandInteraction, msg: disnake.Message):
        await inter.response.defer(ephemeral=True)
        await self.sync(msg.author)
        embed_counter = disnake.Embed(title=(f'Синхронизация {msg.author} | ' + str(inter.guild)), color=0xffff00)
        await inter.edit_original_message(
            embed=embed_counter)


def setup(client):
    client.add_cog(BACSynchronization(client))
