"""
Cog-file for listener, detects bans, unbans, role changes, cheats, deaths, fwarns in Plasmo RP Guild / Server
"""
import logging

import disnake
from disnake.ext import tasks, commands

logger = logging.getLogger(__name__)


class StatusPage(commands.Cog):
    """
    Cog for listener, detects bans, unbans, role changes, cheats, deaths, fwarns in Plasmo RP Guild / Server
    """

    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    '''   @commands.command(name="status")
    async def status(self, ctx: disnake.ext.commands.Context):
        """
        Check all penalties and cancel them if user is banned
        """
        # await ctx.reply("https://tenor.com/view/discord-komaru-gif-26032653")

        plasmo_guild = self.bot.get_guild(settings.PlasmoRPGuild.guild_id)
        if plasmo_guild is None:
            await ctx.reply("Plasmo RP Guild not found")
            return

        status_embed_text = ""
        for bot_name in settings.bots_to_ping:
            status_embed_text += f"{bot_name}: {settings.Emojis.loading}\n"

        status_embed = (
            disnake.Embed(
                title="Plasmo Status",
                colour=disnake.Colour.blue(),
            )
            .add_field(  # 0
                name="Bots",
                value=status_embed_text,
                inline=False,
            )
            .add_field(  # 1
                name="Permissions",
                value=f"Change nickname: {settings.Emojis.loading}",
                inline=False,
            )
            .add_field(  # 2
                name="Sites",
                value=settings.Emojis.loading,
                inline=False,
            )
        )
        message = await ctx.reply(embed=status_embed)

        status_embed_text = ""
        for bot_name in settings.bots_to_ping:
            status_embed_text += f"{bot_name}: "
            bot = plasmo_guild.get_member(settings.bots_to_ping[bot_name])
            if bot is None:
                status_embed_text += f"{settings.Emojis.disabled} Not found\n"
                continue
            bot: disnake.Member
            if bot.status != disnake.Status.invisible:
                status_embed_text += f"{settings.Emojis.online} Online\n"
            else:
                status_embed_text += f"{settings.Emojis.offline} Offline\n"
        status_embed.set_field_at(
            index=0,
            inline=False,
            name="Bots",
            value=status_embed_text,
        )

        permissions_text = "Change nickname: " + (
            settings.Emojis.enabled + " Enabled"
            if plasmo_guild.get_role(
                settings.PlasmoRPGuild.player_role_id
            ).permissions.change_nickname
            else settings.Emojis.disabled + " Disabled"
        )
        status_embed.set_field_at(
            index=1,
            inline=False,
            name="Permissions",
            value=permissions_text,
        )

        await message.edit(embed=status_embed)

        sites = ["`" + site + f"`: ⏳" for site in settings.sites_to_ping]
        status_embed.set_field_at(
            index=2,
            inline=False,
            name="Sites",
            value="\n".join(sites),
        )
        await message.edit(embed=status_embed)

        for index, site in enumerate(settings.sites_to_ping):
            sites[index] = "`" + site + "`: " + settings.Emojis.loading
            status_embed.set_field_at(
                index=2,
                inline=False,
                name="Sites",
                value="\n".join(sites),
            )
            await message.edit(embed=status_embed)
            if await api.utils.ping_site(site):
                sites[index] = "`" + site + "`: " + settings.Emojis.site_online
            else:
                sites[index] = "`" + site + "`: " + settings.Emojis.site_offline
            status_embed.set_field_at(
                index=2,
                inline=False,
                name="Sites",
                value="\n".join(sites),
            )
            await message.edit(embed=status_embed)

        await message.edit(embed=status_embed, delete_after=60)
    '''
    async def cog_load(self):
        logger.info("%s Ready", __name__)


def setup(client):
    """
    Internal disnake setup function
    """
    client.add_cog(StatusPage(client))
