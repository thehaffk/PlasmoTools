from __future__ import annotations

import logging
from typing import Optional, List

import aiosqlite

from plasmotools import settings

logger = logging.getLogger(__name__)

PATH = settings.DATABASE_PATH


class Role:
    def __init__(
        self,
        name: str,
        guild_discord_id: int,
        role_discord_id: int,
        available: bool | int,
        webhook_url: str,
    ):
        self.name = name
        self.guild_discord_id = guild_discord_id
        self.role_discord_id = role_discord_id
        self.available = bool(available)
        self.webhook_url = webhook_url

    async def push(self):
        async with aiosqlite.connect(PATH) as db:
            await db.execute(
                """
                UPDATE structure_roles SET 
                        name = ?,
                        guild_discord_id = ?,
                        available = ?,
                        webhook_url = ?
                WHERE role_discord_id = ? 
                """,
                (
                    self.name,
                    self.guild_discord_id,
                    int(self.available),
                    self.webhook_url,
                    self.role_discord_id,
                ),
            )
            await db.commit()

    async def edit(
        self,
        name: Optional[str] = None,
        guild_discord_id: Optional[int] = None,
        role_discord_id: Optional[int] = None,
        available: Optional[bool] = None,
        webhook_url: Optional[str] = None,
    ):
        if name is not None:
            self.name = name
        if guild_discord_id is not None:
            self.guild_discord_id = guild_discord_id
        if role_discord_id is not None:
            self.role_discord_id = role_discord_id
        if available is not None:
            self.available = available
        if webhook_url is not None:
            self.webhook_url = webhook_url

        await self.push()

    async def delete(self):

        async with aiosqlite.connect(PATH) as db:
            await db.execute(
                """DELETE FROM structure_roles WHERE role_discord_id = ?""",
                (self.role_discord_id,),
            )
            await db.commit()


async def get_role(role_discord_id: int) -> Optional[Role]:
    async with aiosqlite.connect(PATH) as db:
        async with db.execute(
            """SELECT 
                                                name, guild_discord_id, role_discord_id, available, webhook_url
                                                FROM structure_roles WHERE role_discord_id = ?
                                                """,
            (role_discord_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return Role(
                name=row[0],
                guild_discord_id=row[1],
                role_discord_id=row[2],
                available=bool(row[3]),
                webhook_url=row[4],
            )


async def add_role(
    name: str,
    guild_discord_id: int,
    role_discord_id: int,
    available: bool | int,
    webhook_url: str,
) -> Role:
    available = bool(available)
    async with aiosqlite.connect(PATH) as db:
        async with db.execute(
            """INSERT INTO structure_roles (
                                                name, guild_discord_id, role_discord_id, available, webhook_url
                                            ) VALUES (?, ?, ?, ?, ?)""",
            (name, guild_discord_id, role_discord_id, available, webhook_url),
        ):
            await db.commit()
            return await get_role(role_discord_id)


async def get_roles(guild_discord_id: Optional[int] = None) -> List[Role]:
    async with aiosqlite.connect(PATH) as db:
        async with db.execute(
            """SELECT 
                                                name, guild_discord_id, role_discord_id, available, webhook_url
                                                FROM structure_roles """
            + ("WHERE guild_discord_id = ?" if guild_discord_id is not None else ""),
            (guild_discord_id,) if guild_discord_id is not None else (),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                Role(
                    name=row[0],
                    guild_discord_id=row[1],
                    role_discord_id=row[2],
                    available=bool(row[3]),
                    webhook_url=row[4],
                )
                for row in rows
            ]
