from __future__ import annotations

import logging
from typing import Optional, List

import aiosqlite

from plasmotools import settings

logger = logging.getLogger(__name__)

PATH = settings.DATABASE_PATH


# todo: crud interface for saved cards


class Project:
    def __init__(
            self,
            project_id: int,
            name: str,
            is_active: int | bool,
            guild_discord_id: int,
            webhook_url: str,
            from_card: Optional[int] = None,
            plasmo_bearer_token: Optional[str] = None,
    ):
        self.id = project_id
        self.name = name
        self.is_active = bool(is_active)
        self.guild_discord_id = guild_discord_id
        self.webhook_url = webhook_url
        self.from_card = from_card
        self.plasmo_bearer_token = plasmo_bearer_token

    async def push(self):
        async with aiosqlite.connect(PATH) as db:
            await db.execute(
                """
                UPDATE structure_projects SET 
                        name = ?,
                        is_active = ?,
                        guild_discord_id = ?,
                        webhook_url = ?,
                        from_card = ?,
                        plasmo_bearer_token = ?
                WHERE id = ? 
                """,
                (
                    self.name,
                    int(self.is_active),
                    self.guild_discord_id,
                    self.webhook_url,
                    self.from_card,
                    self.plasmo_bearer_token,
                    self.id,
                ),
            )
            await db.commit()

    async def edit(
            self,
            name: Optional[str] = None,
            is_active: Optional[int] = None,
            guild_discord_id: Optional[int] = None,
            webhook_url: Optional[str] = None,
            from_card: Optional[int] = None,
            plasmo_bearer_token: Optional[str] = None,
    ):
        if name is not None:
            self.name = name
        if is_active is not None:
            self.is_active = bool(is_active)
        if guild_discord_id is not None:
            self.guild_discord_id = guild_discord_id
        if webhook_url is not None:
            self.webhook_url = webhook_url
        if from_card is not None:
            self.from_card = from_card
        if plasmo_bearer_token is not None:
            self.plasmo_bearer_token = plasmo_bearer_token

        await self.push()

    async def delete(self):

        async with aiosqlite.connect(PATH) as db:
            await db.execute(
                """DELETE FROM structure_projects WHERE id = ?""",
                (self.id,),
            )
            await db.commit()


async def get_project(project_id: int) -> Optional[Project]:
    async with aiosqlite.connect(PATH) as db:
        async with db.execute(
                """SELECT 
                                        id, name, is_active, guild_discord_id, webhook_url, from_card, plasmo_bearer_token
                                        FROM structure_projects WHERE id = ?
                                        """,
                (project_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return Project(
                project_id=row[0],
                name=row[1],
                is_active=row[2],
                guild_discord_id=row[3],
                webhook_url=row[4],
                from_card=row[5],
                plasmo_bearer_token=row[6],
            )


async def register_project(
        name: str,
        is_active: int | bool,
        guild_discord_id: int,
        webhook_url: str,
        from_card: Optional[int] = None,
        plasmo_bearer_token: Optional[str] = None,
) -> Project:
    async with aiosqlite.connect(PATH) as db:
        cursor = await db.execute(
            """INSERT INTO structure_projects
             (name, is_active, guild_discord_id, webhook_url, from_card, plasmo_bearer_token)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                name,
                int(is_active),
                guild_discord_id,
                webhook_url,
                from_card,
                plasmo_bearer_token,
            ),
        )
        await db.commit()
        return await get_project(cursor.lastrowid)


async def get_projects(guild_discord_id: Optional[int] = None) -> List[Project]:
    async with aiosqlite.connect(PATH) as db:
        async with db.execute(
                """SELECT 
                                        id, name, is_active, guild_discord_id, webhook_url, from_card, plasmo_bearer_token
                                        FROM structure_projects """
                + ("WHERE guild_discord_id = ?" if guild_discord_id is not None else ""),
                (guild_discord_id,) if guild_discord_id is not None else (),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                Project(
                    project_id=row[0],
                    name=row[1],
                    is_active=row[2],
                    guild_discord_id=row[3],
                    webhook_url=row[4],
                    from_card=row[5],
                    plasmo_bearer_token=row[6],
                )
                for row in rows
            ]
