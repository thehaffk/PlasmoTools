import asyncio
import logging

import disnake
import requests
from disnake.ext import commands

import settings

logger = logging.getLogger(__name__)


def Difference(li1, li2):
    return list(set(li1) - set(li2)) + list(set(li2) - set(li1))


class PlasmoLogger(commands.Cog):
    def __init__(self, bot):

        self.monitored_roles = None
        self.nicknames_channel = None
        self.roles_channel = None
        self.bans_channel = None
        self.bot = bot
        self.digital_drugs = None

    @commands.Cog.listener()
    async def on_member_update(self, before, after):

        if before.guild.id != settings.plasmo_rp["id"]:
            return False

        if before.roles != after.roles:
            roles = Difference(before.roles, after.roles)

            for role in roles:
                if role.id not in self.monitored_roles:
                    continue

                log_embed = disnake.Embed(
                    title="Роль изменена",
                    color=disnake.Color.yellow(),
                    description=f"{after.mention}("
                    f"[{after.display_name}](https://rp.plo.su/u/"
                    f"{after.display_name})): \n"
                    f"Роль "
                    f'"{role.name}" {"выдана" if role in after.roles else "снята"}',
                )

                await self.nicknames_channel.send(
                    content=f"<@{before.id}>", embed=log_embed
                )

    @commands.Cog.listener()
    async def on_member_ban(self, guild, member):
        if guild.id != settings.plasmo_rp["id"]:
            return False
        member_data = requests.get(
            f"https://rp.plo.su/api/user/profile?discord_id={member.id}&fields=warns"
        ).json()
        redwarn_counter = 0
        for warn in member_data["data"]["warns"]:
            if not warn["revoked"] and warn["force"]:
                redwarn_counter += 1

        if "ban_reason" in member_data["data"]:
            reason = member_data["data"]["ban_reason"]
        else:
            reason = (
                "**причина не указана**"
                if redwarn_counter < 3
                else (
                    "За красные варны: **"
                    + member_data["data"]["warns"][0]["message"]
                    + "**"
                )
            )

        log_embed = disnake.Embed(
            title="Игрок забанен",
            color=disnake.Color.red(),
            description=f'[{member_data["data"]["nick"]}]'
            f'(https://rp.plo.su/u/{member_data["data"]["nick"]}) '
            f"был забанен\n"
            f"Причина: "
            f"{reason}",
        )
        msg = await self.bans_channel.send(content=f"<@{member.id}>", embed=log_embed)
        await msg.publish()

    @commands.Cog.listener()
    async def on_member_unban(self, guild, member):
        if not guild.id == settings.plasmo_rp_guild:
            return False
        if guild.id != settings.plasmo_rp["id"]:
            return False
        member_data = requests.get(
            f"https://rp.plo.su/api/user/profile?discord_id={member.id}"
        ).json()

        log_embed = disnake.Embed(
            title="Игрок разбанен",
            color=disnake.Color.green(),
            description=f'[{member_data["data"]["nick"]}]'
            f'(https://rp.plo.su/u/{member_data["data"]["nick"]}) '
            f"был разбанен\n",
        )
        await self.bans_channel.send(content=f"<@{member.id}>", embed=log_embed)

    @commands.Cog.listener()
    async def on_ready(self):
        self.digital_drugs = self.bot.get_guild(settings.digital_drugs["id"])
        self.bans_channel = self.digital_drugs.get_channel(
            settings.digital_drugs["bans"]
        )
        self.roles_channel = self.digital_drugs.get_channel(
            settings.digital_drugs["roles"]
        )
        self.nicknames_channel = self.digital_drugs.get_channel(
            settings.digital_drugs["nicknames"]
        )
        self.monitored_roles = [
            settings.plasmo_rp_roles[role] for role in settings.plasmo_rp_roles
        ]


        logger.info("Ready")


def setup(client):
    client.add_cog(PlasmoLogger(client))
