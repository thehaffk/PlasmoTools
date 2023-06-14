import logging
from typing import List

import disnake
from disnake.ext import commands

from plasmotools import checks, settings
from plasmotools.utils.api import banker

logger = logging.getLogger(__name__)


async def generate_bankers_stats_embeds(days=7) -> List[disnake.Embed]:
    transactions = await banker.get_banker_transactions(days)

    bankers = {}
    for transaction in transactions:
        if transaction["banker"] not in bankers:
            bankers[transaction["banker"]] = 0
        bankers[transaction["banker"]] += 1
    bankers = sorted(bankers.items(), key=lambda x: x[1], reverse=True)
    bankers_top = "\n`№. transactions` - user\n"
    for index, _banker in enumerate(bankers[:99]):
        bankers_top += f"`{index + 1}. {' ' * (3 - len(str(_banker[1])) + 2 - len(str(index + 1)))}{_banker[1]}` - " \
                       f"{disnake.utils.escape_markdown(_banker[0])} \n"
    if len(bankers) > 100:
        bankers_top += f"100 - {len(bankers) + 1} hidden"
    main_statistics_embed = disnake.Embed(
        title=f"Bank statistics for last {days} days",
        description=f"Total transactions: {len(transactions)}\n" + bankers_top,
        color=disnake.Color.green(),
    )
    return [main_statistics_embed]


async def generate_banker_stats_embeds(
    user: disnake.Member, days: int = 7
) -> List[disnake.Embed]:
    banker_stats_embed = disnake.Embed(
        title=f"Banker statistics for {user.display_name} for last {days} days",
        color=disnake.Color.green(),
        description="`Roles:`" + ", ".join([role.mention for role in user.roles[1:]]),
    )

    transactions = await banker.get_banker_transactions(days)
    transactions = [
        transaction
        for transaction in transactions
        if transaction["banker"] == user.display_name
    ]

    # 0 - card created
    # 1 - withdraw
    # 2 - deposit

    total_earned = 0
    for transaction in transactions:
        if transaction["action"] == 0:
            total_earned += 8  # todo: change if 4th season will have different numbers
            continue
        if transaction["amount"] <= 62:
            total_earned += 1
        elif transaction["amount"] <= 252:
            total_earned += 2
        else:
            total_earned += 4

    banker_stats_embed.add_field(
        name="Основная статистика",
        value=f"""
        Всего операций: `{len(transactions)}`
        Всего операций на сумму: `{sum([transaction["amount"] for transaction in transactions])}`
        Создано карт: `{len([transaction for transaction in transactions 
                             if transaction["action"] == 0])}`
        Создано удаленных карт: `{len([transaction for transaction in transactions 
                                       if transaction["action"] == 0 and transaction["card"]["name"] == ""] )}`
        Всего операций по снятию: `{len([transaction for transaction in transactions 
                                         if transaction["action"] == 1])}`
        Обналичено алмазов: `{sum([transaction["amount"] for transaction in transactions 
                                   if transaction["action"] == 1])}`
        Всего операций по пополнению: `{len([transaction for transaction in transactions 
                                             if transaction["action"] == 2])}`
        Пополнено алмазов: `{sum([transaction["amount"] for transaction in transactions 
                                  if transaction["action"] == 2])}`
        
        Всего заработано на комиссии: `{total_earned}`
            """,
        inline=False,
    )

    return [banker_stats_embed]


class BankerStats(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    async def cog_load(self):
        logger.info("%s Ready", __name__)

    @commands.slash_command(
        name="banker-stats",
        dm_permission=False,
        guild_ids=[
            settings.economy_guild.discord_id,
            settings.DevServer.guild_id,
            settings.LogsServer.guild_id,
        ],
    )
    @checks.blocked_users_slash_command_check()
    @commands.default_member_permissions(administrator=True)
    async def bankers_stats(
        self,
        inter: disnake.ApplicationCommandInteraction,
        days: int = commands.Param(gt=0, lt=366, default=7),
        user: disnake.Member = commands.Param(default=None),
    ):
        """
        Show statistics of all bankers / detailed by one employee {{BANKER_STATS_COMMAND}}

        Parameters
        ----------
        inter
        days: Number of days for which you need to get statistics {{BANKER_STATS_DAYS}}
        user: The user whose statistics you want to get {{BANKER_STATS_USER}}
        """
        await inter.send(
            embed=disnake.Embed(
                color=disnake.Color.green(),
                title=f"{settings.Emojis.loading2} Calculating...",
                description="Collecting statistics can take a long time, please wait...",
            ),
            ephemeral=True,
        )
        if user is None:
            embeds = await generate_bankers_stats_embeds(days)
        else:
            embeds = await generate_banker_stats_embeds(user, days)
        await inter.edit_original_message(embeds=embeds)

    @commands.user_command(
        name="Статистика банкира",
        guild_ids=[settings.economy_guild.discord_id],
    )
    @commands.default_member_permissions(administrator=True)
    async def banker_stats_buton(
        self, inter: disnake.ApplicationCommandInteraction, user: disnake.Member
    ):
        await inter.send(
            embed=disnake.Embed(
                color=disnake.Color.green(),
                title=f"{settings.Emojis.loading2} Calculating...",
                description="Collecting statistics can take a long time, please wait...",
            ),
            ephemeral=True,
        )
        weekly_embeds = await generate_banker_stats_embeds(user, 7)
        monthly_embeds = await generate_banker_stats_embeds(user, 28)
        await inter.edit_original_message(embeds=weekly_embeds + monthly_embeds)


def setup(client):
    """
    Internal disnake setup function
    """
    client.add_cog(BankerStats(client))
