"""
Cog-file for synchronization nicknames and roles at GCA discord guild
"""
import logging
import time

import disnake
from aiohttp import ClientSession
from disnake import ApplicationCommandInteraction
from disnake.ext import commands

import settings

logger = logging.getLogger(__name__)


class BankTools(commands.Cog):
    """
    Cog for GCA(Grand Court of Appeal) tools - announcements
    """

    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    @commands.guild_permissions(
        settings.DevServer.guild_id,
        users={
            384643212830310401: True,
        },
        owner=True,
    )
    @commands.slash_command(
        name="транзакции",
        guild_ids=[settings.DevServer.guild_id],
        default_permission=False,
    )
    async def request_placeholder(
            self,
            inter: ApplicationCommandInteraction,
            nickname: str = commands.Param(description="ник банкира, case sensitive", ge=3, le=16),
            days: int = commands.Param(description="количество дней", ge=1),
    ):
        """
        Получить статистику банкира (количество операций)
        """
        # TODO: Refactor this, it's scary

        # ⚠ BAD PRACTICE DO NOT COPY-PASTE
        # ⚠ BAD PRACTICE DO NOT COPY-PASTE
        # ⚠ BAD PRACTICE DO NOT COPY-PASTE

        logger.info("Trying to get transactions for %s by %s day(s)", nickname, days)
        await inter.response.defer(ephemeral=True)

        async with ClientSession() as session:
            headers = dict()
            headers["Accept"] = "application/json"
            headers["Authorization"] = f"Bearer {settings.PLASMO_BANKER_TOKEN}"
            async with session.get(
                    url=f"https://rp.plo.su/api/bank/banker/transactions/search?value={nickname}&to=1000000",
                    headers=headers,
            ) as response:
                response_json = await response.json()

                if (
                        response.status != 200
                        or response_json.get("status", False) is False
                ):
                    logger.warning(
                        "Could not get data from PRP API: %s",
                        response_json,
                    )
                    return False

                data = response_json.get("data", dict())
                transactions = data.get("list")
                if not transactions:
                    return await inter.edit_original_message(
                        embed=disnake.Embed(
                            title="❌",
                            description=f"Поиск по нику {nickname} ничего не вернул"
                        )
                    )
                last_transaction_id = transactions[0].get("id")
                search_results = data.get("total", 0)
                selected_time_counter = 0
                total_counter = 0
                cursor = last_transaction_id + 1

                for _ in range(search_results // 100 + 1):
                    async with ClientSession() as session:
                        headers = dict()
                        headers["Accept"] = "application/json"
                        headers["Authorization"] = f"Bearer {settings.PLASMO_BANKER_TOKEN}"
                        async with session.get(
                                url=f"https://rp.plo.su/api/bank/banker/transactions/search?value={nickname}"
                                    f"&to={cursor}&count=100",
                                headers=headers,
                        ) as response:
                            response_json = await response.json()

                            if (
                                    response.status != 200
                                    or response_json.get("status", False) is False
                            ):
                                logger.warning(
                                    "Could not get data from PRP API: %s",
                                    await response_json,
                                )
                                return False

                            data = response_json.get("data", dict())
                            transactions = data.get("list", "")

                            for transaction in transactions:
                                if transaction.get("banker") != nickname:
                                    continue

                                if transaction.get("date") >= int(time.time()) - (days * 24 * 60 * 60):
                                    selected_time_counter += 1
                                total_counter += 1

                            cursor = transactions[-1].get("id")

                banker_stats_embed = disnake.Embed(
                    title=f"Статистика {nickname}",
                    description=f"""
                    Транзакций, начиная с <t:{int(time.time()) - days * 24 * 60 * 60}:R> - **{selected_time_counter}**
                    Всего транзакций - **{total_counter}**
                    """,
                    colour=disnake.Color.dark_green()
                )

                await inter.edit_original_message(embed=banker_stats_embed)

    async def cog_load(self):
        """
        Called when disnake bot object is ready
        """

        logger.info("%s Ready", __name__)


def setup(client):
    """
    Disnake internal setup function
    """
    client.add_cog(BankTools(client))
