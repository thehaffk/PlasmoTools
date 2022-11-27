import logging

import disnake
from disnake import ApplicationCommandInteraction
from disnake.ext import commands

from plasmotools import settings
from plasmotools.ext.plasmo_structures.payouts import Payouts
from plasmotools.utils.database import plasmo_structures as database

logger = logging.getLogger(__name__)

# todo: Rewrite with buttons

interpol_ranks = {
    935606863075090503: {
        "name": "Рядовой",
        "fake_call_payout": 3,
    },
    935607349681475584: {
        "name": "Сержант",
        "fake_call_payout": 5,
    },
    935607425917132903: {
        "name": "Полковник",
        "fake_call_payout": 8,
    },
    1014506371649118329: {
        "name": "Генерал",
        "fake_call_payout": 10,
    },
}
fake_call_project_id = 1 if settings.DEBUG else 3
events_project_id = 1 if settings.DEBUG else 4


class FastInterpolPayouts(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    @commands.message_command(
        name="Говновызов", guild_ids=[settings.interpol_guild.discord_id]
    )
    @commands.default_member_permissions(administrator=True)
    async def fast_fake_call_payout_button(
        self, inter: ApplicationCommandInteraction, message: disnake.Message
    ):
        await inter.response.defer(ephemeral=True)
        rank = None
        for role in message.author.roles[::-1]:
            if role.id in interpol_ranks:
                rank = interpol_ranks[role.id]
                break
        if rank is None:
            await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description="Не удалось найти ранговую роль, невозможно вычислить размер выплаты",
                ),
                ephemeral=True,
            )
            return

        payouts_cog = self.bot.get_cog("Payouts")
        if payouts_cog is None:
            await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description="Неизвестная ошибка",
                ),
                ephemeral=True,
            )
            raise RuntimeError("Payouts cog not found")

        payouts_cog: Payouts
        result = await payouts_cog.payout(
            interaction=inter,
            user=message.author,
            amount=rank["fake_call_payout"],
            project=await database.projects.get_project(fake_call_project_id),
            message=f"Выплата за ложный вызов / {rank['name']}",
        )
        if result:
            await message.add_reaction("✅")
        else:
            await message.add_reaction("⚠")

    async def cog_load(self):
        """
        Called when disnake bot object is ready
        """

        logger.info("%s Ready", __name__)


def setup(bot: disnake.ext.commands.Bot):
    """
    Disnake internal setup function
    """
    bot.add_cog(FastInterpolPayouts(bot))
