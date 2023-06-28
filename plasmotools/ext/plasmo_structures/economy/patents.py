import logging

import disnake
from disnake.ext import commands

from plasmotools import checks, settings

logger = logging.getLogger(__name__)


class SelectPatentOwnersView(disnake.ui.View):
    def __init__(self, bot: disnake.ext.commands.Bot):
        super().__init__(timeout=600)
        self.bot = bot
        self.patent_owners = []
        self.cancelled = True

    @disnake.ui.button(
        label="Подтвердить", style=disnake.ButtonStyle.green, emoji="✅", row=1
    )
    async def confirm_button(
        self, button: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        await interaction.response.defer(ephemeral=True, with_message=False)
        self.cancelled = False
        await interaction.message.edit(view=self.clear_items())
        self.stop()

    @disnake.ui.button(
        label="Отменить создание патента",
        style=disnake.ButtonStyle.gray,
        emoji="✅",
        row=1,
    )
    async def confirm_button(
        self, button: disnake.ui.Button, interaction: disnake.MessageInteraction
    ):
        await interaction.response.defer(ephemeral=True, with_message=False)
        self.cancelled = True
        await interaction.message.edit(view=self.clear_items())
        self.stop()

    @disnake.ui.user_select(
        placeholder="Укажите владельцев патента",
        min_values=1,
        max_values=8,
        row=0,
    )
    async def user_select(
        self, select: disnake.UserSelectMenu, interaction: disnake.MessageInteraction
    ):
        self.patent_owners = interaction.values
        print(self.patent_owners)
        await interaction.response.defer(ephemeral=True, with_message=False)

    async def on_timeout(self) -> None:
        self.cancelled = True
        self.stop()


class BankerPatents(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    @commands.slash_command(
        name="patent-alpha",
        guild_ids=[settings.DevServer.guild_id, settings.LogsServer.guild_id],
    )
    @commands.is_owner()
    @checks.blocked_users_slash_command_check()
    async def patent_alpha(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer(ephemeral=True)

        """
        Как делаются патенты
        1. Указать тип патента - Мапарт / Другое
        2. Указать название патента в винительном падеже. Патент на: "арт 'artname'" "бренд 'пятерочка'"
        2.1 Указать описание патента, если это не мапарт
        2.2 Указать номера всех карт, если это мапарт
        3. Указать всех владельцев (1 - 8)
        4. Указать тип оплаты - Нал / Безнал
        4.1 Узнать про наличие скидок (Интерпол / Лицензия артодела)
        5.a.1 В случае если безнал - указать карту для оплаты патента
        5.a.2 Выставить счет на 25 алмазов (со скидкой другие числа)
        5.a.3 Распределить из казны DDT Bank так чтобы: 19 алмазов ушло в казну патентов, 6 выплатой банкиру
        5.b.1 Пусть банкир сам разбирается
        6. Попросить банкира сходить взять 2 книжки с пером
        7. Сгенерировать номер патента и текст для книжки, чтобы банкир вставил в книгу (может не влезть, предупредить об этом)
        8. Подписать книгу, сделать копию
        9. Если субъект мапарт - выдать банкиру инструкцию и список команд для ламинирования
        10. Отдать клиенту мапарты и копию патента
        11. Отправить патент на модерацию
        12. После модерации отправить эмбед в канал с патентами
        """

        select_owners_view = SelectPatentOwnersView(self.bot)
        select_owners_embed = disnake.Embed(
            title="Создание патента",
            description='Укажите всех владельцев патента и нажмите кнопку "Подтвердить"\n\nОт 1 до 8 игроков',
            color=disnake.Color.dark_green(),
        )

        await inter.edit_original_response(
            embed=select_owners_embed, view=select_owners_view
        )

        timed_out = await select_owners_view.wait()
        if timed_out:
            return await inter.edit_original_response(
                embed=disnake.Embed(title="Время вышло", color=disnake.Color.dark_red()),
                view=None,
            )

    async def cog_load(self):
        logger.info("%s loaded", __name__)


def setup(client):
    """
    Internal disnake setup function
    """
    # client.add_cog(BankerPatents(client))
    # todo: remove this when patents will be ready
