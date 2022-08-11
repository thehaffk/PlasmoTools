"""
Cog-file for synchronization nicknames and roles at GCA discord guild
"""
import logging

import disnake
from disnake import ApplicationCommandInteraction
from disnake.ext import commands

from plasmotools import settings

logger = logging.getLogger(__name__)


class GCATools(commands.Cog):
    """
    Cog for GCA(Grand Court of Appeal) tools - announcements
    """

    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

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
        Logs data about all gca decisions for admins

        """
        embed = disnake.Embed(
            description=" | ".join(
                [
                    str(user.id),
                    str(user.display_name),
                    str(user),
                    result,
                    "Очищать инвентарь" if clear_inventory else "",
                    "Сбрасывать проходку: " if reset_pass else "",
                    additions,
                    conditions,
                ]
            ),
        )
        components = []
        if "разбан" in result.lower():
            components.append(
                disnake.ui.Button(
                    custom_id=f"gca unban {user.id}",
                    label="Разбанить",
                    emoji="🔓",
                )
            )
        msg = await (self.bot.get_channel(settings.BACGuild.dev_logs_channel_id)).send(
            embed=embed,
            components=components,
        )
        await msg.add_reaction("✔")

    @commands.Cog.listener()
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id.startswith("gca unban"):
            if inter.author.id not in self.bot.owner_ids:
                return await inter.send(
                    embed=disnake.Embed(
                        title="У Вас недостаточно прав.",
                        description="Вам нужно быть "
                        "администратором Plasmo или разработчиком бота для использования этой функции.",
                        color=disnake.Color.red(),
                    ),
                    ephemeral=True,
                )

            user_id = inter.component.custom_id.split(" ")[-1]
            plasmo = self.bot.get_guild(settings.PlasmoRPGuild.guild_id)
            await inter.response.defer(ephemeral=True)
            try:
                await plasmo.unban(
                    disnake.Object(id=user_id),
                    reason=f"Разбан решением БАС / {inter.author.display_name}",
                )
            except disnake.NotFound:
                await inter.message.edit(components=[])
                return await inter.send(
                    embed=disnake.Embed(
                        title="Ошибка",
                        description=f"Не удалось разбанить пользователя: Пользователь не в бане",
                        color=disnake.Color.red(),
                    ),
                    ephemeral=True,
                )
            except disnake.HTTPException as err:
                return await inter.send(
                    embed=disnake.Embed(
                        title="Ошибка",
                        description=f"Не удалось разбанить пользователя: {err}",
                        color=disnake.Color.red(),
                    ),
                    ephemeral=True,
                )
            await inter.send(
                embed=disnake.Embed(
                    title="Успех",
                    description="Игрок разбанен",
                    color=disnake.Color.green(),
                ),
                ephemeral=True,
            )
            await inter.message.edit(components=[])

    @commands.slash_command(
        name="заявка",
        guild_ids=[settings.BACGuild.guild_id],
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
        reason: str,
    ):
        """
        Заявка отклонена

        Parameters
        ----------
        user: Игрок
        reason: Причина отклонения
        inter: ApplicationCommandInteraction object

        """
        await inter.response.defer(ephemeral=True)

        await (
            await self.bot.get_guild(settings.BACGuild.guild_id)
            .get_channel(settings.BACGuild.announcements_channel_id)
            .webhooks()
        )[0].send(
            content=user.mention,
            embed=disnake.Embed(
                title="🟥 Заявка отклонена",
                color=disnake.Color.red(),
                description=reason,
            ).set_footer(
                text=f"{inter.author.display_name} ㆍ Plasmo Tools",
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
            description=f"Положительно - **{result}{(', проходка обнуляется' if reset_pass else '')}**\n\n{additions}",
        ).set_footer(
            text=f"{inter.author.display_name} ㆍ Plasmo Tools",
            icon_url=f"https://rp.plo.su/avatar/{inter.author.display_name}",
        )

        if conditions:
            embed.add_field(name="Требования к игроку", value=conditions)

        self.announcements_channel: disnake.NewsChannel
        await (
            await self.bot.get_guild(settings.BACGuild.guild_id)
            .get_channel(settings.BACGuild.announcements_channel_id)
            .webhooks()
        )[0].send(content=user.mention, embed=embed)

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
    ):
        """
        Заявка будет рассмотрена в суде

        Parameters
        ----------
        user: Игрок
        inter: ApplicationCommandInteraction object


        """
        await inter.response.defer(ephemeral=True)

        gca_guild = self.bot.get_guild(settings.BACGuild.guild_id)

        self.announcements_channel: disnake.NewsChannel
        await (
            await gca_guild.get_channel(
                settings.BACGuild.announcements_channel_id
            ).webhooks()
        )[0].send(
            content=user.mention,
            embed=disnake.Embed(
                title="🟨 Заявка будет рассмотрена в суде",
                color=disnake.Color.yellow(),
            ).set_footer(
                text=f"{inter.author.display_name} ㆍ Plasmo Tools",
                icon_url=f"https://rp.plo.su/avatar/{inter.author.display_name}",
            ),
        )

        await inter.edit_original_message(content="Дело сделано")
        await user.add_roles(
            gca_guild.get_role(settings.BACGuild.defendant_role_id),
            reason="Дело будет рассмотрено в суде",
        )

    @commands.slash_command(
        name="суд",
        guild_ids=[settings.BACGuild.guild_id],
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
        addition: str = "Вы сможете позже подать заявку на следующий апелляционный суд",
    ):
        """
        Заявка рассмотрена в суде

        Parameters
        ----------
        user: Игрок
        addition: Примечание для игрока
        inter: ApplicationCommandInteraction object

        """
        await inter.response.defer(ephemeral=True)

        embed = disnake.Embed(
            title="🟥 Заявка рассмотрена в суде",
            color=disnake.Color.red(),
            description="Результат - **Отрицательно**",
        ).set_footer(
            text=f"{inter.author.display_name} ㆍ Plasmo Tools",
            icon_url=f"https://rp.plo.su/avatar/{inter.author.display_name}",
        )

        embed.add_field(name="Примечание", value=addition)

        gca_guild = self.bot.get_guild(settings.BACGuild.guild_id)

        self.announcements_channel: disnake.NewsChannel
        await (
            await gca_guild.get_channel(
                settings.BACGuild.announcements_channel_id
            ).webhooks()
        )[0].send(
            content=user.mention,
            embed=embed,
        )

        defendant_role = gca_guild.get_role(settings.BACGuild.defendant_role_id)

        if defendant_role in user.roles:
            await user.remove_roles(defendant_role)

        await inter.edit_original_message(content="Дело сделано")

    @court_placeholder.sub_command(
        name="положительно",
        guild_ids=[settings.BACGuild.guild_id],
    )
    async def court_accepted(
        self,
        inter: ApplicationCommandInteraction,
        user: disnake.Member,
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
            text=f"{inter.author.display_name} ㆍ Plasmo Tools",
            icon_url=f"https://rp.plo.su/avatar/{inter.author.display_name}",
        )

        if conditions:
            embed.add_field(name="Требования к игроку", value=conditions)

        gca_guild = self.bot.get_guild(settings.BACGuild.guild_id)

        self.announcements_channel: disnake.NewsChannel
        await (
            await gca_guild.get_channel(
                settings.BACGuild.announcements_channel_id
            ).webhooks()
        )[0].send(
            content=user.mention,
            embed=embed,
        )

        defendant_role = gca_guild.get_role(settings.BACGuild.defendant_role_id)

        if defendant_role in user.roles:
            await user.remove_roles(defendant_role)

        await inter.edit_original_message(content="Дело сделано")

        await self.log_for_admins(
            user=user,
            result=result,
            additions=additions,
            conditions=conditions,
            clear_inventory=clear_inventory,
            reset_pass=reset_pass,
        )

    @commands.slash_command(
        name="комитет",
        guild_ids=[settings.BACGuild.guild_id],
    )
    async def committee_placeholder(self, inter: ApplicationCommandInteraction):
        """
        Placeholder for sub commands
        """
        pass

    @committee_placeholder.sub_command(
        name="положительно",
        guild_ids=[settings.BACGuild.guild_id],
    )
    async def committee_accepted(
        self,
        inter: ApplicationCommandInteraction,
        user: disnake.Member,
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
        Заявка одобрена комитетом

        Parameters
        ----------
        user: Игрок
        result: Тип рассмотренной заявки
        conditions: Условия
        clear_inventory: Очистить инвентарь
        reset_pass: Сбросить проходку
        additions: Дополнительные условия, например снятие красных при разбане
        inter: ApplicationCommandInteraction object


        """
        await inter.response.defer(ephemeral=True)

        embed = disnake.Embed(
            title="🟩 Заявка рассмотрена комитетом",
            color=disnake.Color.dark_green(),
            description=f"Положительно - **{result}{(', проходка обнуляется' if reset_pass else '')}**\n\n{additions}",
        ).set_footer(
            text=f"{inter.author.display_name} ㆍ Plasmo Tools",
            icon_url=f"https://rp.plo.su/avatar/{inter.author.display_name}",
        )

        if conditions:
            embed.add_field(name="Требования к игроку", value=conditions)

        self.announcements_channel: disnake.NewsChannel
        await (
            await self.bot.get_guild(settings.BACGuild.guild_id)
            .get_channel(settings.BACGuild.announcements_channel_id)
            .webhooks()
        )[0].send(content=user.mention, embed=embed)
        await user.remove_roles(
            inter.guild.get_role(settings.BACGuild.committee_defendant_role_id),
            reason="Рассмотрено",
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

    @committee_placeholder.sub_command(
        name="отрицательно",
        guild_ids=[settings.BACGuild.guild_id],
    )
    async def committee_declined(
        self,
        inter: ApplicationCommandInteraction,
        user: disnake.Member,
        addition: str = "Вы сможете позже подать заявку на следующий апелляционный суд",
    ):
        """
        Заявка рассмотрена комитетом

        Parameters
        ----------
        user: Игрок
        addition: Примечание для игрока
        inter: ApplicationCommandInteraction object

        """
        await inter.response.defer(ephemeral=True)

        embed = disnake.Embed(
            title="🟥 Заявка рассмотрена комитетом",
            color=disnake.Color.red(),
            description="Результат - **Отрицательно**",
        ).set_footer(
            text=f"{inter.author.display_name} ㆍ Plasmo Tools",
            icon_url=f"https://rp.plo.su/avatar/{inter.author.display_name}",
        )

        embed.add_field(name="Примечание", value=addition)

        gca_guild = self.bot.get_guild(settings.BACGuild.guild_id)

        self.announcements_channel: disnake.NewsChannel
        await (
            await gca_guild.get_channel(
                settings.BACGuild.announcements_channel_id
            ).webhooks()
        )[0].send(
            content=user.mention,
            embed=embed,
        )

        await user.remove_roles(
            gca_guild.get_role(settings.BACGuild.committee_defendant_role_id),
            reason="Рассмотрено",
        )

        await inter.edit_original_message(content="Дело сделано")

    @committee_placeholder.sub_command(
        name="допущено",
        guild_ids=[settings.BACGuild.guild_id],
    )
    async def commitee_approved(
        self,
        inter: ApplicationCommandInteraction,
        user: disnake.Member,
    ):
        """
        Заявка будет рассмотрена на комитете

        Parameters
        ----------
        user: Игрок
        inter: ApplicationCommandInteraction object


        """
        await inter.response.defer(ephemeral=True)

        gca_guild = self.bot.get_guild(settings.BACGuild.guild_id)

        self.announcements_channel: disnake.NewsChannel
        await (
            await gca_guild.get_channel(
                settings.BACGuild.announcements_channel_id
            ).webhooks()
        )[0].send(
            content=user.mention,
            embed=disnake.Embed(
                title="🟨 Заявка будет рассмотрена комитетом",
                color=disnake.Color.yellow(),
            ).set_footer(
                text=f"{inter.author.display_name} ㆍ Plasmo Tools",
                icon_url=f"https://rp.plo.su/avatar/{inter.author.display_name}",
            ),
        )

        await inter.edit_original_message(content="Дело сделано")
        await user.add_roles(
            gca_guild.get_role(settings.BACGuild.committee_defendant_role_id),
            reason="Дело будет рассмотрено комитетом",
        )

    async def cog_load(self):
        """
        Called when disnake bot object is ready
        """

        logger.info("%s Ready", __name__)


def setup(client):
    """
    Disnake internal setup function
    """
    client.add_cog(GCATools(client))
