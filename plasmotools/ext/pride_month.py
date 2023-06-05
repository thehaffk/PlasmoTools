import datetime
import logging
from dataclasses import dataclass
from typing import Optional

import aiohttp
import disnake
from disnake.ext import commands, tasks

logger = logging.getLogger(__name__)

pride_month_event_id = 1103678285570904204


@dataclass()
class Guild:
    id: int
    pride_avatar_url: str
    original_avatar_url: str


guilds_to_edit = list()

guilds_to_edit.append(
    Guild(
        id=813451608871796766,  # Интерпол
        pride_avatar_url="https://cdn.discordapp.com/attachments/939520105874858014/1108044362945929236/44sIPuM.png",
        original_avatar_url="https://cdn.discordapp.com/attachments/980941642934673478/1114357563820089374/lpUKyvx.png",
    )
)
guilds_to_edit.append(
    Guild(
        id=866301587525861376,  # Экономика
        pride_avatar_url="https://cdn.discordapp.com/attachments/939520105874858014/1108044622015504404/ihVxTA5.png",
        original_avatar_url="https://cdn.discordapp.com/attachments/980941642934673478/1114357564164018246/uFDbkB4.png",
    )
)
guilds_to_edit.append(
    Guild(
        id=756750263351771146,  # Инфраструктура
        pride_avatar_url="https://media.discordapp.net/attachments/939520105874858014/1108044652046712954/xegaYV4.png",
        original_avatar_url="https://cdn.discordapp.com/attachments/980941642934673478/1114357564428271698/p1xzKXD.png",
    )
)
guilds_to_edit.append(
    Guild(
        id=923224449728274492,  # Суд
        pride_avatar_url="https://media.discordapp.net/attachments/939520105874858014/1108044667423047711/DpDpfLx.png",
        original_avatar_url="https://i.imgur.com/nsB3iXj.png",
    )
)
guilds_to_edit.append(
    Guild(
        id=855532780187156501,  # БАС
        pride_avatar_url="https://cdn.discordapp.com/attachments/939520105874858014/1108044686112866314/LlN1gIU.png",
        original_avatar_url="https://cdn.discordapp.com/attachments/980941642934673478/1114357564730253443/nsB3iXj.png",
    )
)
guilds_to_edit.append(
    Guild(
        id=814490777526075433,  # МКО
        pride_avatar_url="https://media.discordapp.net/attachments/939520105874858014/1108044704601350224/qEy8KuP.png",
        original_avatar_url="https://cdn.discordapp.com/attachments/980941642934673478/1114357565321650186/Mssu73W.png",
    )
)
guilds_to_edit.append(
    Guild(
        id=841392525499826186,  # Культура
        pride_avatar_url="https://media.discordapp.net/attachments/939520105874858014/1108044721839951912/fp5sBhv.png",
        original_avatar_url="https://cdn.discordapp.com/attachments/980941642934673478/1114357565577498706/Rivylr8.png",
    )
)


class PrideMonthManager(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot
        self.up_to_date_avatars_guild_ids = []

    @tasks.loop(minutes=10)
    async def pride_avatars_check_task(self):
        datetime_now = datetime.datetime.now()
        if not (datetime_now.day == 1 and datetime_now.month == 7):
            return

        for guild in guilds_to_edit:
            if guild.id in self.up_to_date_avatars_guild_ids:
                continue

            current_guild: Optional[disnake.Guild] = self.bot.get_guild(guild.id)

            if not current_guild:
                logger.warning("Unable to get %i guild", guild.id)
                continue
            logger.info('Resetting pride avatar for "%s" guild', current_guild)
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(guild.original_avatar_url) as resp:
                        if resp.status != 200:
                            logger.warning(
                                "Unable to reset pride avatar at %s guild: %s ",
                                current_guild,
                                str(resp.content),
                            )
                            continue
                        contents = await resp.read()
                await current_guild.edit(
                    icon=contents, reason="GOOD BYE, PRIDE MONTH, SEE U IN 2024"
                )
                self.up_to_date_avatars_guild_ids.append(guild.id)
            except disnake.Forbidden:
                logger.warning("Unable to update avatar in %s", current_guild)

        if len(self.up_to_date_avatars_guild_ids) == len(guilds_to_edit):
            logger.info("All avatars are up to date, disabling check")
            self.pride_avatars_check_task.stop()

    @pride_avatars_check_task.before_loop
    async def before_pride_avatars_check_task(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.pride_avatars_check_task.is_running():
            self.pride_avatars_check_task.start()

    async def cog_load(self):
        logger.info("%s Ready", __name__)


def setup(client):
    client.add_cog(PrideMonthManager(client))