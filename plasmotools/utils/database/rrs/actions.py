from __future__ import annotations

import logging
from typing import List, Optional

import aiosqlite

from plasmotools import settings

logger = logging.getLogger(__name__)
PATH = settings.DATABASE_PATH

queries = [
    """
create table if not exists rrs_actions 
(
    id                  integer not null
        primary key autoincrement,
    structure_role_id   integer not null,
    user_id             integer not null,
    author_id           integer not null,
    approved_by_user_id integer not null,
    is_role_granted     integer not null,
    reason              integer,
    date                utc     not null
);
"""
]


async def setup_database():
    logger.info("Setting up database")
    async with aiosqlite.connect(PATH) as db:
        for query in queries:
            await db.execute(query)
        await db.commit()


class RRSAction:
    def __init__(
        self,
        _id: int,
        structure_role_id: int,
        user_id: int,
        author_id: int,
        approved_by_user_id: int,
        is_role_granted: bool,
        reason: Optional[str],
        date: int,
    ):
        self.id = _id
        self.structure_role_id = structure_role_id
        self.user_id = user_id
        self.author_id = author_id
        self.approved_by_user_id = approved_by_user_id
        self.is_role_granted = is_role_granted
        self.reason = reason
        self.date = date

    async def push(self):
        async with aiosqlite.connect(PATH) as db:
            await db.execute(
                """
                UPDATE rrs_actions SET
                structure_role_id = ?,
                user_id = ?,
                author_id = ?,
                approved_by_user_id = ?,
                is_role_granted = ?,
                reason = ?,
                date = ?
                WHERE id = ?
                """,
                (
                    self.structure_role_id,
                    self.user_id,
                    self.author_id,
                    self.approved_by_user_id,
                    int(self.is_role_granted),
                    self.reason,
                    self.date,
                    self.id,
                ),
            )
            await db.commit()

    async def edit(
        self,
        structure_role_id: Optional[int] = None,
        user_id: Optional[int] = None,
        author_id: Optional[int] = None,
        approved_by_user_id: Optional[int] = None,
        is_role_granted: Optional[bool] = None,
        reason: Optional[str] = "-1",
        date: Optional[int] = None,
    ):
        if structure_role_id is not None:
            self.structure_role_id = structure_role_id
        if user_id is not None:
            self.user_id = user_id
        if author_id is not None:
            self.author_id = author_id
        if approved_by_user_id is not None:
            self.approved_by_user_id = approved_by_user_id
        if is_role_granted is not None:
            self.is_role_granted = is_role_granted
        if reason != "-1":
            self.reason = reason
        if date is not None:
            self.date = date

        await self.push()

    async def delete(self):
        async with aiosqlite.connect(PATH) as db:
            await db.execute(
                """DELETE FROM rrs_actions WHERE id = ?""",
                (self.id,),
            )
            await db.commit()


async def get_action(_id: int) -> Optional[RRSAction]:
    async with aiosqlite.connect(PATH) as db:
        async with db.execute(
            """ SELECT id, structure_role_id, user_id, author_id, approved_by_user_id, is_role_granted, reason, date FROM rrs_actions WHERE id = ?""",
            (_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return RRSAction(
                _id=row[0],
                structure_role_id=row[1],
                user_id=row[2],
                author_id=row[3],
                approved_by_user_id=row[4],
                is_role_granted=bool(row[5]),
                reason=row[6],
                date=row[7],
            )


async def register_action(
    structure_role_id: int,
    user_id: int,
    author_id: int,
    approved_by_user_id: int,
    is_role_granted: bool,
    reason: Optional[str],
    date: int,
) -> RRSAction:
    async with aiosqlite.connect(PATH) as db:
        async with db.execute(
            """
            INSERT INTO rrs_actions (structure_role_id, user_id, author_id, approved_by_user_id, is_role_granted, reason, date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                structure_role_id,
                user_id,
                author_id,
                approved_by_user_id,
                int(is_role_granted),
                reason,
                date,
            ),
        ) as cursor:
            await db.commit()
            return await get_action(cursor.lastrowid)


async def get_actions(
    structure_role_id: Optional[int] = None,
    user_id: Optional[int] = None,
    author_id: Optional[int] = None,
    approved_by_user_id: Optional[int] = None,
    is_role_granted: Optional[bool] = None,
    reason: Optional[str] = None,
    date: Optional[int] = None,
) -> List[RRSAction]:
    async with aiosqlite.connect(PATH) as db:
        async with db.execute(
            """
            SELECT id, structure_role_id, user_id, author_id, approved_by_user_id, is_role_granted, reason, date
            WHERE
                (structure_role_id = ? OR ? IS NULL)
                AND (user_id = ? OR ? IS NULL)
                AND (author_id = ? OR ? IS NULL)
                AND (approved_by_user_id = ? OR ? IS NULL)
                AND (is_role_granted = ? OR ? IS NULL)
                AND (reason = ? OR ? IS NULL)
                AND (date = ? OR ? IS NULL)
            """,
            (
                structure_role_id,
                structure_role_id,
                user_id,
                user_id,
                author_id,
                author_id,
                approved_by_user_id,
                approved_by_user_id,
                int(is_role_granted),
                is_role_granted,
                reason,
                reason,
            ),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                RRSAction(
                    _id=row[0],
                    structure_role_id=row[1],
                    user_id=row[2],
                    author_id=row[3],
                    approved_by_user_id=row[4],
                    is_role_granted=bool(row[5]),
                    reason=row[6],
                    date=row[7],
                )
                for row in rows
            ]
