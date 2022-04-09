"""
Cog-file for synchronization nicknames and roles at BAC discord guild
"""
import logging
import disnake
from disnake import ApplicationCommandInteraction
from disnake.ext import commands

import settings

logger = logging.getLogger(__name__)


# TODO: расписание сделать каким-то хуем
# TODO: синхронизация с бд игры через aiomysql
# TODO: синхронизация с бд кубов по кнопке


class BACTools(commands.Cog):  # TODO: Rename
    """
    Cog for GCA(Grand Court of Appeal) tools - announcements
    """

    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

        self.bac_guild = None
        self.bac_banned_role = None
        self.bac_has_pass_role = None
        self.defendant_role = None
        self.juror_role = None

        self.dev_logs_channel = None
        self.announcements_channel = None

    async def log_for_admins(
        self,
        user: disnake.Member,
        result: str,
        clear_inventory: bool,
        additions: str,
        reset_pass: bool,
        conditions: str,
    ):
        """
        Logs data about unbanned / or

        """
        msg = await self.dev_logs_channel.send(
            embed=disnake.Embed(
                description=" | ".join(
                    [
                        user.display_name,
                        str(user),
                        result,
                        "Очищать инвентарь: " + str(clear_inventory),
                        "Сбрасывать проходку: " + str(reset_pass),
                        additions,
                        conditions,
                    ]
                ),
            )
        )

        await msg.add_reaction("✔")

    @commands.guild_permissions(
        settings.BACGuild.guild_id,
        roles={
            settings.BACGuild.staff_role_id: True,
            settings.BACGuild.admin_role_id: True,
        },
        owner=True,
    )
    @commands.slash_command(
        name="заявка",
        guild_ids=[settings.BACGuild.guild_id],
        default_permission=False,
    )
    async def request_placeholder(self, inter: ApplicationCommandInteraction):
        """
        Placeholder for sub commands
        """
        pass

    @request_placeholder.sub_command(
        name="отклонена",
        guild_ids=[settings.BACGuild.guild_id],
    )
    async def request_declined(
        self,
        inter: ApplicationCommandInteraction,
        user: disnake.Member,
        tripetto_id: str,
        reason: str,
    ):
        """
        Заявка отклонена

        Parameters
        ----------
        user: Игрок
        tripetto_id: ID заявки
        reason: Причина отклонения
        inter: ApplicationCommandInteraction object

        """
        await inter.response.defer(ephemeral=True)

        await (await self.announcements_channel.webhooks())[0].send(
            content=user.mention,
            embed=disnake.Embed(
                title="🟥 Заявка отклонена",
                color=disnake.Color.red(),
                description=reason,
            ).set_footer(
                text=f"{inter.author.display_name} ㆍ ID: {tripetto_id}",
                icon_url=f"https://rp.plo.su/avatar/{inter.author.display_name}",
            ),
        )

        await inter.edit_original_message(content="Дело сделано")

    @request_placeholder.sub_command(
        name="одобрена",
        guild_ids=[settings.BACGuild.guild_id],
    )
    async def request_accepted(
        self,
        inter: ApplicationCommandInteraction,
        user: disnake.Member,
        tripetto_id: str,
        result: str = commands.Param(
            autocomplete=lambda *args: [
                "Разбан",
                "Красный варн снимается",
                "Два красных варна снимаются",
                "Разбан, красный варн снимается",
                "Разбан, два красных варна снимаются",
            ]
        ),
        conditions: str = "",
        clear_inventory: bool = False,
        reset_pass: bool = False,
        additions: str = "",
    ):
        """
        Заявка одобрена

        Parameters
        ----------
        user: Игрок
        tripetto_id: ID заявки
        result: Тип рассмотренной заявки
        conditions: Условия
        clear_inventory: Очистить инвентарь
        reset_pass: Сбросить проходку
        additions: Дополнительные условия, например снятие красных при разбане
        inter: ApplicationCommandInteraction object


        """
        await inter.response.defer(ephemeral=True)

        embed = disnake.Embed(
            title="🟩 Заявка одобрена",
            color=disnake.Color.dark_green(),
            description="Положительно - **{0}{1}**\n\n{2}".format(
                result, (f", проходка обнуляется" if reset_pass else ""), additions
            ),
        ).set_footer(
            text=f"{inter.author.display_name} ㆍ ID: {tripetto_id}",
            icon_url=f"https://rp.plo.su/avatar/{inter.author.display_name}",
        )

        if conditions:
            embed.add_field(name="Требования к игроку", value=conditions)

        self.announcements_channel: disnake.NewsChannel
        await (await self.announcements_channel.webhooks())[0].send(
            content=user.mention, embed=embed
        )

        await inter.edit_original_message(content="Дело сделано")

        await self.log_for_admins(
            user=user,
            result=result,
            additions=additions,
            conditions=conditions,
            clear_inventory=clear_inventory,
            reset_pass=reset_pass,
        )

    @request_placeholder.sub_command(
        name="допущена",
        guild_ids=[settings.BACGuild.guild_id],
    )
    async def request_approved(
        self,
        inter: ApplicationCommandInteraction,
        user: disnake.Member,
        tripetto_id: str,
    ):
        """
        Заявка будет рассмотрена в суде

        Parameters
        ----------
        user: Игрок
        tripetto_id: ID заявки
        inter: ApplicationCommandInteraction object


        """
        await inter.response.defer(ephemeral=True)

        self.announcements_channel: disnake.NewsChannel
        await (await self.announcements_channel.webhooks())[0].send(
            content=user.mention,
            embed=disnake.Embed(
                title="🟨 Заявка будет рассмотрена в суде",
                color=disnake.Color.yellow(),
            ).set_footer(
                text=f"{inter.author.display_name} ㆍ ID: {tripetto_id}",
                icon_url=f"https://rp.plo.su/avatar/{inter.author.display_name}",
            ),
        )

        await inter.edit_original_message(content="Дело сделано")
        await user.add_roles(
            self.defendant_role, reason="Дело будет рассмотрено в суде"
        )

    @commands.guild_permissions(
        settings.BACGuild.guild_id,
        roles={
            settings.BACGuild.staff_role_id: True,
            settings.BACGuild.admin_role_id: True,
        },
        owner=True,
    )
    @commands.slash_command(
        name="суд",
        guild_ids=[settings.BACGuild.guild_id],
        default_permission=False,
    )
    async def court_placeholder(self, inter: ApplicationCommandInteraction):
        """
        Placeholder for sub commands
        """
        pass

    @court_placeholder.sub_command(
        name="отрицательно",
        guild_ids=[settings.BACGuild.guild_id],
    )
    async def court_declined(
        self,
        inter: ApplicationCommandInteraction,
        user: disnake.Member,
        tripetto_id: str,
        addition: str = "Вы сможете позже подать заявку на следующий апелляционный суд",
    ):
        """
        Заявка рассмотрена в суде

        Parameters
        ----------
        user: Игрок
        tripetto_id: ID заявки
        addition: Примечание для игрока
        inter: ApplicationCommandInteraction object

        """
        await inter.response.defer(ephemeral=True)

        embed = disnake.Embed(
            title="🟥 Заявка рассмотрена в суде",
            color=disnake.Color.red(),
            description="Результат - **Отрицательно**",
        ).set_footer(
            text=f"{inter.author.display_name} ㆍ ID: {tripetto_id}",
            icon_url=f"https://rp.plo.su/avatar/{inter.author.display_name}",
        )

        embed.add_field(name="Примечание", value=addition)

        self.announcements_channel: disnake.NewsChannel
        await (await self.announcements_channel.webhooks())[0].send(
            content=user.mention,
            embed=embed,
        )

        if self.defendant_role in user.roles:
            await user.remove_roles(self.defendant_role)

        await inter.edit_original_message(content="Дело сделано")

    @court_placeholder.sub_command(
        name="положительно",
        guild_ids=[settings.BACGuild.guild_id],
    )
    async def court_accepted(
        self,
        inter: ApplicationCommandInteraction,
        user: disnake.Member,
        tripetto_id: str,
        result: str = commands.Param(
            autocomplete=lambda *args: [
                "Разбан",
                "Красный варн снимается",
                "Два красных варна снимаются",
                "Разбан, красный варн снимается",
                "Разбан, два красных варна снимаются",
            ]
        ),
        conditions: str = "",
        clear_inventory: bool = False,
        reset_pass: bool = False,
        additions: str = "",
    ):
        """
        Заявка рассмотрена в суде

        Parameters
        ----------
        user: Игрок
        tripetto_id: ID заявки
        result: Тип рассмотренной заявки
        conditions: Условия
        clear_inventory: Очистить инвентарь
        reset_pass: Сбросить проходку
        additions: Дополнительные условия, например снятие красных при разбане
        inter: ApplicationCommandInteraction object

        """
        await inter.response.defer(ephemeral=True)

        embed = disnake.Embed(
            title="🟩 Заявка рассмотрена в суде",
            color=disnake.Color.dark_green(),
            description="Положительно - **{0}{1}**\n\n{2}".format(
                result, (f", проходка обнуляется" if reset_pass else ""), additions
            ),
        ).set_footer(
            text=f"{inter.author.display_name} ㆍ ID: {tripetto_id}",
            icon_url=f"https://rp.plo.su/avatar/{inter.author.display_name}",
        )

        if conditions:
            embed.add_field(name="Требования к игроку", value=conditions)

        self.announcements_channel: disnake.NewsChannel
        await (await self.announcements_channel.webhooks())[0].send(
            content=user.mention, embed=embed
        )

        await inter.edit_original_message(content="Дело сделано")

        if self.defendant_role in user.roles:
            await user.remove_roles(self.defendant_role)

        await self.log_for_admins(
            user=user,
            result=result,
            additions=additions,
            conditions=conditions,
            clear_inventory=clear_inventory,
            reset_pass=reset_pass,
        )

    @commands.Cog.listener()
    async def on_ready(self):
        """
        Called when disnake bot object is ready
        """
        self.bac_guild: disnake.Guild = self.bot.get_guild(settings.BACGuild.guild_id)

        self.announcements_channel: disnake.NewsChannel = self.bac_guild.get_channel(
            settings.BACGuild.announcements_channel_id
        )
        self.dev_logs_channel: disnake.TextChannel = self.bac_guild.get_channel(
            settings.BACGuild.dev_logs_channel_id
        )

        self.defendant_role = self.bac_guild.get_role(
            settings.BACGuild.defendant_role_id
        )
        self.juror_role = self.bac_guild.get_role(settings.BACGuild.juror_role_id)
        self.bac_has_pass_role: disnake.Role = self.bac_guild.get_role(
            settings.BACGuild.has_pass_role_id
        )
        self.bac_banned_role: disnake.Role = self.bac_guild.get_role(
            settings.BACGuild.banned_role_id
        )

        logger.info("%s Ready", __name__)


def setup(client):
    """
    Disnake internal setup function
    """
    client.add_cog(BACTools(client))
