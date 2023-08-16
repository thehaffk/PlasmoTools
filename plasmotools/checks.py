import disnake
from disnake.ext import commands

from plasmotools import models, settings
from plasmotools.cogs.error_handler import GuildIsNotRegistered


def blocked_users_slash_command_check():
    def predicate(inter: disnake.ApplicationCommandInteraction) -> bool:
        return inter.author.id not in settings.blocked_users_ids

    return commands.check(predicate)


def is_guild_registered():
    async def predicate(inter):
        if not (
            await models.StructureGuild.objects.filter(
                discord_id=inter.guild.id
            ).exists()
        ):
            raise GuildIsNotRegistered()
        return True

    return commands.check(predicate)
