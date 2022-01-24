import disnake
from disnake.ext import commands, tasks
from aiohttp.client import ClientSession
import settings
import sqlite3
import datetime

positions = commands.option_enum({
    settings.texts['interpol']: 'interpol',
    settings.texts['arbiter']: 'arbiter',
    settings.texts['secretary']: 'secretary',
    settings.texts['deputy']: 'deputy'})


class InterpolHR(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.has_permissions(manage_roles=True)
    @commands.slash_command(name='нанять', guild_ids=[settings.interpol['id']])
    async def hire(self,
                   inter: disnake.ApplicationCommandInteraction,
                   user: disnake.User,
                   position: positions
                   ):
        """
        Нанять игрока.

        Parameters
        ----------
        :param inter: Interaction
        :param user: Участник сервера для найма.
        :param position: Должность
        """
        if self.player not in user.roles:  # Player check
            return await inter.response.send_message(f'Умный дохуя? Пошел нахуй', ephemeral=True)
        await inter.response.defer(ephemeral=True)

        # Permissions check (+ hierarchy)
        if (position == 'deputy' or self.interpol_guild.get_role(settings.interpol['deputy']) in user.roles) \
                and (not self.interpol_guild.get_role(settings.interpol['interpol_head']) in inter.author.roles or
                     inter.author.id not in self.bot.owner_ids):
            return await inter.edit_original_message(embed=disnake.Embed(title='У вас нет прав на это',
                                                                         color=disnake.Color.red()))

        role = self.interpol_guild.get_role(settings.interpol[position])
        if role in user.roles:
            return await inter.response.send_message(f'{user.mention} уже на должности {settings.texts[position]}.',
                                                     ephemeral=True)

        await user.add_roles(role, reason=f'Нанят ({inter.author.display_name})')

        async with ClientSession() as session:
            webhook = disnake.Webhook.from_url(settings.interpol_announcements_webhook_url if
                                               role in [settings.interpol['interpol'], settings.interpol['deputy']]
                                               else settings.interpol_court_announcements_webhook_url,
                                               session=session)
            hr_embed = disnake.Embed(description=f'{user.mention} принят на должность {settings.texts[position]}.',
                                     color=disnake.Color.green()).set_author(name=user.display_name,
                                                                             icon_url=f'https://rp.plo.su/avatar/'
                                                                                      f'{user.display_name}')
            hr_embed.set_footer(text='Нанял ' + inter.author.display_name,
                                icon_url=f'https://rp.plo.su/avatar/{inter.author.display_name}'
                                )
            await webhook.send(content=user.mention,
                               embed=hr_embed)
        await inter.response.send_message(f'{user.mention} принят на должность {settings.texts[position]}.',
                                          ephemeral=True)

    @commands.has_permissions(manage_roles=True)
    @commands.slash_command(name='уволить', guild_ids=[settings.interpol_guild])
    async def fire(self,
                   inter: disnake.ApplicationCommandInteraction,
                   user: disnake.User,
                   position: positions,
                   reason: str = "Не указана",
                   ):
        """
        Уволить игрока.

        Parameters
        ----------
        user: Участник сервера для найма.
        position: Должность
        reason: Причина
        """
        if self.player not in user.roles:
            return await inter.response.send_message(f'Умный дохуя? Пошел нахуй', ephemeral=True)

        await inter.response.defer(ephemeral=True)
        if (position == 'deputy' or self.interpol_guild.get_role(settings.interpol['deputy']) in user.roles) \
                and (not self.interpol_guild.get_role(settings.interpol['interpol_head']) in inter.author.roles or
                     inter.author.id not in self.bot.owner_ids):
            return await inter.edit_original_message(embed=disnake.Embed(title='У вас нет прав на это',
                                                                         color=disnake.Color.red()))

        role = self.interpol_guild.get_role(settings.interpol[position])
        if role not in user.roles:
            return await inter.edit_original_message(content=f'{user.mention} не является {settings.texts[position]}.')

        await user.remove_roles(role, reason=f'Снят ({inter.author.display_name})')

        async with ClientSession() as session:
            webhook = disnake.Webhook.from_url(settings.interpol_announcements_webhook_url if
                                               role in [settings.interpol['interpol'], settings.interpol['deputy']]
                                               else settings.interpol_court_announcements_webhook_url,
                                               session=session)
            HR_embed = disnake.Embed(description=f'{user.mention} снят с должности {settings.texts[position]}.\n\n'
                                                 f'{"    Причина: " + reason if reason != "Не указана" else ""}',
                                     color=disnake.Color.red()).set_author(name=user.display_name,
                                                                           icon_url=f'https://rp.plo.su/avatar/{user.display_name}')
            HR_embed.set_footer(text='Снял ' + inter.author.display_name,
                                icon_url=f'https://rp.plo.su/avatar/{inter.author.display_name}'
                                )
            await webhook.send(content=user.mention,
                               embed=HR_embed)
        await inter.edit_original_message(content=f'{user.mention} снят с должности {settings.texts[position]}.')

    @commands.has_permissions(manage_roles=True)
    @commands.slash_command(name='малоактивный', guild_ids=[settings.interpol_guild])
    async def lowactive(self,
                        inter: disnake.ApplicationCommandInteraction,
                        user: disnake.User,
                        reason: str = "Не указана",
                        ):
        """
        Выдать игроку роль малоактивного.

        Parameters
        ----------
        user: Участник сервера для выдачи роли малоактивного.
        reason: Причина
        """
        if self.player not in user.roles:
            return await inter.response.send_message(f'Умный дохуя? Пошел нахуй', ephemeral=True)
        await inter.response.defer(ephemeral=True)

        role = self.interpol_guild.get_role(settings.interpol['lowactive'])
        if role in user.roles:
            return await inter.edit_original_message(content=f'{user.mention} уже {settings.texts["lowactive"]}.')

        await user.add_roles(role, reason=f'Выдал ({inter.author.display_name})')

        async with ClientSession() as session:
            webhook = disnake.Webhook.from_url(settings.interpol_announcements_webhook_url if
                                               role in [settings.interpol['interpol'], settings.interpol['deputy']]
                                               else settings.interpol_court_announcements_webhook_url,
                                               session=session)
            HR_embed = disnake.Embed(description=f'{user.mention} проявляет малую активность.\n\n'
                                                 f'{"    Причина: " + reason if reason != "Не указана" else ""}',
                                     color=disnake.Color.dark_gray()).set_author(name=user.display_name,
                                                                                 icon_url=f'https://rp.plo.su/avatar/{user.display_name}')
            HR_embed.set_footer(text='Выдал ' + inter.author.display_name,
                                icon_url=f'https://rp.plo.su/avatar/{inter.author.display_name}'
                                )
            await webhook.send(content=user.mention,
                               embed=HR_embed)
        await inter.edit_original_message(content=f'{user.mention} стал малоактивным.',)

    @commands.has_permissions(manage_roles=True)
    @commands.slash_command(name='исправился', guild_ids=[settings.interpol_guild])
    async def remove_lowactive(self,
                               inter: disnake.ApplicationCommandInteraction,
                               user: disnake.User,
                               reason: str = "Не указана",
                               ):
        """
        Снять игроку роль малоактивного.

        Parameters
        ----------
        user: Участник сервера для снятия роли малоактивного.
        reason: Причина
        """
        if self.player not in user.roles:
            return await inter.response.send_message(f'Умный дохуя? Пошел нахуй', ephemeral=True)

        role = self.interpol_guild.get_role(settings.interpol['lowactive'])
        if role not in user.roles:
            return await inter.response.send_message(f'{user.mention} не {settings.texts["lowactive"]}.',
                                                     ephemeral=True)

        await user.remove_roles(role, reason=f'Снял ({inter.author.display_name})')

        async with ClientSession() as session:
            webhook = disnake.Webhook.from_url(settings.interpol_announcements_webhook_url,
                                               session=session)
            HR_embed = disnake.Embed(description=f'{user.mention} больше не проявляет малую активность.\n\n'
                                                 f'{"    Причина: " + reason if reason != "Не указана" else ""}',
                                     color=disnake.Color.green()).set_author(name=user.display_name,
                                                                             icon_url=f'https://rp.plo.su/avatar/{user.display_name}')
            HR_embed.set_footer(text='Снял ' + inter.author.display_name,
                                icon_url=f'https://rp.plo.su/avatar/{inter.author.display_name}'
                                )
            await webhook.send(content=user.mention,
                               embed=HR_embed)
        await inter.response.send_message(f'{user.mention} перестал быть малоактивным.',
                                          ephemeral=True)

    @commands.slash_command(name='отпуск', guild_ids=[settings.interpol['id']])
    async def vacation(self, inter):
        pass

    @commands.has_permissions(manage_roles=True)
    @vacation.sub_command(name='отправить', guild_ids=[settings.interpol['id']])
    async def to_vacation(self,
                          inter: disnake.ApplicationCommandInteraction,
                          user: disnake.User,
                          days: int,
                          reason: str = "Не указана",
                          ):
        """
        Отправить попуска в отпуск.

        Parameters
        ----------
        user: Попуск
        days: Количество дней
        reason: Причина
        """

        if days <= 0:
            return await inter.response.send_message(f'Внимание всем, {inter.author.mention} - еблан')

        if self.player not in user.roles:
            return await inter.response.send_message(f'Умный дохуя? Пошел нахуй', ephemeral=True)

        vacation_role = self.interpol_guild.get_role(settings.interpol['vacation'])
        if vacation_role in user.roles:
            return await inter.response.send_message(f'Игрок уже в отпуске', ephemeral=True)

        await inter.response.defer(ephemeral=True)

        self.cursor.execute(
            f'INSERT INTO vacations VALUES ({user.id},'
            f' {days},'
            f' {int(datetime.datetime.now(datetime.timezone.utc).timestamp())})')
        self.conn.commit()
        await user.add_roles(vacation_role, reason=f'Отправлен в отпуск ({inter.author.display_name})')
        async with ClientSession() as session:
            webhook = disnake.Webhook.from_url(settings.interpol_vacation_webhook_url,
                                               session=session)
            HR_embed = disnake.Embed(description=f'{user.mention} отправлен в отпуск на {days} дн.\n\n'
                                                 f'{"    Причина: " + reason if reason != "Не указана" else ""}',
                                     color=disnake.Color.dark_gray()).set_author(name=user.display_name,
                                                                                 icon_url=f'https://rp.plo.su/avatar/{user.display_name}')
            HR_embed.set_footer(text='Отправил ' + inter.author.display_name,
                                icon_url=f'https://rp.plo.su/avatar/{inter.author.display_name}'
                                )
            await webhook.send(content=user.mention,
                               embed=HR_embed)
        await inter.edit_original_message(content=f'{user.mention} отправлен в отпуск.')

    @commands.has_permissions(manage_roles=True)
    @vacation.sub_command(name='вернуть', guild_ids=[settings.interpol['id']])
    async def remove_from_vacation(self,
                                   inter: disnake.ApplicationCommandInteraction,
                                   user: disnake.User,
                                   reason: str = "Не указана",
                                   ):
        """
        Досрочно вернуть попуска из отпуска.

        Parameters
        ----------
        user: Попуск
        reason: Причина
        """

        if self.player not in user.roles:
            return await inter.response.send_message(f'Умный дохуя? Пошел нахуй', ephemeral=True)

        vacation_role = self.interpol_guild.get_role(settings.interpol['vacation'])
        if vacation_role not in user.roles:
            return await inter.response.send_message(f'Игрок не в отпуске', ephemeral=True)

        await inter.response.defer(ephemeral=True)

        self.cursor.execute(f'DELETE FROM vacations WHERE discord_id = {user.id}')
        self.conn.commit()
        await user.remove_roles(vacation_role, reason=f'Возвращен из отпуска ({inter.author.display_name})')
        async with ClientSession() as session:
            webhook = disnake.Webhook.from_url(settings.interpol_vacation_webhook_url,
                                               session=session)
            HR_embed = disnake.Embed(description=f'{user.mention} досрочно возвращен из отпуска.\n\n'
                                                 f'{"    Причина: " + reason if reason != "Не указана" else ""}',
                                     color=disnake.Color.dark_gray()).set_author(name=user.display_name,
                                                                                 icon_url=f'https://rp.plo.su/avatar/{user.display_name}')
            HR_embed.set_footer(text='Вернул ' + inter.author.display_name,
                                icon_url=f'https://rp.plo.su/avatar/{inter.author.display_name}'
                                )
            await webhook.send(content=user.mention,
                               embed=HR_embed)
        await inter.edit_original_message(content=f'{user.mention} возвращен из отпуска')

    @tasks.loop(hours=1)
    async def check_vacations(self):
        remove_from_vacation_users = self.cursor.execute(
            f'SELECT * FROM vacations WHERE (since + days * 86400) <= {int(datetime.datetime.now(datetime.timezone.utc).timestamp())}').fetchall()
        for row in remove_from_vacation_users:
            user = self.interpol_guild.get_member(row[0])
            self.cursor.execute(f'DELETE FROM vacations WHERE discord_id = {user.id}')
            self.conn.commit()
            vacation_role = self.interpol_guild.get_role(settings.interpol['vacation'])
            await user.remove_roles(vacation_role, reason=f'Возвращен из отпуска (Plasmo Tools)')
            async with ClientSession() as session:
                webhook = disnake.Webhook.from_url(settings.interpol_vacation_webhook_url,
                                                   session=session)
                HR_embed = disnake.Embed(description=f'{user.mention} возвращен из отпуска.\n\n',
                                         color=disnake.Color.dark_gray()).set_author(name=user.display_name,
                                                                                     icon_url=f'https://rp.plo.su/avatar/{user.display_name}')
                HR_embed.set_footer(text='Возвращен автоматически')
                await webhook.send(content=f'{user.mention} <@&{settings.interpol["interpol_head"]}>',
                                   embed=HR_embed)

    @commands.Cog.listener()
    async def on_ready(self):

        self.interpol_guild = self.bot.get_guild(settings.interpol['id'])
        self.player = self.interpol_guild.get_role(settings.interpol['player'])
        self.conn = sqlite3.connect('interpol.db')
        self.cursor = self.conn.cursor()
        print('HR - Ready')
        await self.check_vacations()


def setup(client):
    client.add_cog(InterpolHR(client))
