from __future__ import annotations

import logging
from typing import List, Optional

import aiosqlite

from plasmotools import settings

logger = logging.getLogger(__name__)

PATH = settings.DATABASE_PATH


class Patent:
    def __init__(
        self,
        patent_id: int,
        name: str,
        owner_discord_ids: List[int],
        banker_discord_id: int,
        moderator_discord_id: int,
        is_art: bool,
        decision: int = 0,
        map_ids: Optional[List[int]] = None,
    ):
        self.id = patent_id
        self.name = name
        self.owner_discord_ids = owner_discord_ids
        self.banker_discord_id = banker_discord_id
        self.moderator_discord_id = moderator_discord_id
        self.is_art = is_art
        self.decision = decision
        if map_ids is None:
            map_ids = []
        self.map_ids = map_ids

    async def push(self):
        async with aiosqlite.connect(PATH) as db:
            await db.execute(
                """
                UPDATE patents SET 
                name = ?,
                owner_ids = ?,
                banker_id = ?,
                moderator_id = ?,
                is_art = ?,
                decision = ?,
                map_ids = ?
                WHERE id = ? 
                """,
                (
                    self.name,
                    ", ".join(map(str, self.owner_discord_ids)),
                    self.banker_discord_id,
                    self.moderator_discord_id,
                    int(self.is_art),
                    self.decision,
                    ", ".join(map(str, self.map_ids)),
                    self.id,
                ),
            )
            await db.commit()

    async def edit(
        self,
        name: Optional[str] = None,
        owner_discord_ids: Optional[List[int]] = None,
        banker_discord_id: Optional[int] = None,
        moderator_discord_id: Optional[int] = None,
        is_art: Optional[bool] = None,
        decision: Optional[int] = None,
        map_ids: Optional[List[int]] = None,
    ):
        if name is not None:
            self.name = name
        if owner_discord_ids is not None:
            self.owner_discord_ids = owner_discord_ids
        if banker_discord_id is not None:
            self.banker_discord_id = banker_discord_id
        if moderator_discord_id is not None:
            self.moderator_discord_id = moderator_discord_id
        if is_art is not None:
            self.is_art = is_art
        if decision is not None:
            self.decision = decision
        if map_ids is not None:
            self.map_ids = map_ids

        await self.push()

    async def delete(self):
        async with aiosqlite.connect(PATH) as db:
            await db.execute(
                """DELETE FROM patents WHERE id = ?""",
                (self.id,),
            )
            await db.commit()


async def create_patent(
    name: str,
    owner_discord_ids: List[int],
    banker_discord_id: int,
    moderator_discord_id: int,
    is_art: bool,
    decision: int = 0,
    map_ids: Optional[List[int]] = None,
) -> Patent:
    if map_ids is None:
        map_ids = []
    async with aiosqlite.connect(PATH) as db:
        cursor = await db.execute(
            """INSERT INTO patents 
            (name, owner_ids, banker_id, moderator_id, is_art, decision, map_ids) 
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                name,
                ", ".join(map(str, owner_discord_ids)),
                banker_discord_id,
                moderator_discord_id,
                int(is_art),
                decision,
                ", ".join(map(str, map_ids)),
            ),
        )
        await db.commit()
        return await get_patent(cursor.lastrowid)


async def get_patent(patent_id: int) -> Optional[Patent]:
    async with aiosqlite.connect(PATH) as db:
        async with db.execute(
            """SELECT 
            id, name, owner_ids, banker_id, moderator_id, is_art, decision, map_ids
            FROM patents WHERE id = ?
            """,
            (patent_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return Patent(
                patent_id=row[0],
                name=row[1],
                owner_discord_ids=list(map(int, row[2].split(", "))),
                banker_discord_id=row[3],
                moderator_discord_id=row[4],
                is_art=row[5],
                decision=row[6],
                map_ids=list(map(int, row[7].split(", "))),
            )


async def get_projects(decision: Optional[int] = None) -> List[Patent]:
    async with aiosqlite.connect(PATH) as db:
        async with db.execute(
            """SELECT 
                id, name, owner_ids, banker_id, moderator_id, is_art, decision, map_ids
                 FROM patents """
            + ("WHERE description = ?" if decision is not None else ""),
            (decision,) if decision is not None else (),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                Patent(
                    patent_id=row[0],
                    name=row[1],
                    owner_discord_ids=list(map(int, row[2].split(", "))),
                    banker_discord_id=row[3],
                    moderator_discord_id=row[4],
                    is_art=row[5],
                    decision=row[6],
                    map_ids=list(map(int, row[7].split(", "))),
                )
                for row in rows
            ]
