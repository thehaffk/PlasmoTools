import logging

import disnake
from disnake.ext import commands

from plasmotools import settings
from plasmotools.embeds import build_simple_embed
from plasmotools.plasmo_api import messenger

logger = logging.getLogger(__name__)


class ConfirmView(disnake.ui.View):
    def __init__(
        self,
    ):
        super().__init__(timeout=86400)
        self.decision = None
        self.user = None

    @disnake.ui.button(label="Подтвердить", style=disnake.ButtonStyle.green, emoji="✅")
    async def confirm(self, _: disnake.ui.Button, interaction: disnake.Interaction):
        self.decision = True
        self.user = interaction.author
        await interaction.response.send_message("Подтверждено", ephemeral=True)
        self.stop()

    @disnake.ui.button(label="Отменить", style=disnake.ButtonStyle.gray, emoji="❌")
    async def cancel(self, _: disnake.ui.Button, interaction: disnake.Interaction):
        self.decision = False
        self.user = interaction.author
        await interaction.response.send_message(
            "Операция успешно отменена", ephemeral=True
        )
        self.stop()


class ScheduledEventsSync(commands.Cog):
    """
    Cog for syncing scheduled events from culture guild to plasmo rp
    """

    def __init__(self, bot: disnake.ext.commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_guild_scheduled_event_create")
    async def on_guild_scheduled_event_create(self, event: disnake.GuildScheduledEvent):
        if event.creator.bot:
            return

        monitored_guild_id = settings.culture_guild.discord_id
        target_guild_id = settings.PlasmoRPGuild.guild_id
        mod_channel_id = settings.PlasmoRPGuild.moderators_channel_id
        mod_role_id = settings.PlasmoRPGuild.ads_moderator_role_id
        if settings.DEBUG:
            monitored_guild_id = settings.DevServer.guild_id
            target_guild_id = settings.LogsServer.guild_id
            mod_channel_id = settings.LogsServer.moderators_channel_id
            mod_role_id = settings.LogsServer.moderator_role_id

        if (
            event.guild.id != monitored_guild_id
            or event.entity_type != disnake.GuildScheduledEventEntityType.external
        ):
            return

        # ask event owner for confirmation
        view = ConfirmView()
        confirm_msg = await event.creator.send(
            content=event.url,
            embed=disnake.Embed(
                title="Вы хотите перенести ваш ивент в Plasmo RP?",
                description="Если вы хотите перенести ваш ивент в дискорд Plasmo RP, нажмите на кнопку ниже",
                color=disnake.Color.dark_green(),
            ),
            view=view,
        )
        await view.wait()
        if not view.decision:
            return await confirm_msg.delete()
        await confirm_msg.edit(
            embed=build_simple_embed("Ваш ивент отправлен на модерацию"),
            components=[],
            content="",
        )

        # create mod request in mod channel
        mod_channel = self.bot.get_channel(mod_channel_id)
        view = ConfirmView()
        invite_url = (
            (await event.guild.channels[0].create_invite(unique=False)).url
            + "?event="
            + str(event.id)
        )

        embed = disnake.Embed(
            title="Новый ивент",
            description=f"Создатель: {event.creator.mention}\n"
            f"Название: {event.name}\n"
            f"Описание: {event.description}\n"
            f"Дата: {disnake.utils.format_dt(event.scheduled_start_time, style='f') }\n"
            f"Ссылка: {event.url}",
            color=disnake.Color.dark_green(),
        )

        confirm_msg = await mod_channel.send(
            content=f"<@&{mod_role_id}> {invite_url}",
            embed=embed,
            view=view,
        )
        await view.wait()
        await confirm_msg.edit(
            embed=embed.add_field(
                name="Модератор",
                value=str(view.user.mention) if view.user is not None else "Timed out",
            ).add_field("Одобрено", value=str(view.decision)),
            view=None,
        )
        if not view.decision:
            await event.creator.send(
                f"Ваш ивент ({event.name}) был отклонён модераторами Plasmo, "
                f"ивент в дс культуры удалён"
            )
            await event.cancel(reason="Отклонено модераторами Plasmo")
            return

        # create event in target guild
        target_guild: disnake.Guild = self.bot.get_guild(target_guild_id)
        synced_event = await target_guild.create_scheduled_event(
            name=event.name,
            scheduled_start_time=event.scheduled_start_time,
            scheduled_end_time=event.scheduled_end_time,
            description=event.description,
            entity_type=disnake.GuildScheduledEventEntityType.external,  #
            entity_metadata=disnake.GuildScheduledEventMetadata(
                location=event.entity_metadata.location
            ),
            privacy_level=disnake.GuildScheduledEventPrivacyLevel.guild_only,
            image=event.image,
        )
        await event.creator.send(
            "Ваш ивент был успешно перенесён в Plasmo RP\n" + synced_event.url
        )

    @commands.Cog.listener("on_guild_scheduled_event_update")
    async def plasmo_event_start_listener(
        self, before: disnake.GuildScheduledEvent, after: disnake.GuildScheduledEvent
    ):
        target_guild_id = settings.PlasmoRPGuild.guild_id

        if settings.DEBUG:
            target_guild_id = settings.LogsServer.guild_id
        if before.guild.id != target_guild_id or not (
            before.status == disnake.GuildScheduledEventStatus.scheduled
            and after.status == disnake.GuildScheduledEventStatus.active
        ):
            return

        async for user in after.fetch_users():
            await messenger.send_mc_message(
                f"Ивент {after.name} начинается. Место проведения: {after.entity_metadata.location}",
                discord_id=user.id,
            )

    async def cog_load(self):
        logger.info("%s loaded", __name__)


def setup(client):
    """
    Internal disnake setup function
    """
    client.add_cog(ScheduledEventsSync(client))
