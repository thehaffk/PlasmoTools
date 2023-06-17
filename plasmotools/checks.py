import disnake
from disnake.ext import commands

import plasmotools.utils.database.plasmo_structures.guilds as guilds_db
from plasmotools import settings
from plasmotools.ext.error_handler import GuildIsNotRegistered


def blocked_users_slash_command_check():
    def predicate(inter: disnake.ApplicationCommandInteraction) -> bool:
        return inter.author.id not in settings.blocked_users_ids

    return commands.check(predicate)


def is_guild_registered():
    async def predicate(inter):
        if (await guilds_db.get_guild(inter.guild.id)) is None:
            raise GuildIsNotRegistered()
        return True

    return commands.check(predicate)
