import logging
from random import randint

import disnake
from disnake.ext import commands

from plasmotools import checks, settings

logger = logging.getLogger(__name__)


def generate_ticket_page(ticket: int = 1) -> str:
    ticket_text = f"**PLASMO LOTO TICKET {ticket}**\n"
    ticket_names = ["      Поле Альфа", "      Поле Бета", "      Поле Фокстрот"]
    tickets = [
        [
            [
                (
                    number
                    if len(number := str(randint(1, 99))) == 2
                    else "0" + str(number)
                )
                for _ in range(5)
            ]
            for _ in range(5)
        ]
        for _ in range(3)
    ]
    for ticket_page in tickets:
        page_text = "".join("".join(list(map(str, row))) for row in ticket_page)
        while page_text.count(" ☽") < 2:
            x, y = randint(0, 4), randint(0, 4)
            if ticket_page[x][y] != " ☽":
                ticket_page[x][y] = " ☽"
            page_text = "".join("".join(list(map(str, row))) for row in ticket_page)

    for ticket_name, ticket_rows in zip(ticket_names, tickets):
        ticket_text += f"New book page```"
        ticket_text += """\n  -=-=-ЛотоРП-=-=-\n"""
        ticket_text += ticket_name + "\n\n"
        for row in ticket_rows:
            ticket_text += "     " + " ".join([str(i) for i in row]) + "\n"
            ticket_text += "\n"
        ticket_text += " " * (6 - len(str(ticket))) + f"-=Билет№{ticket}=-"
        ticket_text += "```"
    ticket_text += f"\n{ticket}\n"
    for ticket_rows in tickets:
        for row in ticket_rows:
            ticket_text += "".join(
                ["=$A$" + str(number) + " " for number in row]
            ).replace(" ☽", "100")
            ticket_text += "\n"
        ticket_text += "\n"
    return ticket_text


class LotoView(disnake.ui.View):
    def __init__(self, ticket: int = 0):
        super().__init__()
        self.ticket = ticket

    @disnake.ui.button(
        custom_id="generate_ticket",
        label="Сгенерировать следующий билет",
        style=disnake.ButtonStyle.green,
    )
    async def generate_ticket(
        self, button: disnake.ui.Button, interaction: disnake.Interaction
    ):
        self.ticket += 1
        await interaction.response.edit_message(
            content=generate_ticket_page(self.ticket), view=self
        )


class PlasmoLoto(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    @commands.slash_command(
        name="loto",
        guild_ids=[settings.culture_guild.discord_id, settings.DevServer.guild_id],
    )
    @checks.blocked_users_slash_command_check()
    @commands.default_member_permissions(administrator=True)
    async def loto(self, inter: disnake.ApplicationCommandInteraction, ticket: int = 1):
        """
        Генерирует билеты для лотереи

        Parameters
        ----------
        inter
        ticket: Номер билета, с которого нужно начать генерацию
        """
        await inter.send(
            generate_ticket_page(ticket),
            ephemeral=True,
            view=LotoView(ticket=ticket),
        )

    async def cog_load(self):
        """
        Called when disnake bot object is ready
        """

        logger.info("%s loaded", __name__)


def setup(bot: disnake.ext.commands.Bot):
    """
    Disnake internal setup function
    """
    bot.add_cog(PlasmoLoto(bot))
