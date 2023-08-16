import logging

import disnake

from plasmotools import models

logger = logging.getLogger(__name__)


async def role_autocompleter(
    inter: disnake.ApplicationCommandInteraction, _: str
) -> dict[str, str]:
    if inter.guild is None:
        return {}
    roles = (
        await models.StructureRole.objects.filter(
            guild_discord_id=inter.guild.id, is_available=True
        )
        .limit(25)
        .all()
    )

    return (
        {role.name: str(role.role_discord_id) for role in roles}
        if roles
        else {"Нет доступных ролей": "69420"}
    )


async def payouts_projects_autocompleter(
    inter: disnake.ApplicationCommandInteraction,
    _: str,
) -> dict[str, str]:
    """
    Returns a list of projects from this guild, where is_active is true and from_card is not null
    """
    if inter.guild is None:
        return {}

    db_projects = (
        await models.StructureProject.objects.filter(
            guild_discord_id=inter.guild.id,
            is_active=True,
        )
        .limit(25)
        .all()
    )

    db_projects = {
        project.name: str(project.id)
        for project in db_projects
        if project.from_card_str is not None and project.from_card_str != ""
    }
    if len(db_projects) == 0:
        db_projects = {"Нет доступных проектов": "69420"}

    return db_projects
