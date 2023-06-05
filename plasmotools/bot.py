import logging
from typing import Optional

import disnake
from disnake.ext import commands

from plasmotools import settings

logger = logging.getLogger()


class PlasmoTools(commands.Bot):
    """
    Base bot instance.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def create(cls) -> "PlasmoTools":
        """Create and return an instance of a Bot"""
        _intents = disnake.Intents.all()
        _intents.presences = False
        return cls(
            owner_ids=settings.owner_ids,
            status=disnake.Status.do_not_disturb,
            intents=_intents,
            command_prefix=commands.when_mentioned_or("pt."),
            help_command=None,
            description="Plasmo Tools",
            case_insensitive=True,
            reload=settings.DEBUG,
            strip_after_prefix=True,
            strict_localization=True,
        )

    async def on_ready(self):
        logger.info("Plasmo Tools %s is ready", settings.__version__)
        logger.info(f"Logged in as {self.user}")
        await self.change_presence(
            activity=disnake.Activity(
                type=disnake.ActivityType.playing,
                name=f"t.me/plasmotools | Version: {settings.__version__}",
            )
        )

        log_channel = self.get_channel(settings.DevServer.bot_logs_channel_id)
        await log_channel.send(
            embeds=[
                disnake.Embed(
                    title="New Connection",
                    description=f"Version: `{settings.__version__}`",
                ),
                disnake.Embed(
                    title="Запускаю проверку всех серверов...",
                    color=disnake.Color.dark_orange(),
                ),
            ]
        )

        plasmo_guild: Optional[disnake.Guild] = self.get_guild(
            settings.PlasmoRPGuild.guild_id
        )
        if plasmo_guild is not None:
            plasmo_guild: disnake.Guild
            await log_channel.send(
                embed=disnake.Embed(
                    title="Plasmo RP - подключение установлено",
                    color=disnake.Color.dark_green(),
                    description="Plasmo Tools есть на сервере",
                ).set_thumbnail(url=plasmo_guild.icon.url)
            )

            plasmo_guild_permissions = plasmo_guild.get_member(
                self.user.id
            ).guild_permissions
            if not all(
                [
                    plasmo_guild_permissions.ban_members,
                    plasmo_guild_permissions.view_audit_log,
                    plasmo_guild_permissions.manage_events,
                    plasmo_guild_permissions.send_messages,
                    plasmo_guild_permissions.add_reactions,
                    plasmo_guild_permissions.manage_messages,
                    plasmo_guild_permissions.read_message_history,
                ]
            ):
                await log_channel.send(
                    embed=disnake.Embed(
                        title="Недостаточно прав на Plasmo RP",
                        color=disnake.Color.dark_red(),
                        description="Обязательные для дальнейшей работы Plasmo Tools права отсутствуют, "
                        "передобавьте бота по [ссылке]"
                        "(https://discord.com/api/oauth2/authorize"
                        "?client_id=876907717837594646&permissions=420943834308&scope=bot%20applications.commands)",
                    )
                )

        else:
            await log_channel.send(
                embed=disnake.Embed(
                    title="Plasmo RP - невозможно подключиться",
                    color=disnake.Color.dark_red(),
                    description="Plasmo Tools отсутствует, добавьте его по [ссылке]"
                    "(https://discord.com/api/oauth2/authorize"
                    "?client_id=876907717837594646&permissions=422017617092&scope=bot%20applications.commands)",
                ).set_thumbnail(
                    url="https://media.discordapp.net/attachments/"
                    "980950597203292190/980952408811253840/-_.png"
                )
            )

        for structure_guild in settings.structure_guilds:
            guild = self.get_guild(structure_guild.discord_id)
            if guild is None:
                await log_channel.send(
                    embed=disnake.Embed(
                        title=f"{structure_guild.alias} - невозможно подключиться",
                        color=disnake.Color.dark_red(),
                        description="Plasmo Tools отсутствует, добавьте его по [ссылке]"
                        "(https://discord.com/api/oauth2/authorize"
                        "?client_id=876907717837594646&permissions=8&scope=bot%20applications.commands)",
                    ).set_thumbnail(
                        url="https://media.discordapp.net/attachments/"
                        "980950597203292190/980952408811253840/-_.png"
                    )
                )
                continue
            player_role = guild.get_role(structure_guild.player_role_id)
            head_role = guild.get_role(structure_guild.structure_head_role_id)
            chat = guild.get_channel(structure_guild.public_chat_channel_id)
            await log_channel.send(
                embed=disnake.Embed(
                    title=f"{guild} - подключение установлено",
                    color=disnake.Color.dark_green(),
                    description=f"`Player:` {player_role}\n`Head:` {head_role}\n`Chat:` {chat}",
                ).set_thumbnail(url=guild.icon.url)
            )
            if not guild.get_member(self.user.id).guild_permissions.administrator:
                await log_channel.send(
                    embed=disnake.Embed(
                        title=f"Недостаточно прав на {guild}",
                        color=disnake.Color.dark_red(),
                        description="Обязательные для дальнейшей работы Plasmo Tools права отсутствуют, "
                        "передобавьте бота по [ссылке]"
                        "(https://discord.com/api/oauth2/authorize"
                        "?client_id=876907717837594646&permissions=8&scope=bot%20applications.commands)",
                    )
                )
