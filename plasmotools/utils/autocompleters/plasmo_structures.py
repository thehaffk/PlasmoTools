import logging

import disnake

from plasmotools.utils.database.plasmo_structures.projects import get_projects
from plasmotools.utils.database.plasmo_structures.roles import get_roles

logger = logging.getLogger(__name__)


async def role_autocompleter(
    inter: disnake.ApplicationCommandInteraction, value: str
) -> dict[str, str]:
    if inter.guild is None:
        return {}
    roles = await get_roles(guild_discord_id=inter.guild.id)
    roles = roles[:25]

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

    db_projects = await get_projects(guild_discord_id=inter.guild.id)
    db_projects = db_projects[:25]

    db_projects = {
        project.name: str(project.id)
        for project in db_projects
        if project.is_active and project.from_card is not None
    }
    if len(db_projects) == 0:
        db_projects = {"Нет доступных проектов": "404"}

    return db_projects
