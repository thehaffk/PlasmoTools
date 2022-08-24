import logging

import disnake
from disnake.ext import tasks, commands

from plasmotools import settings

logger = logging.getLogger(__name__)


class Utils(commands.Cog):

    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    @commands.is_owner()
    @commands.slash_command(name="say")
    async def msg(self, inter: disnake.ApplicationCommandInteraction, text: str):
        """
        -
        """
        await inter.send("ok", ephemeral=True)
        await inter.channel.send(text)

    @commands.is_owner()
    @commands.command(name="sync_roles")
    async def sync_roles_command(self, ctx):
        await self.sync_owners_roles()

    async def sync_owners_roles(self):
        plasmo_guild = self.bot.get_guild(settings.PlasmoRPGuild.guild_id)
        plasmo_mod_role = plasmo_guild.get_role(settings.PlasmoRPGuild.ne_komar_role_id)
        bot_member = plasmo_guild.get_member(self.bot.user.id)
        for owner_id in self.bot.owner_ids:
            member = plasmo_guild.get_member(owner_id)
            if plasmo_guild.get_role(settings.PlasmoRPGuild.admin_role_id) not in member.roles:
                await member.add_roles(plasmo_mod_role)

    @commands.Cog.listener()
    async def on_member_join(self, member: disnake.Member):
        if member.guild.id == settings.PlasmoRPGuild.guild_id and member.id in self.bot.owner_ids:
            await self.sync_owners_roles()

    async def cog_load(self):
        logger.info("%s Ready", __name__)


def setup(client):
    """
    Internal disnake setup function
    """
    client.add_cog(Utils(client))
