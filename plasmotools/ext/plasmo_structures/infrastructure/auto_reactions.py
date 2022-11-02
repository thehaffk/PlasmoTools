import logging

import disnake
from disnake.ext import commands

logger = logging.getLogger(__name__)


class InfrastructureReactions(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    '''
    @commands.Cog.listener("on_message")
    async def on_message_listener(self, message: disnake.Message):
        if (
            message.guild is None
            or message.guild.id != settings.infrastructure_guild.discord_id
        ):
            return

        if message.channel.id != 1002511787234689084:
            return

        await message.add_reaction("🕒")
        await message.add_reaction("✅")
    '''

    async def cog_load(self):
        """
        Called when disnake bot object is ready
        """

        logger.info("%s Ready", __name__)


def setup(bot: disnake.ext.commands.Bot):
    """
    Disnake internal setup function
    """
    bot.add_cog(InfrastructureReactions(bot))
