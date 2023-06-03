import disnake
from disnake.ext import commands

from plasmotools import settings


def blocked_users_slash_command_check():
    def predicate(inter: disnake.ApplicationCommandInteraction) -> bool:
        return inter.author.id not in settings.blocked_users_ids

    return commands.check(predicate)
