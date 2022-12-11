import logging

import disnake
from disnake.ext import commands

from plasmotools.utils import api
from plasmotools.utils.database import plasmo_structures as database

logger = logging.getLogger(__name__)


class StructureStatictics(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    @commands.guild_only()
    @commands.default_member_permissions(manage_roles=True)
    @commands.slash_command(
        name="role-stats",
    )
    async def role_stats_command(
        self, inter: disnake.ApplicationCommandInteraction, role: disnake.Role
    ):
        """
        Показывает статистику наигранных часов по роли
        """
        await inter.response.defer(ephemeral=True)
        guild = await database.get_guild(inter.guild.id)
        if guild is None:
            return await inter.edit_original_message(
                embed=disnake.Embed(
                    title="Ошибка",
                    description="Сервер не зарегистрирован как официальная структура",
                )
            )
        if len(role.members) > 25:
            return await inter.edit_original_message(
                embed=disnake.Embed(
                    title="Ошибка",
                    description="Подсчет статистики для роли с более чем 25 участниками временно недоступен",
                )
            )

        stats_embed = disnake.Embed(
            title=f"Статистика игроков с ролью {role.name}",
            description=f"Всего игроков: {len(role.members)}",
            color=role.color,
        )
        stats_text = ""
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
                    user_stats.get("all", 0) / 60 // 60,
                    user_stats.get("month", 0) / 60 // 60,
                    user_stats.get("week", 0) / 60 // 60,
                )
            )
        stats_text += "**all** - **month** - **week** - user\n"
        for user_stats in sorted(users, key=lambda _: _[-1], reverse=True):
            stats_text += f"{user_stats[1]} - {user_stats[2]} - {user_stats[3]} - {user_stats[0].mention}\n"

        stats_embed.add_field(name="Наиграно часов", value=stats_text)
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
