import logging

import disnake
from disnake import ApplicationCommandInteraction
from disnake.ext import tasks, commands

from plasmotools.utils.api.user import get_user_data

logger = logging.getLogger(__name__)


async def generate_profile_embeds(member: disnake.Member) -> [disnake.Embed]:
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
    main_embed = (
        disnake.Embed(
            title=f"{member.display_name}'s Plasmo Profile",
            color=disnake.Color.dark_purple(),
            description=f"""
        `Nickname`: {member_api_profile.get('nick', '**-**')}
        `Plasmo ID`: {member_api_profile.get('id', '**-**')}
        `Discord ID`: {member_api_profile.get('discord_id', '**-**')}
        `UUID`: ||{member_api_profile.get('uuid', '**-**')}||
        `Is banned?`: {member_api_profile.get('banned', False)}
        `Ban reason`: {member_api_profile.get('ban_reason', '**-**')}
        `Roles`: {member_api_profile.get('roles', '**-**')}
        `Access`: {member_api_profile.get('has_access', '**-**')}
        `In guild?`: {member_api_profile.get('in_guild', '**-**')}
        `Fusion`: {member_api_profile.get('fusion', '**-**')}
        """,
        )
        .set_footer(text="BETA VERSION")
        .set_thumbnail(
            url="https://rp.plo.su/avatar/"
            + member_api_profile.get("nick", "PlasmoTools")
        )
    )
    return [main_embed]


class Utils(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    @commands.is_owner()
    @commands.slash_command(name="say", dm_permission=False)
    async def msg(self, inter: disnake.ApplicationCommandInteraction, text: str):
        await inter.send("ok", ephemeral=True)
        await inter.channel.send(text)

    @commands.user_command(
        name="Get API Data",
        default_member_permissions=disnake.Permissions(send_messages=True),
    )
    async def profile_user_command(
        self, inter: ApplicationCommandInteraction, user: disnake.Member
    ):
        await inter.response.defer(ephemeral=True)
        await inter.edit_original_message(embeds=(await generate_profile_embeds(user)))

    async def cog_load(self):
        logger.info("%s Ready", __name__)


def setup(client):
    """
    Internal disnake setup function
    """
    client.add_cog(Utils(client))
