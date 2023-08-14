import logging

import disnake
from disnake.ext import commands

from plasmotools import checks, settings
from plasmotools.utils import api
from plasmotools.utils.embeds import build_simple_embed

logger = logging.getLogger(__name__)


class StructureStatictics(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    @commands.guild_only()
    @commands.default_member_permissions(manage_roles=True)
    @commands.slash_command(
        name="role-stats",
    )
    @checks.is_guild_registered()
    async def role_stats_command(
        self,
        inter: disnake.ApplicationCommandInteraction,
        role: disnake.Role,
    ):
        """
        Shows stats for all users with specified role {{ROLE_STATS_COMMAND}}

        Parameters
        ----------
        inter
        role: Role from which participants need to be shown {{ROLE_STATS_ROLE}}
        """
        await inter.send(
            embed=build_simple_embed(
                without_title=True,
                description=f"{settings.Emojis.loading2} Collecting statistics can take a long time, please wait...",
            ),
            ephemeral=True,
        )
        if len(role.members) > 80:
            return await inter.edit_original_message(
                embed=build_simple_embed(
                    "Подсчет статистики для роли с более чем 80 участниками временно недоступен",
                    failure=True,
                )
            )

        stats_text = f"Роль: {role.mention} | Игроков: {len(role.members)}\n"
        users = []
        for member in role.members:
            member_api_data = await api.user.get_user_data(discord_id=member.id)
            if member_api_data is None or member_api_data == {}:
                users.append((member, 0, 0, 0))
                continue
            user_stats = member_api_data.get("stats", {})
            users.append(
                (
                    member,
                    int(user_stats.get("all", 0) / 60 // 60),
                    int(user_stats.get("month", 0) / 60 // 60),
                    int(user_stats.get("week", 0) / 60 // 60),
                )
            )
        stats_text += "` all  month  week` user \n"
        for user_stats in sorted(users, key=lambda _: _[-1], reverse=True):
            if user_stats[0].display_name == "PlasmoTools":
                stats_text += f"`   0 -   0 -   0 ` {self.bot.user.mention}"
                continue

            stats_text += (
                "`" + " " * (4 - len(str(user_stats[1]))) + str(user_stats[1]) + " - "
            )
            stats_text += (
                " " * (3 - len(str(user_stats[2]))) + str(user_stats[2]) + " - "
            )
            stats_text += (
                " " * (3 - len(str(user_stats[3]))) + str(user_stats[3]) + " ` "
            )
            stats_text += f"{user_stats[0].mention}\n"
        stats_embed = disnake.Embed(
            title=f"Статистика наигранных часов",
            description=stats_text,
            color=role.color,
        )
        await inter.edit_original_message(
            embed=stats_embed.set_footer(
                text="Отсортировано по количеству часов за неделю"
            )
        )

    async def cog_load(self):
        """
        Called when disnake bot object is ready
        """

        logger.info("%s loaded", __name__)


def setup(bot: disnake.ext.commands.Bot):
    """
    Disnake internal setup function
    """
    bot.add_cog(StructureStatictics(bot))
