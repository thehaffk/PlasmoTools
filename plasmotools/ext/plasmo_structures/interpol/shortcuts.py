import logging
import re

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
        "event_10min_payout": 2,
    },
    935607349681475584: {
        "name": "Сержант",
        "fake_call_payout": 5,
        "event_10min_payout": 3,
    },
    935607425917132903: {
        "name": "Полковник",
        "fake_call_payout": 8,
        "event_10min_payout": 4,
    },
    1014506371649118329: {
        "name": "Генерал",
        "fake_call_payout": 10,
        "event_10min_payout": 5,
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

    @commands.message_command(
        name="Ивент", guild_ids=[settings.interpol_guild.discord_id]
    )
    @commands.default_member_permissions(administrator=True)
    async def event_payout_button(
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

        message_text = message.content
        # find data in message_text via regex

        finded_groups = re.findall(r"1[. ]*([\s\S]+)2[. ]*([0-9]{1,2}):([0-9]{2})[ ]*-[ ]*([0-9]{1,2}):([0-9]{2})", message_text)
        if len(finded_groups) == 0:
            await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description="Сообщение написано не по форме ⚠",
                ),
                ephemeral=True,
            )
            return
        event_title, start_hour, start_minute, end_hour, end_minute = finded_groups[0]
        event_title = event_title.strip()
        start_time = int(start_hour) * 60 + int(start_minute)
        end_time = int(end_hour) * 60 + int(end_minute)
        if start_time > end_time:
            event_duration = 1440 - start_time + end_time
        else:
            event_duration = end_time - start_time

        if event_duration < 10:
            await message.add_reaction("⚠")
            await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description="Маловато ⚠",
                ),
                ephemeral=True,
            )
            return
        elif event_duration > 150:
            await inter.send(
                embed=disnake.Embed(
                    color=disnake.Color.red(),
                    title="Ошибка",
                    description="Многовато минут, такое вручную выплачивайте ⚠",
                ),
                ephemeral=True,
            )
            return

        payout_amount = rank["event_10min_payout"] * (event_duration // 10)
        await inter.send(f"Ивент `{event_title}`\nДлительность "
                         f"**{event_duration} мин. ({start_hour}:{start_minute} - {end_hour}:{end_minute})**\n"
                         f"Ранк **{rank['name']}**\n"
                         f"Выплата **{payout_amount} = {rank['event_10min_payout']} * ({event_duration} / 10)**")

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
            amount=payout_amount,
            project=await database.projects.get_project(events_project_id),
            message=f"Выплата за ивент '{event_title}' ({event_duration} мин.) / {rank['name']}",
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
