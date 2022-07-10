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
            alias: str,
            name: str,
            guild_discord_id: int,
            role_discord_id: int,
            available: bool | int,
            webhook_url: str,
    ):
        self.alias = alias
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
                        alias = ?,
                        name = ?,
                        guild_discord_id = ?,
                        role_discord_id = ?,
                        available = ?,
                        webhook_url = ?
                WHERE alias = ? 
                """,
                (
                    self.alias,
                    self.name,
                    self.guild_discord_id,
                    self.role_discord_id,
                    int(self.available),
                    self.webhook_url,
                    self.alias,
                ),
            )
            await db.commit()

    async def edit(
            self,
            alias: Optional[str] = None,
            name: Optional[str] = None,
            guild_discord_id: Optional[int] = None,
            role_discord_id: Optional[int] = None,
            available: Optional[bool] = None,
            webhook_url: Optional[str] = None,
    ):
        if alias is not None:
            self.alias = alias
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
                """DELETE FROM structure_roles WHERE alias = ?""",
                (self.alias,),
            )
            await db.commit()


async def get_role(alias: str) -> Optional[Role]:
    async with aiosqlite.connect(PATH) as db:
        async with db.execute(
                """SELECT 
                        alias, name, guild_discord_id, role_discord_id, available, webhook_url
                        FROM structure_roles WHERE alias = ?
                        """,
                (alias,),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return Role(
                alias=row[0],
                name=row[1],
                guild_discord_id=row[2],
                role_discord_id=row[3],
                available=bool(row[4]),
                webhook_url=row[5],
            )


async def add_role(
        alias: str,
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
                        alias, name, guild_discord_id, role_discord_id, available, webhook_url
                    ) VALUES (?, ?, ?, ?, ?, ?)""",
                (alias, name, guild_discord_id, role_discord_id, available, webhook_url),
        ) as cursor:
            await db.commit()
            return await get_role(alias)


async def get_roles(guild_discord_id: Optional[int] = None) -> List[Role]:
    async with aiosqlite.connect(PATH) as db:
        async with db.execute(
                """SELECT 
                        alias, name, guild_discord_id, role_discord_id, available, webhook_url
                        FROM structure_roles """
                + ("WHERE guild_discord_id = ?" if guild_discord_id is not None else ""),
                (guild_discord_id,) if guild_discord_id is not None else (),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                Role(
                    alias=row[0],
                    name=row[1],
                    guild_discord_id=row[2],
                    role_discord_id=row[3],
                    available=bool(row[4]),
                    webhook_url=row[5],
                )
                for row in rows
            ]
