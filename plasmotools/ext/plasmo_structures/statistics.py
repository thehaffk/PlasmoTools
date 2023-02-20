import logging

import disnake
from disnake import Localized
from disnake.ext import commands

from plasmotools import settings
from plasmotools.utils import api
from plasmotools.utils.database import plasmo_structures as database

logger = logging.getLogger(__name__)


class StructureStatictics(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    @commands.guild_only()
    @commands.default_member_permissions(manage_roles=True)
    @commands.slash_command(
        name=Localized("role-stats", key="ROLE_STATS_COMMAND_NAME"),
        description=Localized(key="ROLE_STATS_COMMAND_DESCRIPTION"),
    )
    async def role_stats_command(
        self,
        inter: disnake.ApplicationCommandInteraction,
        role: disnake.Role = commands.Param(
            name=Localized(key="ROLE_STATS_ROLE_NAME"),
            description=Localized(key="ROLE_STATS_ROLE_DESCRIPTION"),
        ),
    ):
        """
        Shows stats for all users with specified role

        Parameters
        ----------
        role: Role from which participants need to be shown
        """
        await inter.send(
            embed=disnake.Embed(
                color=disnake.Color.green(),
                title=f"{settings.Emojis.loading2} Calculating...",
                description="Collecting statistics can take a long time, please wait...",
            ),
            ephemeral=True,
        )
        guild = await database.get_guild(inter.guild.id)
        if guild is None:
            return await inter.edit_original_message(
                embed=disnake.Embed(
                    title="Ошибка",
                    description="Сервер не зарегистрирован как официальная структура",
                )
            )
        if len(role.members) > 80:
            return await inter.edit_original_message(
                embed=disnake.Embed(
                    title="Ошибка",
                    description="Подсчет статистики для роли с более чем 80 участниками временно недоступен",
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

        logger.info("%s Ready", __name__)


def setup(bot: disnake.ext.commands.Bot):
    """
    Disnake internal setup function
    """
    bot.add_cog(StructureStatictics(bot))
