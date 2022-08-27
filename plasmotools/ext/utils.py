import logging

import disnake
from disnake.ext import tasks, commands

from plasmotools import settings
from plasmotools.utils.api.user import get_user_data

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
    @commands.command(name="sync_owner_roles")
    async def sync_roles_command(self, ctx):
        await self.sync_owners_roles()

    @commands.is_owner()
    @commands.command(name="sync_global_roles")
    async def sync_roles_command(self, ctx):
        await self.sync_global_roles()

    async def sync_owners_roles(self):
        plasmo_guild = self.bot.get_guild(settings.PlasmoRPGuild.guild_id)
        plasmo_mod_role = plasmo_guild.get_role(settings.PlasmoRPGuild.ne_komar_role_id)
        bot_member = plasmo_guild.get_member(self.bot.user.id)
        for owner_id in self.bot.owner_ids:
            member = plasmo_guild.get_member(owner_id)
            if (
                plasmo_guild.get_role(settings.PlasmoRPGuild.admin_role_id)
                not in member.roles
            ):
                await member.add_roles(plasmo_mod_role)

    async def sync_global_roles(self):
        plasmo_guild = self.bot.get_guild(settings.PlasmoRPGuild.guild_id)
        members_to_sync = plasmo_guild.members

        logs_channel = plasmo_guild.get_channel(settings.PlasmoRPGuild.logs_channel_id)

        for index, member in enumerate(members_to_sync):
            if (
                plasmo_guild.get_role(settings.PlasmoRPGuild.admin_role_id)
                in member.roles
            ) or (
                plasmo_guild.get_role(settings.PlasmoRPGuild.ne_komar_role_id)
                in member.roles
            ):
                continue
            logger.info(
                "[%i, %i] Syncing %s", index, len(members_to_sync), member.display_name
            )
            member_api_profile = await get_user_data(discord_id=member.id)

            if member_api_profile is None:
                continue

            if member_api_profile.get("banned", False):
                logger.info(
                    "%s %s is banned, but not banned", member.display_name, member.id
                )
                await logs_channel.send(
                    f"<@&{settings.PlasmoRPGuild.ne_komar_role_id}>\n⚠ {member.display_name} {member.mention} "
                    f"is banned, but not banned",
                    components=[
                        disnake.ui.Button(
                            label="ban",
                            emoji="☠",
                            style=disnake.ButtonStyle.red,
                            custom_id=f"ban {member.id}",
                        )
                    ],
                )
                continue
            if member_api_profile.get("roles", None) is None:
                continue
            for role in settings.api_roles:
                has_guild_role = (
                    local_role := plasmo_guild.get_role(settings.api_roles[role])
                ) in member.roles
                has_api_role = role in member_api_profile["roles"]

                if role == "support":
                    if (
                        has_guild_role
                        and member_api_profile["fusion"] == 0
                        and not member.bot
                        and "booster" not in member_api_profile["roles"]
                    ):
                        logger.info(
                            "Removing fusion role from %s %s bc API fusion data = 0",
                            member.display_name,
                            member.id,
                        )
                        await logs_channel.send(
                            f"Removing fusion role from {member.display_name} {member.mention}"
                        )
                        try:
                            await member.remove_roles(local_role, reason=f"API SYNC")
                        except disnake.Forbidden:
                            logger.info(
                                "Could not add %s to %s %s [has_guild_role = False, has_api_role = True]",
                                role,
                                member.display_name,
                                member.id,
                            )
                            await logs_channel.send(
                                f"Could not remove fusion role from {member.display_name} {member.mention}"
                            )
                        continue
                    elif (
                        ("booster" in member_api_profile["roles"])
                        and not member.bot
                        and not has_guild_role
                    ):
                        logger.info(
                            "Adding fusion role to %s %s bc of booster role",
                            member.display_name,
                            member.id,
                        )
                        await logs_channel.send(
                            f"Adding fusion role to {member.display_name} {member.mention} bc of booster role"
                        )
                        try:
                            await member.add_roles(local_role, reason=f"API SYNC")
                        except disnake.Forbidden:
                            logger.info(
                                "Could not add %s to %s %s",
                                role,
                                member.display_name,
                                member.id,
                            )
                            await logs_channel.send(
                                f"Could not add fusion role to {member.display_name} {member.mention}"
                            )
                        continue
                    elif member_api_profile["fusion"] != 0 and not has_guild_role:
                        logger.info(
                            "Adding fusion role to %s %s bc API fusion data != 0",
                            member.display_name,
                            member.id,
                        )
                        await logs_channel.send(
                            f"Adding fusion role to {member.display_name} {member.mention} bc API fusion data != 0"
                        )
                        try:
                            await member.add_roles(local_role, reason=f"API SYNC")
                        except disnake.Forbidden:
                            logger.info(
                                "Could not add %s to %s %s",
                                role,
                                member.display_name,
                                member.id,
                            )
                            await logs_channel.send(
                                f"Could not add fusion role to {member.display_name} {member.mention}"
                            )
                        continue

                if has_guild_role and not has_api_role:
                    logger.info(
                        "Removing %s from %s %s [has_guild_role = True, has_api_role = False]",
                        role,
                        member.display_name,
                        member.id,
                    )
                    await logs_channel.send(
                        f"Removing {role} from {member.display_name} {member.mention}"
                    )
                    try:
                        await member.remove_roles(local_role)
                    except disnake.Forbidden:
                        logger.info(
                            "Could not remove %s from %s %s [has_guild_role = True, has_api_role = False]",
                            role,
                            member.display_name,
                            member.id,
                        )
                        await logs_channel.send(
                            f"Could not remove {local_role} from {member.display_name} {member.mention}"
                        )

                    if role == "player":
                        await member.add_roles(
                            local_role, reason=f"Unable to reset pass"
                        )
                        await logs_channel.send(
                            f"Unable to reset pass for {member.display_name} {member.mention}, adding {local_role} role"
                        )
                        continue

                if not has_guild_role and has_api_role:
                    logger.info(
                        "Adding %s to %s %s [has_guild_role = False, has_api_role = True]",
                        role,
                        member.display_name,
                        member.id,
                    )
                    await logs_channel.send(
                        f"Adding {local_role} to {member.display_name} {member.mention}"
                    )
                    try:
                        await member.add_roles(local_role, reason=f"API SYNC")
                    except disnake.Forbidden:
                        logger.info(
                            "Could not add %s to %s %s [has_guild_role = False, has_api_role = True]",
                            role,
                            member.display_name,
                            member.id,
                        )
                        await logs_channel.send(
                            f"Could not add {local_role} to {member.display_name} {member.mention}"
                        )

    @commands.Cog.listener()
    async def on_member_join(self, member: disnake.Member):
        if (
            member.guild.id == settings.PlasmoRPGuild.guild_id
            and member.id in self.bot.owner_ids
        ):
            await self.sync_owners_roles()

    async def cog_load(self):
        logger.info("%s Ready", __name__)


def setup(client):
    """
    Internal disnake setup function
    """
    client.add_cog(Utils(client))
