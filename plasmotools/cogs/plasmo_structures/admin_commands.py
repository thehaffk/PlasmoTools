import asyncio
import logging

import disnake
from disnake import ApplicationCommandInteraction, MessageInteraction
from disnake.ext import commands

from plasmotools import models
from plasmotools.embeds import build_simple_embed

logger = logging.getLogger(__name__)


class GuildEditingView(disnake.ui.View):
    def __init__(self, bot, guild_id: int):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.bot = bot
        self.alias = None
        self.player_role_id = None
        self.head_role_id = None
        self.public_chat_id = None
        self.logs_channel_id = None

    async def _update_database(self) -> bool:
        db_guild = await models.StructureGuild.objects.filter(
            discord_id=self.guild_id
        ).first()
        if db_guild is None and None in [
            self.alias,
            self.player_role_id,
            self.head_role_id,
            self.public_chat_id,
            self.logs_channel_id,
        ]:
            return False
        elif db_guild is not None:
            self.alias = self.alias or db_guild.alias
            self.player_role_id = self.player_role_id or db_guild.player_role_id
            self.head_role_id = self.head_role_id or db_guild.head_role_id
            self.public_chat_id = self.public_chat_id or db_guild.public_chat_channel_id
            self.logs_channel_id = self.logs_channel_id or db_guild.logs_channel_id

        await models.StructureGuild.objects.update_or_create(
            discord_id=self.guild_id,
            defaults={
                "alias": self.alias,
                "player_role_id": self.player_role_id,
                "head_role_id": self.head_role_id,
                "public_chat_channel_id": self.public_chat_id,
                "logs_channel_id": self.logs_channel_id,
            },
        )
        return True

    def _build_structure_guild_data_embed(self) -> disnake.Embed:
        embed = disnake.Embed(
            title=f"Данные о {self.bot.get_guild(self.guild_id).name}",
            color=disnake.Color.dark_green(),
            description=f"""\
`Алиас:` {self.alias}
`Роль игрока Plasmo:` <@&{self.player_role_id}> ||{self.player_role_id}||
`Роль главы:` <@&{self.head_role_id}> ||{self.head_role_id}||
`Публичный чат:` <#{self.public_chat_id}> ||{self.public_chat_id}||
`Служебный чат PT:` <#{self.logs_channel_id}> ||{self.logs_channel_id}||
`Айди сервера:` {self.guild_id}""",
        )
        if None in [
            self.alias,
            self.player_role_id,
            self.head_role_id,
            self.public_chat_id,
            self.logs_channel_id,
        ]:
            embed.description += (
                "\n\n**Не все данные внесены. Невозможно зарегистрировать сервер**"
            )
        else:
            embed.description += "\n\n**Сервер есть в базе данных**"

        return embed

    @disnake.ui.button(
        style=disnake.ButtonStyle.green,
        label="Редактировать alias",
        custom_id="edit_structure_guild_alias",
        emoji="📝",
    )
    async def edit_structure_guild_alias_button(
        self, _: disnake.ui.Button, inter: MessageInteraction
    ):
        await inter.response.send_modal(
            title="Редактирование alias",
            custom_id="structure_guild_register_alias_modal",
            components=[
                disnake.ui.TextInput(
                    label="Алиас",
                    placeholder="interpol",
                    custom_id="alias",
                    style=disnake.TextInputStyle.short,
                    min_length=1,
                    max_length=32,
                ),
            ],
        )

        try:
            modal_inter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=lambda i: i.custom_id == "structure_guild_register_alias_modal"
                and i.author.id == inter.author.id,
                timeout=600,
            )
        except asyncio.TimeoutError:
            self.alias = None
            return

        await modal_inter.response.defer(ephemeral=True)
        self.alias = modal_inter.text_values["alias"]

        await self._update_database()
        await modal_inter.delete_original_message()
        await inter.edit_original_response(
            embed=self._build_structure_guild_data_embed(),
        )

    @disnake.ui.role_select(max_values=1, placeholder="Роль игрока Plasmo")
    async def player_role_select(
        self, select: disnake.ui.RoleSelect, interaction: disnake.MessageInteraction
    ):
        if len(select.values) != 1:
            await interaction.send(
                embed=build_simple_embed(
                    "Нужно выбрать только 1 элемент", failure=True
                ),
                ephemeral=True,
            )
            await asyncio.sleep(5)
            return await interaction.delete_original_message()

        await interaction.response.defer(ephemeral=True)

        self.player_role_id = select.values[0].id

        await self._update_database()
        await interaction.edit_original_message(
            embed=self._build_structure_guild_data_embed(),
        )

    @disnake.ui.role_select(max_values=1, placeholder="Роль главы структуры")
    async def head_role_select(
        self, select: disnake.ui.RoleSelect, interaction: disnake.MessageInteraction
    ):
        if len(select.values) != 1:
            await interaction.send(
                embed=build_simple_embed(
                    "Нужно выбрать только 1 элемент", failure=True
                ),
                ephemeral=True,
            )
            await asyncio.sleep(5)
            return await interaction.delete_original_message()

        await interaction.response.defer(ephemeral=True)

        self.head_role_id = select.values[0].id

        await self._update_database()
        await interaction.edit_original_message(
            embed=self._build_structure_guild_data_embed(),
        )

    @disnake.ui.channel_select(
        max_values=1,
        placeholder="Публичный чат",
        channel_types=[disnake.ChannelType.text],
    )
    async def public_chat_select(
        self, select: disnake.ui.ChannelSelect, interaction: disnake.MessageInteraction
    ):
        if len(select.values) != 1:
            await interaction.send(
                embed=build_simple_embed(
                    "Нужно выбрать только 1 элемент", failure=True
                ),
                ephemeral=True,
            )
            await asyncio.sleep(5)
            return await interaction.delete_original_message()

        await interaction.response.defer(ephemeral=True)

        self.public_chat_id = select.values[0].id

        await self._update_database()
        await interaction.edit_original_message(
            embed=self._build_structure_guild_data_embed(),
        )

    @disnake.ui.channel_select(
        max_values=1,
        placeholder="Служебный чат PT",
        channel_types=[disnake.ChannelType.text],
    )
    async def pt_logs_channel_select(
        self, select: disnake.ui.ChannelSelect, interaction: disnake.MessageInteraction
    ):
        if len(select.values) != 1:
            await interaction.send(
                embed=build_simple_embed(
                    "Нужно выбрать только 1 элемент", failure=True
                ),
                ephemeral=True,
            )
            await asyncio.sleep(5)
            return await interaction.delete_original_message()

        await interaction.response.defer(ephemeral=True)

        self.logs_channel_id = select.values[0].id

        await self._update_database()
        await interaction.edit_original_message(
            embed=self._build_structure_guild_data_embed(),
        )


