import logging

import disnake
from disnake.ext import commands, tasks

from plasmotools import plasmo_api, settings
from plasmotools.embeds import build_simple_embed
from plasmotools.formatters import build_progressbar

logger = logging.getLogger(__name__)


class DailyReconciliation(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot
        self.strings_to_roles_dict = {
            "player": 746628733452025866,  # Старый игрок
            "new_player": 1122893850692829184,  #
            "fusion": 751722994170331136,  # Fusion
            "admin": 704364763248984145,  # Администрация
            "booster": 689093907912458312,  # Бустер
            "keeper": 1003276423747874896,  # Хранитель
            "helper": 1023622804794527805,  # Хелпер
            "soviet_member": 810492714235723777,  # Член совета глав
            "soviet_helper": 826366703591620618,  # Помощник совета глав
            "mko_helper": 844507728671277106,  # Участник Совета МКО
            "interpol": 751723033357451335,  # Интерпол
            "banker": 826367015014498314,  # Банкир
            "president": 880065048792420403,  # Президент
        }

        if settings.DEBUG:
            self.strings_to_roles_dict = {
                "player": 841098135376101377,  # Игрок
                "fusion": 841098260554317864,  # Fusion
                "admin": 843919496615034911,  # Администрация
                "keeper": 1118537860560191519,  # Хранитель
                "helper": 1118537993813233684,  # Хелпер
                "soviet_member": 873135550046023770,  # Член совета глав
                "soviet_helper": 932719709462331542,  # Помощник совета глав
                "mko_helper": 873135798814408735,  # Участник Совета МКО
                "interpol": 932719823027318864,  # Интерпол
                "banker": 873135413043273739,  # Банкир
                "president": 1112132073319305286,  # Президент
            }

        self.roles_to_strings_dict = {
            self.strings_to_roles_dict[role_string]: role_string
            for role_string in self.strings_to_roles_dict
        }

    @commands.command("run-plasmo_api-sync")
    @commands.is_owner()
    async def manually_run_check(self, ctx):
        await ctx.message.add_reaction("✅")
        await self.validate_all_discord_members()

    async def update_log_message(
        self, index, members, from_check=False, message=None
    ) -> disnake.Message:
        logs_channel = self.bot.get_channel(settings.LogsServer.daily_check_channel_id)
        embed = disnake.Embed(
            title=f"Ежедневная сверка участников дискорда {'Plasmo' if not settings.DEBUG else 'Digital Drugs'}",
            description=f"{'Scheduled' if from_check else 'Manual'}\n"
            f"{build_progressbar(index, len(members))}\n"
            f"Total: {len(members)}",
            color=disnake.Color.dark_green(),
        ).set_footer(text="digital drugs technologies")
        if message:
            await message.edit(embed=embed)
            return message
        else:
            return await logs_channel.send(embed=embed)

    async def log_error(self, member, api_data, message):
        logs_channel = self.bot.get_channel(settings.LogsServer.daily_check_channel_id)
        error_embed = disnake.Embed(
            title="Найдено расхождение",
            description=message,
            color=disnake.Color.dark_red(),
        )

        api_nick = disnake.utils.escape_markdown(api_data.get("nick", "MISSING"))
        user_embed = disnake.Embed(
            title="User data",
            description=f"""
            **Discord**:
            Nick: {member.display_name}
            Id: {member.id} {member.mention}
            Roles: {', '.join(['`' + role.name + '`' for role in member.roles][1:])}
            
            **API**
            Link: [u/{api_nick}](https://rp.plo.su/u/{api_nick})
            id: {api_data.get('id', "`MISSING`")}
            discord_id: {api_data.get('discord_id', "`MISSING`")}
            nick: {disnake.utils.escape_markdown(api_data.get('nick', "MISSING"))}
            uuid: {api_data.get('uuid', "`MISSING`")}
            banned: {api_data.get('banned', "`MISSING`")}
            fusion: {api_data.get('fusion', "`MISSING`")}
            in_guild: {api_data.get('in_guild', "`MISSING`")}
            roles: {api_data.get('roles', "`MISSING`")}
            """,
            color=disnake.Color.dark_grey(),
        )
        await logs_channel.send(
            content="<@&1118548383947305051>", embeds=[error_embed, user_embed]
        )

    # todo: check all bans
    async def validate_all_discord_members(self, from_check=False):
        logger.info("Running validate_all_discord_members")
        guild_to_sync = self.bot.get_guild(
            settings.PlasmoRPGuild.guild_id
            if not settings.DEBUG
            else settings.LogsServer.guild_id
        )
        if not guild_to_sync:
            logger.critical("Unable to get Plasmo Guild")
            return
        members_to_validate = guild_to_sync.members or []
        log_message = await self.update_log_message(
            index=0, members=members_to_validate, from_check=from_check
        )
        await log_message.pin()
        for index, member in enumerate(members_to_validate):
            if build_progressbar(index, len(members_to_validate)) != build_progressbar(
                index + 1, len(members_to_validate)
            ):
                await self.update_log_message(
                    index=index + 1,
                    members=members_to_validate,
                    from_check=from_check,
                    message=log_message,
                )
            discord_roles = []
            api_roles = []

            for role in member.roles:
                if role.id in self.roles_to_strings_dict:
                    discord_roles.append(self.roles_to_strings_dict[role.id])

            api_profile = await plasmo_api.user.get_user_data(discord_id=member.id)
            if api_profile is None:
                # logger.debug("Unable to get Plasmo Profile for %i", member.id)
                continue

            for role in api_profile.get("roles", []):
                if role in self.strings_to_roles_dict:
                    api_roles.append(role)
                elif role != "default":
                    logger.debug(
                        "Unknown API roles: %s at https://rp.plo.su/api/user/profile?discord_id=%i",
                        role,
                        member.id,
                    )

            # Checks
            if api_profile.get("banned", False) and not settings.DEBUG:
                await self.log_error(
                    member, api_profile, "**USER IS BANNED IN API, BUT NOT IN DISCORD**"
                )

                continue

            if api_profile.get("has_access", False) != (
                "player" in discord_roles or "new_player" in discord_roles
            ):
                await self.log_error(
                    member,
                    api_profile,
                    "**HAS_ACCESS AND PLAYER ROLE DO NOT MATCH:** \n"
                    + "plasmo_api      discord\n"
                    + disnake.utils.escape_markdown(
                        f"{api_profile.get('has_access')}    "
                        f"{'has role' if 'player' in discord_roles else 'doesnt have role'}"
                    ),
                )

            if not api_profile.get("has_access", False):
                if discord_roles:
                    await self.log_error(
                        member,
                        api_profile,
                        "**HAS_ACCESS IS FALSE, BUT PLAYER HAS DISCORD ROLES:** \n"
                        + "discord roles: "
                        + ",".join(discord_roles),
                    )
                continue  # Checking for plasmo_api roles / nickname / in_guild is unnececary if it has_access if 0

            if sorted(api_roles) != sorted(discord_roles):
                text = " ROLES ARE NOT THE SAME\n"
                text += "**Discord roles:**\n"
                text += "```diff\n"
                for role in set(discord_roles + api_roles):
                    if role not in discord_roles:
                        text += f"-{role}\n"
                    elif role not in api_roles:
                        text += f"+{role}\n"
                    else:
                        text += f"{role}\n"
                text += "```\n"

                text += "**API roles:**\n"
                text += "```diff\n"
                for role in set(discord_roles + api_roles):
                    if role not in api_roles:
                        text += f"-{role}\n"
                    elif role not in discord_roles:
                        text += f"+{role}\n"
                    else:
                        text += f"{role}\n"
                text += "```"

                await self.log_error(member, api_profile, text)

            #  todo: this?
            # if api_profile.get("nick") != member.display_name:
            #     await self.log_error(
            #         member,
            #         api_profile,
            #         "**NICKNAMES DO NOT MATCH:** \n"
            #         + "plasmo_api          discord\n"
            #         + disnake.utils.escape_markdown(
            #             f"'{api_profile.get('nick')}        '{member.display_name}'"
            #         ),
            #     )

            if not api_profile.get("in_guild", False) and not settings.DEBUG:
                await self.log_error(
                    member, api_profile, "**USER IS IN DISCORD, BUT in_guild IS FALSE**"
                )

        await self.bot.get_channel(settings.LogsServer.daily_check_channel_id).send(
            embed=build_simple_embed("Complete", failure=False)
        )
        await log_message.unpin()

    @tasks.loop(hours=24)
    async def daly_check_task(self):
        await self.validate_all_discord_members(from_check=True)

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.daly_check_task.is_running() and not settings.DEBUG:
            self.daly_check_task.start()

    async def cog_load(self):
        logger.info("%s loaded", __name__)


def setup(client):
    client.add_cog(DailyReconciliation(client))
