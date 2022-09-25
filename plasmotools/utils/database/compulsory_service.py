from __future__ import annotations

import logging
from typing import Optional, List

import aiosqlite

from plasmotools import settings

logger = logging.getLogger(__name__)

PATH = settings.DATABASE_PATH



queries = [
    """
create table if not exists compulsory_service
(
    id              integer not null
        constraint compulsory_service_pk
            primary key autoincrement,
    user_discord_id integer not null,
    hours           integer not null,
    hours_remaining integer,
    issued_at       integer not null,
    unban           boolean default 0,
    comment        text,
    term            integer
);
""",
    """
    create unique index if not exists compulsory_service_id_uindex
    on compulsory_service (id);
    """,
]


async def setup_database():
    logger.info("Setting up database")
    async with aiosqlite.connect(PATH) as db:
        for query in queries:
            await db.execute(query)
        await db.commit()


class CSEntry:
    def __init__(
        self,
        entry_id: int,
        user_discord_id: int,
        hours: int,
        hours_remaining: int,
        issued_at: int,
        unban: bool,
        comment: str,
        term: Optional[int] = None,
    ):
        self.entry_id = entry_id
        self.user_discord_id = user_discord_id
        self.hours = hours
        self.hours_remaining = hours_remaining
        self.issued_at = issued_at
        self.unban = unban
        self.comment = comment
        self.term = term

    async def push(self):
        async with aiosqlite.connect(PATH) as db:
            await db.execute(
                """
                UPDATE compulsory_service SET 
                     user_discord_id = ?,
                        hours = ?,
                        hours_remaining = ?,
                        issued_at = ?,
                        unban = ?,
                        comment = ?,
                        term = ?

                WHERE id = ?
                """,
                (
                    self.user_discord_id,
                    self.hours,
                    self.hours_remaining,
                    self.issued_at,
                    int(self.unban),
                    self.comment,
                    self.term,
                    self.entry_id,
                ),
            )
            await db.commit()

    async def edit(
        self,
        user_discord_id: Optional[int] = None,
        hours: Optional[int] = None,
        hours_remaining: Optional[int] = None,
        issued_at: Optional[int] = None,
        unban: Optional[bool] = None,
        comment: Optional[str] = None,
        term: Optional[int] = -1,
    ):
        if user_discord_id is not None:
            self.user_discord_id = user_discord_id
        if hours is not None:
            self.hours = hours
        if hours_remaining is not None:
            self.hours_remaining = hours_remaining
        if issued_at is not None:
            self.issued_at = issued_at
        if unban is not None:
            self.unban = unban
        if comment is not None:
            self.comment = comment
        if term != -1:
            self.term = term

        await self.push()

    async def delete(self):

        async with aiosqlite.connect(PATH) as db:
            await db.execute(
                """DELETE FROM compulsory_service WHERE id = ?""",
                (self.entry_id,),
            )
            await db.commit()


async def get_cs_entry(_id: int) -> Optional[CSEntry]:
    async with aiosqlite.connect(PATH) as db:
        async with db.execute(
            """SELECT 
                        id, user_discord_id, hours, hours_remaining, issued_at, unban, comment, term
                        FROM compulsory_service WHERE id = ?""",
            (_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return CSEntry(
                entry_id=row[0],
                user_discord_id=row[1],
                hours=row[2],
                hours_remaining=row[3],
                issued_at=row[4],
                unban=bool(row[5]),
                comment=row[6],
                term=row[7],
            )


async def register_cs_entry(
    user_discord_id: int,
    hours: int,
    hours_remaining: int,
    issued_at: int,
    unban: bool,
    comment: str,
    term: Optional[int] = None,
) -> CSEntry:
    async with aiosqlite.connect(PATH) as db:
        async with db.execute(
            """INSERT INTO compulsory_service 
                (user_discord_id, hours, hours_remaining, issued_at, unban, comment, term)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                user_discord_id,
                hours,
                hours_remaining,
                issued_at,
                int(unban),
                comment,
                term,
            ),
        ) as cursor:
            await db.commit()
            return await get_cs_entry(cursor.lastrowid)


async def get_cs_entries(user_id: Optional[int] = None) -> List[CSEntry]:
    async with aiosqlite.connect(PATH) as db:
        async with db.execute(
            """SELECT
                        id, user_discord_id, hours, hours_remaining, issued_at, unban, comment, term
                         FROM compulsory_service """
            + ("WHERE user_discord_id = ?" if user_id is not None else ""),
            (user_id,) if user_id is not None else (),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                CSEntry(
                    entry_id=row[0],
                    user_discord_id=row[1],
                    hours=row[2],
                    hours_remaining=row[3],
                    issued_at=row[4],
                    unban=bool(row[5]),
                    comment=row[6],
                    term=row[7],
                )
                for row in rows
            ]