async def _get_guild_data_embed(guild: disnake.Guild) -> disnake.Embed:
    db_guild = await models.StructureGuild.objects.filter(discord_id=guild.id).first()
    if db_guild is None:
        return disnake.Embed(
            title=f"Данные о {guild.name}",
            color=disnake.Color.dark_green(),
            description="У сервера не установлен статус государственной структуры",
        )
    return disnake.Embed(
        title=f"Данные о {guild.name}",
        color=disnake.Color.dark_green(),
        description=f"""\
`Алиас:` {db_guild.alias}
`Роль игрока Plasmo:` <@&{db_guild.player_role_id}> ||{db_guild.player_role_id}||
`Роль главы:` <@&{db_guild.head_role_id}> ||{db_guild.head_role_id}||
`Публичный чат:` <#{db_guild.public_chat_channel_id}> ||{db_guild.public_chat_channel_id}||
`Служебный чат PT:` <#{db_guild.logs_channel_id}> ||{db_guild.logs_channel_id}||
`Айди сервера:` {db_guild.discord_id}""",
    )


class AdminCommands(commands.Cog):
    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    @commands.is_owner()
    @commands.guild_only()
    @commands.slash_command(
        name="guild",
    )
    async def admin_guild_command(self, inter: ApplicationCommandInteraction):
        """
        Административные утилиты для регистрации госструктуры
        """
        await inter.response.defer(ephemeral=True)

        guild_stats_embed = await _get_guild_data_embed(inter.guild)

        db_guild = await models.StructureGuild.objects.filter(
            discord_id=inter.guild.id
        ).first()
        if db_guild is None:
            components = (
                [
                    disnake.ui.Button(
                        style=disnake.ButtonStyle.green,
                        label="Зарегистрировать",
                        custom_id="register_structure_guild",
                        emoji="📝",
                    ),
                ]
                if inter.author.id in self.bot.owner_ids
                else []
            )
        else:
            components = (
                [
                    disnake.ui.Button(
                        style=disnake.ButtonStyle.green,
                        label="Редактировать",
                        custom_id="edit_structure_guild",
                        emoji="📝",
                    ),
                    disnake.ui.Button(
                        style=disnake.ButtonStyle.red,
                        label="Удалить",
                        custom_id="delete_structure_guild",
                        emoji="🗑️",
                    ),
                ]
                if inter.author.id in self.bot.owner_ids
                else []
            )

        await inter.edit_original_message(
            embed=guild_stats_embed,
            components=components,
        )

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id is None:
            return
        if inter.component.custom_id not in [
            "register_structure_guild",
            "edit_structure_guild",
            "delete_structure_guild",
        ]:
            return
        await inter.response.defer(ephemeral=True)

        guild_embed = await _get_guild_data_embed(inter.guild)

        if inter.component.custom_id in [
            "register_structure_guild",
            "edit_structure_guild",
        ]:
            guild_embed.title = "Редактирование сервера " + inter.guild.name
            await inter.edit_original_message(
                view=GuildEditingView(self.bot, inter.guild.id),
                embed=guild_embed,
            )
            return

        if (
            inter.component.custom_id == "delete_structure_guild"
            and inter.author.id in self.bot.owner_ids
        ):
            await models.StructureGuild.objects.filter(
                discord_id=inter.guild.id
            ).delete()
            await inter.edit_original_message(
                embed=build_simple_embed(
                    f"☠️ Сервер {inter.guild.name} удалён из базы данных",
                ),
                components=[
                    disnake.ui.Button(
                        style=disnake.ButtonStyle.green,
                        label="Зарегистрировать",
                        custom_id="register_structure_guild",
                        emoji="📝",
                    ),
                ],
            )
            return

        await inter.edit_original_message(
            embed=build_simple_embed(description="Неизвестная ошибка", failure=True),
            components=[],
        )


def setup(bot: disnake.ext.commands.Bot):
    """
    Disnake internal setup function
    """
    bot.add_cog(AdminCommands(bot))
