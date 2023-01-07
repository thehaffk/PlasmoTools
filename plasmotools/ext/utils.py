import logging
from typing import Optional

import disnake
from disnake import ApplicationCommandInteraction
from disnake.ext import tasks, commands

from plasmotools.ext.reverse_role_sync.core import RRSCore
from plasmotools.utils.api.user import get_user_data

logger = logging.getLogger(__name__)


class Utils(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    async def generate_profile_embeds(self, member: disnake.Member) -> [disnake.Embed]:
        """
        Generates a discord embeds for a member's plasmo profile
        """
        member_api_profile = await get_user_data(discord_id=member.id)
        if member_api_profile is None:
            return [
                disnake.Embed(
                    title=f"{member.display_name}'s Plasmo Profile",
                    description="This user has no Plasmo profile",
                    color=disnake.Color.red(),
                )
            ]
        fusion = member_api_profile.get("fusion", None)
        fusion_text = f"<t:{fusion}:R>" if fusion else "Не куплен"

        api_embed = (
            disnake.Embed(
                title=f"API Profile - {member.display_name}",
                color=disnake.Color.dark_purple(),
                url=f"https://rp.plo.su/u/{member_api_profile.get('nick', 'PlasmoTools')}",
                description=f"""
            `Nickname`: {member_api_profile.get('nick', '**-**')}
            `Plasmo ID`: {member_api_profile.get('id', '**-**')}
            `Discord ID`: {member_api_profile.get('discord_id', '**-**')}
            `UUID`: {member_api_profile.get('uuid', '**-**')}
            `Is banned?`: {member_api_profile.get('banned', False)}
            `Ban reason`: {member_api_profile.get('ban_reason', '**-**')}
            `Roles`: {member_api_profile.get('roles', '**-**')}
            `Access`: {member_api_profile.get('has_access', '**-**')}
            `In guild?`: {member_api_profile.get('in_guild', '**-**')}
            `Fusion`: {fusion_text}
            """,
            )
            .set_footer(text="Waiting for redesign")
            .set_thumbnail(
                url="https://rp.plo.su/avatar/"
                + member_api_profile.get("nick", "PlasmoTools")
            )
        )
        teams_text = ", ".join(
            [
                f"[{team['name']}](https://rp.plo.su/t/{team['url']})"
                for team in member_api_profile.get("teams", [])
            ]
        )
        if teams_text:
            api_embed.add_field(name="Teams", value=teams_text, inline=False)

        active_warns_text = "\n".join(
            [
                f"🔴 Выдал {warn['helper']} <t:{warn['date']}:R>\nПричина: {warn['message']}"
                for warn in member_api_profile.get("warns", [])
                if not warn["revoked"]
            ]
        )
        if active_warns_text:
            api_embed.add_field(
                name="Active warns", value=active_warns_text, inline=False
            )

        revoked_warns_text = "\n".join(
            [
                f"🟢 Выдал {warn['helper']} <t:{warn['date']}:R>\nПричина: {warn['message']}"
                for warn in member_api_profile.get("warns", [])
                if warn["revoked"]
            ]
        )
        if revoked_warns_text:
            api_embed.add_field(
                name="Revoked warns",
                value=revoked_warns_text
                if len(revoked_warns_text) < 1024
                else (
                    "**Unable to display all warns bc of discord limits\n**"
                    + revoked_warns_text[:950]
                    + "..."
                ),
                inline=False,
            )
        embeds = [api_embed]
        rrs_cog: Optional[RRSCore] = self.bot.get_cog("RRSCore")
        if rrs_cog is not None:
            embeds.append(await rrs_cog.generate_profile_embed(member))
        return embeds

    @commands.is_owner()
    @commands.command(name="say")
    async def msg(self, ctx, *, text: str):
        await ctx.channel.send(text)

    @commands.user_command(
        name="Profile",
        default_member_permissions=disnake.Permissions(send_messages=True),
    )
    async def profile_user_command(
        self, inter: ApplicationCommandInteraction, user: disnake.Member
    ):
        await inter.response.defer(ephemeral=True)
        await inter.edit_original_message(
            embeds=(await self.generate_profile_embeds(user))
        )

    async def cog_load(self):
        logger.info("%s Ready", __name__)


def setup(client):
    """
    Internal disnake setup function
    """
    client.add_cog(Utils(client))
