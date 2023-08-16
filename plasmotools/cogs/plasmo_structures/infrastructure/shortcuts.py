import logging
from typing import Optional

import disnake
from disnake import ApplicationCommandInteraction, Localized
from disnake.ext import commands

from plasmotools import models, settings
from plasmotools.cogs.plasmo_structures.payouts import Payouts
from plasmotools.embeds import build_simple_embed

logger = logging.getLogger(__name__)


class FastInfrastructurePayouts(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    async def checks(
        self, message: disnake.Message, inter: disnake.Interaction
    ) -> bool:
        if message.author == inter.author:
            await inter.send(
                embed=build_simple_embed(
                    "Нельзя выплачивать самому себе", failure=True
                ),
                ephemeral=True,
            )
            return False
        reacted_users = [
            await _.users().flatten() for _ in message.reactions if _.emoji == "✅"
        ]
        reacted_users.append([])
        if self.bot.user in reacted_users[0]:
            await inter.send(
                embed=build_simple_embed(
                    "На сообщении стоит реакция ✅ от PlasmoTools, нельзя выплатить второй раз.\n\n"
                    "Администраторы могут убрать эту реакцию и выплата будет вновь доступна",
                    failure=True,
                ),
                ephemeral=True,
            )
            return False

        return True

    @commands.message_command(
        name=Localized("Call", key="CALL_INFRASTUCTURE_BUTTON_NAME"),
        guild_ids=[settings.infrastructure_guild.discord_id],
    )
    @commands.default_member_permissions(administrator=True)
    async def fast_call_payout_button(
        self, inter: ApplicationCommandInteraction, message: disnake.Message
    ):
        await inter.response.defer(ephemeral=True)

        if not await self.checks(message, inter):
            return

        payouts_cog: Optional[Payouts] = self.bot.get_cog("Payouts")
        if payouts_cog is None:
            await inter.send(
                embed=build_simple_embed("Неизвестная ошибка", failure=True),
                ephemeral=True,
            )
            raise RuntimeError("Payouts cog not found")

        fake_call_project = await models.StructureProject.objects.filter(
            name="Ложный вызов",
            guild_discord_id=inter.guild.id,
            is_active=True,
        ).first()
        if fake_call_project is None:
            await inter.send(
                embed=build_simple_embed(
                    "Не удалось найти ни один активный проект с названием `Ложный вызов`",
                    failure=True,
                ),
                ephemeral=True,
            )
            return

        payouts_cog: Payouts
        result = await payouts_cog.payout(
            interaction=inter,
            user=message.author,
            amount=8,
            project=fake_call_project,
            message=f"За [вызов]({message.jump_url})",
            transaction_message="Автоматическая выплата за вызов",
        )
        if not result:
            await message.add_reaction("⚠")

        for reaction in message.reactions:
            await reaction.remove(user=self.bot.user)
        await message.add_reaction("✅")

    @commands.message_command(
        name=Localized("Breakage", key="BREAKAGE_INFRASTUCTURE_BUTTON_NAME"),
        guild_ids=[settings.infrastructure_guild.discord_id],
    )
    @commands.default_member_permissions(administrator=True)
    async def damage_payout_button(
        self, inter: ApplicationCommandInteraction, message: disnake.Message
    ):
        await inter.response.defer(ephemeral=True)

        if not await self.checks(message, inter):
            return

        payouts_cog: Optional[Payouts] = self.bot.get_cog("Payouts")
        if payouts_cog is None:
            await inter.send(
                embed=build_simple_embed("Неизвестная ошибка", failure=True),
                ephemeral=True,
            )
            raise RuntimeError("Payouts cog not found")

        quick_fix_payout_project = await models.StructureProject.objects.filter(
            name="Поломки",
            guild_discord_id=inter.guild.id,
            is_active=True,
        ).first()
        if quick_fix_payout_project is None:
            await inter.send(
                embed=build_simple_embed(
                    "Не удалось найти ни один активный проект с названием `Поломки`",
                    failure=True,
                ),
                ephemeral=True,
            )
            return

        payouts_cog: Payouts
        result = await payouts_cog.payout(
            interaction=inter,
            user=message.author,
            amount=4,
            project=quick_fix_payout_project,
            message=f"За [починку поломки]({message.jump_url})",
            transaction_message="Автоматическая выплата за починку поломки",
        )
        if not result:
            await message.add_reaction("⚠")

        for reaction in message.reactions:
            await reaction.remove(user=self.bot.user)
        await message.add_reaction("✅")

    async def cog_load(self):
        """
        Called when disnake bot object is ready
        """

        logger.info("%s loaded", __name__)


def setup(bot: disnake.ext.commands.Bot):
    """
    Disnake internal setup function
    """
    bot.add_cog(FastInfrastructurePayouts(bot))
