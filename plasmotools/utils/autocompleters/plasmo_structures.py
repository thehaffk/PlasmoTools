import logging

import disnake

from plasmotools.utils.database.plasmo_structures import get_roles

logger = logging.getLogger(__name__)


async def role_autocompleter(
        inter: disnake.ApplicationCommandInteraction, value: str
) -> dict[str, str]:
    if inter.guild is None:
        return {}
    roles = await get_roles(guild_discord_id=inter.guild.id)

    return (
        {role.name: str(role.role_discord_id) for role in roles if role.available}
        if roles
        else {"Нет доступных ролей": "404"}
    )
