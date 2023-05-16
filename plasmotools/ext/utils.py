import asyncio
import logging
from typing import Optional

import disnake
from disnake import ApplicationCommandInteraction, Localized
from disnake.ext import commands

from plasmotools import settings
from plasmotools.ext.reverse_role_sync.core import RRSCore
from plasmotools.utils import formatters
from plasmotools.utils.api import bank, messenger
from plasmotools.utils.api.user import get_user_data

logger = logging.getLogger(__name__)

colors = {
    Localized("Red", key="EMBED_COLOR_RED"): str(disnake.Color.red().value),
    Localized("Dark red", key="EMBED_COLOR_RED"): str(disnake.Color.dark_red().value),
    Localized("Green", key="EMBED_COLOR_RED"): str(disnake.Color.green().value),
    Localized("Dark green", key="EMBED_COLOR_RED"): str(
        disnake.Color.dark_green().value
    ),
    Localized("Without color", key="EMBED_COLOR_RED"): str(0x2F3136),
    Localized("Dark purple", key="EMBED_COLOR_RED"): str(
        disnake.Color.dark_purple().value
    ),
    Localized("Gray", key="EMBED_COLOR_RED"): str(disnake.Color.dark_gray().value),
}


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
        fusion_text = f"До <t:{fusion}:R>" if fusion else "Не куплен"

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
        try:
            await ctx.message.delete()
        except disnake.Forbidden:
            pass

    @commands.slash_command(
        name=Localized("embed", key="EMBED_COMMAND_NAME"),
        description=Localized(key="EMBED_COMMAND_DESCRIPTION"),
    )
    @commands.has_guild_permissions(manage_webhooks=True)
    async def embed_command(
        self,
        inter: disnake.ApplicationCommandInteraction,
        title: str = commands.Param(
            default="",
            name=Localized(key="EMBED_TITLE_NAME"),
            description=Localized(key="EMBED_TITLE_DESCRIPTION"),
        ),
        description: str = commands.Param(
            default="",
            name=Localized(key="EMBED_DESCRIPTION_NAME"),
            description=Localized(key="EMBED_DESCRIPTION_DESCRIPTION"),
        ),
        message_content: str = commands.Param(
            default="",
            name=Localized(key="EMBED_MESSAGE_CONTENT_NAME"),
            description=Localized(key="EMBED_MESSAGE_CONTENT_DESCRIPTION"),
        ),
        color: str = commands.Param(
            choices=colors,
            name=Localized(key="EMBED_COLOR_NAME"),
            description=Localized(key="EMBED_COLOR_DESCRIPTION"),
            default=str(0x2F3136),
        ),
    ):
        """
        Send embed without webhooks

        Parameters
        ----------
        title: Title field in embed
        description: Description field in embed
        message_content: Content beyond the embed
        color: Embed color
        """
        await inter.response.defer(ephemeral=True)
        embed = disnake.Embed(
            title=title,
            description=description,
            color=int(color),
        ).set_footer(
            text=inter.author,
            icon_url=f"https://rp.plo.su/avatar/{inter.author.display_name}",
        )
        await inter.edit_original_response(
            embed=embed,
            content=message_content,
            components=[
                disnake.ui.Button(
                    style=disnake.ButtonStyle.green,
                    label="Опубликовать",
                    custom_id="publish",
                )
            ],
        )
        try:
            await self.bot.wait_for(
                "button_click",
                check=lambda i: (i.component.custom_id == f"publish"),
                timeout=300,
            )
        except asyncio.TimeoutError:
            return await inter.edit_original_message(components=[])

        await inter.edit_original_message(components=[])
        await inter.channel.send(embed=embed, content=message_content)

    @commands.user_command(
        name=Localized("Profile", key="PROFILE_BUTTON_NAME"),
        default_member_permissions=disnake.Permissions(send_messages=True),
    )
    async def profile_user_command(
        self, inter: ApplicationCommandInteraction, user: disnake.Member
    ):
        await inter.response.defer(ephemeral=True)
        await inter.edit_original_message(
            embeds=(await self.generate_profile_embeds(user))
        )

    @commands.slash_command(
        name=Localized("help", key="HELP_COMMAND_NAME"),
        description=Localized(key="HELP_COMMAND_DESCRIPTION"),
    )
    async def help_command(self, inter: ApplicationCommandInteraction):
        """
        Get info about bot
        """
        await inter.send(
            ephemeral=True,
            embed=disnake.Embed(
                title=f"Plasmo Tools {settings.__version__}",
                color=disnake.Color.dark_green(),
                description=f"""
Plasmo Tools - многофункциональный бот для дискорд сервера Plasmo RP и государственных структур
    
Прочитать описание функционала и получить гайд по командам можно по ссылке: [notion.so]({settings.help_url})
Сервер поддержки: [discord.com/invite]({settings.DevServer.support_invite})
                """,
            ),
        )

    @commands.is_owner()
    @commands.slash_command(
        name="send-mc-message",
        description="Send message via plasmo messenger",
        guild_ids=[settings.DevServer.guild_id, settings.LogsServer.guild_id],
    )
    async def senc_mc_message_command(
        self,
        inter: ApplicationCommandInteraction,
        nickname: str,
        message: str,
        even_if_offline: bool = False,
    ):
        await inter.response.defer(ephemeral=True)
        status = await messenger.send_mc_message(
            nickname=nickname, message=message, even_if_offline=even_if_offline
        )
        await inter.edit_original_response(
            embed=disnake.Embed(
                description=f"PlasmoTools -> {nickname}: {message}\n"
                f"**Message status: {'success' if status else 'fail'}**"
            )
        )

    @commands.slash_command(
        name=Localized("treasury-balance", key="TREASURY_BALANCE_COMMAND_NAME"),
        description=Localized(key="TREASURY_BALANCE_COMMAND_DESCRIPTION"),
    )
    async def treasury_balance_command(self, inter: ApplicationCommandInteraction):
        """
        Get treasury balance for server and government structures
        """
        await inter.send(
            embed=disnake.Embed(
                color=disnake.Color.green(),
                title=f"{settings.Emojis.loading2} Calculating...",
                description="Collecting data can take a long time, please wait...",
            ),
            ephemeral=True,
        )
        embed_text = ""
        summary_balance = 0
        for card in list(range(1, 30)):
            card_formatted = formatters.format_bank_card(card)
            card_data = await bank.get_card_data(card, silent=True)
            if card_data is None:
                continue
            summary_balance += card_data["value"]
            embed_text += f"**{card_formatted}** {card_data['holder']} - {card_data['name']} - {card_data['value']}\n"

        embed_text += f"\n**Суммарно:** {summary_balance} алм."

        await inter.edit_original_response(
            embed=disnake.Embed(
                title="Казна сервера",
                description=embed_text,
                color=disnake.Color.dark_green(),
            )
        )

    async def cog_load(self):
        logger.info("%s Ready", __name__)


def setup(client):
    """
    Internal disnake setup function
    """
    client.add_cog(Utils(client))
