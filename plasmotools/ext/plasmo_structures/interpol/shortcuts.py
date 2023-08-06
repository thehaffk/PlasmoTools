import asyncio
import logging
import re
from typing import Optional

import disnake
from disnake import ApplicationCommandInteraction, Localized
from disnake.ext import commands

from plasmotools import settings
from plasmotools.ext.plasmo_structures.payouts import Payouts
from plasmotools.utils import models
from plasmotools.utils.embeds import build_simple_embed

logger = logging.getLogger(__name__)


interpol_ranks = {
    935606863075090503: {
        "name": "Рядовой",
        "fake_call_payout": 3,
        "event_10min_payout": 2,
        "ten_penalties_payout": 10,
    },
    935607349681475584: {
        "name": "Сержант",
        "fake_call_payout": 5,
        "event_10min_payout": 3,
        "ten_penalties_payout": 20,
    },
    935607425917132903: {
        "name": "Полковник",
        "fake_call_payout": 8,
        "event_10min_payout": 4,
        "ten_penalties_payout": 30,
    },
    1014506371649118329: {
        "name": "Генерал",
        "fake_call_payout": 10,
        "event_10min_payout": 5,
        "ten_penalties_payout": 40,
    },
}
fake_call_project_id = 3
events_project_id = 4


class FastInterpolPayouts(commands.Cog):
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
        name=Localized("Fake call", key="FAKE_CALL_INTERPOL_BUTTON_NAME"),
        guild_ids=[settings.interpol_guild.discord_id],
    )
    @commands.default_member_permissions(administrator=True)
    async def fast_fake_call_payout_button(
        self, inter: ApplicationCommandInteraction, message: disnake.Message
    ):
        await inter.response.defer(ephemeral=True)

        if not await self.checks(message, inter):
            return

        rank = None
        for role in message.author.roles[::-1]:
            if role.id in interpol_ranks:
                rank = interpol_ranks[role.id]
                break
        if rank is None:
            await inter.send(
                embed=build_simple_embed(
                    "Не удалось найти ранговую роль, невозможно вычислить размер выплаты",
                    failure=True,
                ),
                ephemeral=True,
            )
            return

        payouts_cog: Optional[Payouts] = self.bot.get_cog("Payouts")
        if payouts_cog is None:
            await inter.send(
                embed=build_simple_embed("Неизвестная ошибка", failure=True),
                ephemeral=True,
            )
            raise RuntimeError("Payouts cog not found")

        payouts_cog: Payouts
        result = await payouts_cog.payout(
            interaction=inter,
            user=message.author,
            amount=rank["fake_call_payout"],
            project=await models.StructureProject.objects.get(id=fake_call_project_id),
            message=f"За [ложный вызов]({message.jump_url}) / {rank['name']}",
            transaction_message=f"Выплата за ложный вызов / Расценка по рангу {rank['name']}",
        )
        if result:
            for reaction in message.reactions:
                await reaction.remove(user=self.bot.user)
            await message.add_reaction("✅")
        else:
            await message.add_reaction("⚠")

    @commands.message_command(
        name=Localized("10 Penalties", key="TEN_PENALTIES_INTERPOL_BUTTON_NAME"),
        guild_ids=[settings.interpol_guild.discord_id],
    )
    @commands.default_member_permissions(administrator=True)
    async def fast_10_penalties_payout_button(
        self, inter: ApplicationCommandInteraction, message: disnake.Message
    ):
        await inter.response.defer(ephemeral=True)
        if not await self.checks(message, inter):
            return

        rank = None
        for role in message.author.roles[::-1]:
            if role.id in interpol_ranks:
                rank = interpol_ranks[role.id]
                break
        if rank is None:
            await inter.send(
                embed=build_simple_embed(
                    "Не удалось найти ранговую роль, невозможно вычислить размер выплаты",
                    failure=True,
                ),
                ephemeral=True,
            )
            return

        payouts_cog: Optional[Payouts] = self.bot.get_cog("Payouts")
        if payouts_cog is None:
            await inter.send(
                embed=build_simple_embed("Неизвестная ошибка", failure=True),
                ephemeral=True,
            )
            raise RuntimeError("Payouts cog not found")

        payouts_cog: Payouts
        result = await payouts_cog.payout(
            interaction=inter,
            user=message.author,
            amount=rank["ten_penalties_payout"],
            project=await models.StructureProject.objects.get(id=fake_call_project_id),
            message=f"За 10 выданных штрафов / {rank['name']}",
            transaction_message=f"Выплата за 10 выполненных штрафов / Расценка по рангу {rank['name']}",
        )
        if result:
            for reaction in message.reactions:
                await reaction.remove(user=self.bot.user)
            await message.add_reaction("✅")
        else:
            await message.add_reaction("⚠")

    @commands.message_command(
        name=Localized("Event", key="EVENT_INTERPOL_BUTTON_NAME"),
        guild_ids=[settings.interpol_guild.discord_id, settings.DevServer.guild_id],
    )
    @commands.default_member_permissions(administrator=True)
    async def event_payout_button(
        self, inter: ApplicationCommandInteraction, message: disnake.Message
    ):
        await inter.response.defer(ephemeral=True)
        if not await self.checks(message, inter):
            return

        rank = None
        for role in message.author.roles[::-1]:
            if role.id in interpol_ranks:
                rank = interpol_ranks[role.id]
                break
        if rank is None:
            await inter.send(
                embed=build_simple_embed(
                    "Не удалось найти ранговую роль, невозможно вычислить размер выплаты",
                    failure=True,
                ),
                ephemeral=True,
            )
            return

        message_text = message.content

        finded_groups = re.findall(
            r"1\.[ ]*([\s\S]+)2\.[ ]*([0-9]{1,2}):([0-9]{2})[ ]*-[ ]*([0-9]{1,2}):([0-9]{2})",
            message_text,
        )
        if len(finded_groups) == 0:
            await inter.send(
                embed=build_simple_embed(
                    "Сообщение написано не по форме ⚠", failure=True
                ),
                ephemeral=True,
                components=[
                    disnake.ui.Button(
                        label="Оповестить юзера",
                        custom_id=f"interpol_shortcut_events_{message.id}",
                    )
                ],
            )
            try:
                await self.bot.wait_for(
                    "button_click",
                    check=lambda i: (
                        i.component.custom_id
                        == f"interpol_shortcut_events_{message.id}"
                    ),
                    timeout=600,
                )
                await message.reply(
                    embed=disnake.Embed(
                        title="",
                        description="⚠️ Сообщение написано не по форме, выплата отменена.\n"
                        "Напишите новый лог об ивенте в формате:\n"
                        "```1. Релиз Plasmo Tools 1.5.10\n"
                        "2. 17:10 - 17:30\n"
                        "[1-2 Прикрепленных изображения]```",
                        color=disnake.Color.dark_red(),
                    ).set_footer(text="This message will be deleted in 15 minutes"),
                    delete_after=900,
                )
            except asyncio.TimeoutError:
                ...
            return await inter.edit_original_message(components=[])
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
                embed=build_simple_embed("Маловато ⚠", failure=True),
                ephemeral=True,
            )
            return
        elif event_duration > 180:
            await inter.send(
                embed=build_simple_embed(
                    f"Многовато минут, такое вручную выплачивайте ⚠\n"
                    f"Чтобы не выплатить миллион алмазов из-за бага, в боте установлен лимит - 180 минут. "
                    f"Если что, выплата должна быть такой:\n"
                    f"**{rank['event_10min_payout'] * ((event_duration + 3) // 10)} "
                    f"= {rank['event_10min_payout']} * (({event_duration} + 3)/ 10)**",
                    failure=True,
                ),
                ephemeral=True,
            )
            return

        payout_amount = rank["event_10min_payout"] * ((event_duration + 3) // 10)
        await inter.send(
            f"Ивент `{event_title}`\nДлительность "
            f"**{event_duration} мин. ({start_hour}:{start_minute} - {end_hour}:{end_minute})**\n"
            f"Ранк **{rank['name']}**\n"
            f"Выплата **{payout_amount} = {rank['event_10min_payout']} * (({event_duration} + 3)/ 10)**"
        )

        payouts_cog: Optional[Payouts] = self.bot.get_cog("Payouts")
        if payouts_cog is None:
            await inter.send(
                embed=build_simple_embed("Неизвестная ошибка", failure=True),
                ephemeral=True,
            )
            raise RuntimeError("Payouts cog not found")

        payouts_cog: Payouts
        result = await payouts_cog.payout(
            interaction=inter,
            user=message.author,
            amount=payout_amount,
            project=await models.StructureProject.objects.get(events_project_id),
            message=f"За ивент '{event_title}' ({event_duration} мин.) / {rank['name']}",
        )
        if result:
            for reaction in message.reactions:
                await reaction.remove(user=self.bot.user)
            await message.add_reaction("✅")
        else:
            await message.add_reaction("⚠")

    async def cog_load(self):
        """
        Called when disnake bot object is ready
        """

        logger.info("%s loaded", __name__)


def setup(bot: disnake.ext.commands.Bot):
    """
    Disnake internal setup function
    """
    bot.add_cog(FastInterpolPayouts(bot))
