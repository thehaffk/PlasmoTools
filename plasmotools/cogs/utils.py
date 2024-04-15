import asyncio
import logging

import disnake
from disnake import ApplicationCommandInteraction, Localized
from disnake.ext import commands

from plasmotools import checks, formatters, settings
from plasmotools.embeds import build_simple_embed
from plasmotools.plasmo_api import bank, messenger, utils
from plasmotools.plasmo_api.user import get_user_data

logger = logging.getLogger(__name__)

colors = {
    Localized("Red", key="EMBED_COLOR_RED"): str(disnake.Color.dark_red().value),
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
                    color=disnake.Color.dark_red(),
                )
            ]
        fusion = member_api_profile.get("fusion", None)
        fusion_text = f"До <t:{fusion}:R>" if fusion else "Не куплен"

        api_embed = (
            disnake.Embed(
                title=f"API Profile - {member.display_name}",
                color=disnake.Color.dark_purple(),
                url=f"https://plasmorp.com/u/{member_api_profile.get('nick', 'PlasmoTools')}",
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
                url="https://plasmorp.com/avatar/"
                + member_api_profile.get("nick", "PlasmoTools")
            )
        )
        teams_text = ", ".join(
            [
                f"[{team['name']}](https://plasmorp.com/t/{team['url']})"
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
                value=(
                    revoked_warns_text
                    if len(revoked_warns_text) < 1024
                    else (
                        "**Unable to display all warns bc of discord limits\n**"
                        + revoked_warns_text[:950]
                        + "..."
                    )
                ),
                inline=False,
            )
        embeds = [api_embed]
        rrs_cog = self.bot.get_cog("RRSCore")
        if rrs_cog is not None:
            embeds.append(await rrs_cog.generate_profile_embed(member))  # type: ignore
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
        name="embed",
    )
    @commands.has_guild_permissions(manage_webhooks=True)
    @checks.blocked_users_slash_command_check()
    async def embed_command(
        self,
        inter: disnake.ApplicationCommandInteraction,
        title: str = commands.Param(
            default="",
        ),
        description: str = commands.Param(
            default="",
        ),
        message_content: str = commands.Param(
            default="",
        ),
        color: str = commands.Param(
            choices=colors,
            default=str(0x2F3136),
        ),
    ):
        """
        Send embed without webhooks  {{EMBED_COMMAND}}

        Parameters
        ----------
        inter: ApplicationCommandInteraction
        title: Title field in embed {{EMBED_TITLE}}
        description: Description field in embed {{EMBED_DESCRIPTION}}
        message_content: Content beyond the embed {{EMBED_MESSAGE_CONTENT}}
        color: Embed color {{EMBED_COLOR}}
        """
        await inter.response.defer(ephemeral=True)
        embed = disnake.Embed(
            title=title,
            description=description,
            color=int(color),
        ).set_footer(
            text=inter.author,
            icon_url=f"https://plasmorp.com/avatar/{inter.author.display_name}",
        )
        await inter.edit_original_response(
            embed=embed,
            content=message_content,
            components=[
                disnake.ui.Button(
                    style=disnake.ButtonStyle.green,
                    label="Опубликовать",
                    custom_id=f"publish_{inter.author.id}",
                )
            ],
        )
        try:
            await self.bot.wait_for(
                "button_click",
                check=lambda i: (i.component.custom_id == f"publish_{inter.author.id}"),
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

    @commands.slash_command(name="help")
    @checks.blocked_users_slash_command_check()
    async def help_command(self, inter: ApplicationCommandInteraction):
        """
        Get info about bot {{HELP_COMMAND}}
        """
        await inter.send(
            ephemeral=True,
            embed=disnake.Embed(
                title=f"Plasmo Tools {settings.__version__}",
                color=disnake.Color.dark_green(),
                description=f"""
Plasmo Tools - многофункциональный бот для дискорд сервера Plasmo RP и государственных структур
    
Прочитать описание функционала и получить гайд по командам можно по ссылке: [notion.so]({settings.HELP_URL})
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
    @checks.blocked_users_slash_command_check()
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
            embed=build_simple_embed(
                description=f"PlasmoTools -> {nickname}: {message}\n"
                f"**Message status: {'success' if status else 'fail'}**",
                without_title=True,
            )
        )

    @commands.slash_command(name="treasury-balance")
    @checks.blocked_users_slash_command_check()
    async def treasury_balance_command(self, inter: ApplicationCommandInteraction):
        """
        Get treasury balance for server and government structures {{TREASURY_BALANCE_COMMAND}}
        """
        await inter.send(
            embed=build_simple_embed(
                description=f"{settings.Emojis.loading2} Collecting data can take a long time, please wait...",
                without_title=True,
            ),
            ephemeral=True,
        )
        embed_text = ""
        summary_balance = 0
        for card in list(range(1, 30)):
            card_formatted = formatters.format_bank_card(card, bank_prefix="EB")
            card_data = await bank.get_card_data(card_formatted, supress_warnings=True)
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

    @commands.command(name="budget")
    async def budget_command(self, ctx: disnake.ext.commands.Context):
        pay2_data = await utils.get_pay2_stats()
        try:
            await ctx.message.reply(
                embed=build_simple_embed(
                    description=disnake.utils.escape_markdown(pay2_data),
                    without_title=True,
                ),
                delete_after=360,
            )
            await asyncio.sleep(360)
            await ctx.message.delete()
        except disnake.Forbidden:
            ...

    async def cog_load(self):
        logger.info("%s loaded", __name__)


def setup(client):
    """
    Internal disnake setup function
    """
    client.add_cog(Utils(client))
