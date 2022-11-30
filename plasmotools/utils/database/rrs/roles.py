from __future__ import annotations

import logging
from typing import Optional, List

import aiosqlite

from plasmotools import settings

logger = logging.getLogger(__name__)
PATH = settings.DATABASE_PATH

queries = [
    """
create table if not exists rrs_roles
(
    verified_by_plasmo INTEGER default 0,
    structure_guild_id INTEGER not null,
    structure_role_id  INTEGER not null,
    plasmo_role_id     INTEGER not null,
    disabled           INTEGER default 0,
    id                 integer not null
    primary key autoincrement
);
"""
]


async def setup_database():
    logger.info("Setting up database")
    async with aiosqlite.connect(PATH) as db:
        for query in queries:
            await db.execute(query)
        await db.commit()


class RRSRole:
    def __init__(
        self,
        _id: int,
        structure_guild_id: int,
        structure_role_id: int,
        plasmo_role_id: int,
        verified_by_plasmo: bool = False,
        disabled: bool = False,
    ):
        self.id = _id
        self.structure_guild_id = structure_guild_id
        self.structure_role_id = structure_role_id
        self.plasmo_role_id = plasmo_role_id
        self.verified_by_plasmo = verified_by_plasmo
        self.disabled = disabled

    async def push(self):
        async with aiosqlite.connect(PATH) as db:
            await db.execute(
                """
                UPDATE rrs_roles SET 
                verified_by_plasmo = ?,
                structure_guild_id = ?,
                structure_role_id = ?,
                plasmo_role_id = ?,
                disabled = ?
                WHERE id = ?
                """,
                (
                    int(self.verified_by_plasmo),
                    self.structure_guild_id,
                    self.structure_role_id,
                    self.plasmo_role_id,
                    int(self.disabled),
                    self.id,
                ),
            )
            await db.commit()

    async def edit(
        self,
        structure_guild_id: Optional[int] = None,
        structure_role_id: Optional[int] = None,
        plasmo_role_id: Optional[int] = None,
        verified_by_plasmo: Optional[bool] = None,
        disabled: Optional[bool] = None,
    ):
        if structure_guild_id is not None:
            self.structure_guild_id = structure_guild_id
        if structure_role_id is not None:
            self.structure_role_id = structure_role_id
        if plasmo_role_id is not None:
            self.plasmo_role_id = plasmo_role_id
        if verified_by_plasmo is not None:
            self.verified_by_plasmo = verified_by_plasmo
        if disabled is not None:
            self.disabled = disabled

        await self.push()

    async def delete(self):

        async with aiosqlite.connect(PATH) as db:
            await db.execute(
                """DELETE FROM rrs_roles WHERE id = ?""",
                (self.id,),
            )
            await db.commit()


async def get_rrs_role(_id: int) -> Optional[RRSRole]:
    async with aiosqlite.connect(PATH) as db:
        async with db.execute(
            """ SELECT id, structure_guild_id, structure_role_id, plasmo_role_id, verified_by_plasmo, disabled FROM rrs_roles WHERE id = ?""",
            (_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return RRSRole(
                _id=row[0],
                structure_guild_id=row[1],
                structure_role_id=row[2],
                plasmo_role_id=row[3],
                verified_by_plasmo=bool(row[4]),
                disabled=bool(row[5]),
            )


async def register_rrs_role(
    structure_guild_id: int,
    structure_role_id: int,
    plasmo_role_id: int,
    verified_by_plasmo: bool = False,
    disabled: bool = False,
) -> RRSRole:
    async with aiosqlite.connect(PATH) as db:
        async with db.execute(
            """
            INSERT INTO rrs_roles (structure_guild_id, structure_role_id, plasmo_role_id, verified_by_plasmo, disabled)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                structure_guild_id,
                structure_role_id,
                plasmo_role_id,
                int(verified_by_plasmo),
                int(disabled),
            ),
        ) as cursor:
            await db.commit()
            return await get_rrs_role(cursor.lastrowid)


async def get_rrs_roles(
    structure_role_id: Optional[int] = None,
    plasmo_role_id: Optional[int] = None,
    structure_guild_id: Optional[int] = None,
) -> List[RRSRole]:
    async with aiosqlite.connect(PATH) as db:
        async with db.execute(
            """
            SELECT id, structure_guild_id, structure_role_id, plasmo_role_id, verified_by_plasmo, disabled FROM rrs_roles
            WHERE
                (structure_role_id = ? OR ? IS NULL)
                AND (plasmo_role_id = ? OR ? IS NULL)
                AND (structure_guild_id = ? OR ? IS NULL)
            """,
            (
                structure_role_id,
                structure_role_id,
                plasmo_role_id,
                plasmo_role_id,
                structure_guild_id,
                structure_guild_id,
            ),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                RRSRole(
                    _id=row[0],
                    structure_guild_id=row[1],
                    structure_role_id=row[2],
                    plasmo_role_id=row[3],
                    verified_by_plasmo=bool(row[4]),
                    disabled=bool(row[5]),
                )
                for row in rows
            ]
