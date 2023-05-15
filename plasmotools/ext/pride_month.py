import datetime
import logging
from dataclasses import dataclass
from typing import Optional

import aiohttp
import disnake
from disnake.ext import commands, tasks

from plasmotools import settings

logger = logging.getLogger(__name__)

pride_month_event_id = 1103678285570904204


@dataclass()
class Guild:
    id: int
    pride_avatar_url: str
    original_avatar_url: str


guilds_to_edit = list()

# guilds_to_edit.append(Guild(id=813451608871796766,  # Plasmo
#                             pride_avatar_url="https://i.imgur.com/44sIPuM.jpg",
#                             original_avatar_url="https://i.imgur.com/lpUKyvx.png"))

guilds_to_edit.append(
    Guild(
        id=813451608871796766,  # Интерпол
        pride_avatar_url="https://i.imgur.com/44sIPuM.jpg",
        original_avatar_url="https://i.imgur.com/lpUKyvx.png",
    )
)
guilds_to_edit.append(
    Guild(
        id=866301587525861376,  # Экономика
        pride_avatar_url="https://i.imgur.com/ihVxTA5.jpg",
        original_avatar_url="https://i.imgur.com/uFDbkB4.png",
    )
)
guilds_to_edit.append(
    Guild(
        id=756750263351771146,  # Инфраструктура
        pride_avatar_url="https://i.imgur.com/xegaYV4.jpg",
        original_avatar_url="https://i.imgur.com/p1xzKXD.png",
    )
)
guilds_to_edit.append(
    Guild(
        id=923224449728274492,  # Суд
        pride_avatar_url="https://i.imgur.com/DpDpfLx.jpg",
        original_avatar_url="https://i.imgur.com/nsB3iXj.png",
    )
)
guilds_to_edit.append(
    Guild(
        id=855532780187156501,  # БАС
        pride_avatar_url="https://i.imgur.com/LlN1gIU.jpg",
        original_avatar_url="https://i.imgur.com/N66WYog.png",
    )
)
guilds_to_edit.append(
    Guild(
        id=814490777526075433,  # МКО
        pride_avatar_url="https://i.imgur.com/qEy8KuP.jpg",
        original_avatar_url="https://i.imgur.com/Mssu73W.png",
    )
)
guilds_to_edit.append(
    Guild(
        id=841392525499826186,  # Культура
        pride_avatar_url="https://i.imgur.com/fp5sBhv.jpg",
        original_avatar_url="https://i.imgur.com/Rivylr8.png",
    )
)
guilds_to_edit.append(
    Guild(
        id=872877081774657536,  # Бидрилс e
        pride_avatar_url="https://i.imgur.com/4KQ7uO9.png",
        original_avatar_url="https://imgur.com/nIk4s4x.png",
    )
)
guilds_to_edit.append(
    Guild(
        id=1007717949743829112,  # Порт 3
        pride_avatar_url="https://i.imgur.com/TpYqb34.png",
        original_avatar_url="https://i.imgur.com/2Ify7JA.png",
    )
)
guilds_to_edit.append(
    Guild(
        id=828683007635488809,  # ДД
        pride_avatar_url="https://i.imgur.com/hBG3r5J.png",
        original_avatar_url="https://i.imgur.com/kw0Kafw.png",
    )
)
guilds_to_edit.append(
    Guild(
        id=966785796902363188,  # ДДТ
        pride_avatar_url="https://i.imgur.com/B6rCBQz.png",
        original_avatar_url="https://i.imgur.com/0gQE4Ac.png",
    )
)


class PrideMonthManager(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot
        self.up_to_date_avatars_guild_ids = []  # for ratelimits
        self.up_to_date_events_guild_ids = []  # for ratelimits

    @tasks.loop(minutes=1)
    async def pride_avatars_check_task(self):
        datetime_now = datetime.datetime.now()
        if not (datetime_now.day == 1 and datetime_now.month == 6):
            return

        if len(self.up_to_date_avatars_guild_ids) == len(guilds_to_edit):
            logger.info("All avatars are up to date, disabling check")

            self.pride_avatars_check_task.stop()

        for guild in guilds_to_edit:
            if guild.id in self.up_to_date_avatars_guild_ids:
                continue

            current_guild: Optional[disnake.Guild] = self.bot.get_guild(guild.id)

            if not current_guild:
                logger.warning("Unable to get %i guild", guild.id)
                continue
            logger.info('Updating pride avatar for "%s" guild', current_guild)

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(guild.pride_avatar_url) as resp:
                        if resp.status != 200:
                            logger.warning(
                                "Unable to set pride avatar at %s guild: %s ",
                                current_guild,
                                str(resp.content),
                            )
                            continue
                        contents = await resp.read()
                await current_guild.edit(
                    icon=contents, reason="Welcome to Pride Month 2023!"
                )
                self.up_to_date_avatars_guild_ids.append(guild.id)
            except disnake.Forbidden:
                logger.warning("Unable to update avatar in %s", current_guild)


    @tasks.loop(minutes=5)
    async def pride_event_check_task(self):

        datetime_now = datetime.datetime.now()
        if not (datetime_now.day == 31 and datetime_now.month == 5):
            return

        if len(self.up_to_date_events_guild_ids) == len(guilds_to_edit) + 1:
            logger.info("All events are up to date, disabling check")
            self.pride_event_check_task.stop()

        for guild in [
            *guilds_to_edit,
            Guild(
                id=settings.PlasmoRPGuild.guild_id,
                pride_avatar_url="",
                original_avatar_url="",
            ),
        ]:
            if guild.id in self.up_to_date_events_guild_ids:
                continue

            current_guild: Optional[disnake.Guild] = self.bot.get_guild(guild.id)

            if not current_guild:
                logger.warning("Unable to get %i guild", guild.id)
                continue
            logger.info('Syncing pride event for "%s" guild', current_guild)

            pride_month_event = self.bot.get_guild(
                settings.LogsServer.guild_id
            ).get_scheduled_event(pride_month_event_id)
            if pride_month_event.guild_id == guild.id:
                continue
            try:
                logger.info("Creating pride month event in %s", current_guild)
                await current_guild.create_scheduled_event(
                    name=pride_month_event.name,
                    entity_type=pride_month_event.entity_type,
                    scheduled_start_time=pride_month_event.scheduled_start_time,
                    scheduled_end_time=pride_month_event.scheduled_end_time,
                    entity_metadata=pride_month_event.entity_metadata,
                    privacy_level=pride_month_event.privacy_level,
                    description=pride_month_event.description
                    + "\n\nSynced event author: **haffk** <@737501414141591594>",
                    image=pride_month_event.image,
                    reason="WELCOME TO PRIDE MONTH",
                )
                self.up_to_date_events_guild_ids.append(guild.id)
            except disnake.Forbidden:
                logger.warning("Unable to create scheduled event in %s", current_guild)

    @pride_avatars_check_task.before_loop
    async def before_pride_avatars_check_task(self):
        await self.bot.wait_until_ready()

    @pride_event_check_task.before_loop
    async def before_pride_event_check_task(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.pride_event_check_task.is_running():
            self.pride_event_check_task.start()
        if not self.pride_avatars_check_task.is_running():
            self.pride_avatars_check_task.start()

    async def cog_load(self):
        logger.info("%s Ready", __name__)


def setup(client):
    client.add_cog(PrideMonthManager(client))
