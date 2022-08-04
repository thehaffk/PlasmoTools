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


async def payouts_projects_autocompleter(
        inter: disnake.ApplicationCommandInteraction, value: str
) -> dict[str, str]:
    """
    Returns a list of projects from this guild, where is_active is true and from_card is not null
    """
    if inter.guild is None:
        return {}
    from plasmotools.utils.database.plasmo_structures import get_projects

    projects = await get_projects(guild_discord_id=inter.guild.id)

    return {
        project.name: str(project.id)
        for project in projects
        if project.is_active and project.from_card is not None
    }
