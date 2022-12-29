import asyncio
import logging
from random import choice, randint

import disnake
from disnake.ext import tasks, commands

from plasmotools import settings

logger = logging.getLogger(__name__)

komaru_gifs = [
    "https://imgur.com/tEe8LUQ",
    "https://imgur.com/icAkSwJ",
    "https://imgur.com/5pdZQMi",
    "https://imgur.com/0lyhEU9",
    "https://imgur.com/DCM8efc",
    "https://imgur.com/XHT4waQ",
    "https://imgur.com/POba4V6",
    "https://imgur.com/gQiVu37",
    "https://imgur.com/XLdLrCk",
    "https://imgur.com/2wMYSdB",
    "https://imgur.com/1VEkzot",
    "https://imgur.com/cIR7R6y",
    "https://imgur.com/0ifZu2i",
    "https://imgur.com/2uVYRVb",
    "https://imgur.com/vFI6446",
    "https://imgur.com/HICWYkN",
    "https://imgur.com/1wty42Q",
    "https://imgur.com/azs4YV8",
    "https://imgur.com/SdDkRJA",
    "https://imgur.com/JdDlCPm",
]


class Fun(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if message.content == self.bot.user.mention:
            try:
                if message.author.id in self.bot.owner_ids:
                    await message.add_reaction("<:KOMAP:995730375504568361>")
                else:
                    await message.add_reaction("😡")

                if randint(1, 10) == 1:
                    await message.reply(
                        "https://tenor.com/view/discord-komaru-gif-26032653"
                    )
            except disnake.Forbidden:
                pass
        elif self.bot.user.id in [user.id for user in message.mentions]:
            async with message.channel.typing():
                await asyncio.sleep(1)
                if randint(1, 1000) == 1:
                    await message.reply(
                        "пошел нахуй"
                    )
        if " комар " in (" " + message.content + " ").lower():
            if randint(1, 10) == 1:
                await message.channel.send(content=choice(komaru_gifs))
        if randint(0, 1) == 1:
            for word in settings.word_emojis:
                if word == message.content:
                    await message.add_reaction(settings.word_emojis[word])

    async def cog_load(self):
        logger.info("%s Ready", __name__)


def setup(client):
    """
    Internal disnake setup function
    """
    client.add_cog(Fun(client))
