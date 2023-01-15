import logging

import disnake
from disnake import ApplicationCommandInteraction
from disnake.ext import commands

from plasmotools import settings
from plasmotools.ext.plasmo_structures.payouts import Payouts
from plasmotools.utils.database import plasmo_structures as database

logger = logging.getLogger(__name__)

# todo: Rewrite with buttons

fake_call_project_id = 1 if settings.DEBUG else 5
damage_project_id = 1 if settings.DEBUG else 5


class FastInfrastructurePayouts(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    @commands.message_command(
        name="Вызов", guild_ids=[settings.infrastructure_guild.discord_id]
    )
    @commands.default_member_permissions(administrator=True)
    async def fast_call_payout_button(
        self, inter: ApplicationCommandInteraction, message: disnake.Message
    ):
        await inter.response.defer(ephemeral=True)

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
            amount=8,
            project=await database.projects.get_project(fake_call_project_id),
            message=f"За [вызов]({message.jump_url})",
            transaction_message=f"Автоматическая выплата за вызов",
        )
        if result:
            await message.add_reaction("✅")
        else:
            await message.add_reaction("⚠")

    @commands.message_command(
        name="Поломка", guild_ids=[settings.infrastructure_guild.discord_id]
    )
    @commands.default_member_permissions(administrator=True)
    async def damage_payout_button(
        self, inter: ApplicationCommandInteraction, message: disnake.Message
    ):
        await inter.response.defer(ephemeral=True)

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
            amount=4,
            project=await database.projects.get_project(damage_project_id),
            message=f"За [починку поломки]({message.jump_url})",
            transaction_message="Автоматическая выплата за починку поломки"
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
    bot.add_cog(FastInfrastructurePayouts(bot))
