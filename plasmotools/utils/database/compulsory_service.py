'''
from __future__ import annotations

import logging
from typing import Optional, List

import aiosqlite

from plasmotools import settings

logger = logging.getLogger(__name__)

PATH = settings.DATABASE_PATH




class CSEntry:
    def __init__(
            self,
            entry_id: int,
            user_discord_id: int,
            original_hours: int,
            hours_remaining: int,
            date_issued: int,
            frozen: bool,
            term: Optional[int] = None,
    ):
        self.project_id = entry_id
        self.user_discord_id = user_discord_id
        self.original_hours = original_hours
        self.hours_remaining = hours_remaining
        self.date_issued = date_issued
        self.frozen = bool(frozen)
        self.term = term

    async def push(self):
        async with aiosqlite.connect(PATH) as db:
            await db.execute(
                """
                UPDATE compulsory_service SET 
                     user_discord_id = ?,
                        original_hours = ?,
                        hours_remaining = ?,
                        date_issued = ?,
                        frozen = ?,
                        term = ?

                WHERE project_id = ?
                """,
                (
                    self.user_discord_id,
                    self.original_hours,
                    self.hours_remaining,
                    self.date_issued,
                    int(self.frozen),
                    self.term,
                    self.project_id,
                ),
            )
            await db.commit()

    async def edit(
            self,
            user_discord_id: Optional[int] = None,
            original_hours: Optional[int] = None,
            hours_remaining: Optional[int] = None,
            date_issued: Optional[int] = None,
            frozen: Optional[bool] = None,
            term: Optional[int] = None,
    ):
        if user_discord_id is not None:
            self.user_discord_id = user_discord_id
        if original_hours is not None:
            self.original_hours = original_hours
        if hours_remaining is not None:
            self.hours_remaining = hours_remaining
        if date_issued is not None:
            self.date_issued = date_issued
        if frozen is not None:
            self.frozen = bool(frozen)
        if term is not None:
            self.term = term
        
        await self.push()

    async def delete(self):

        async with aiosqlite.connect(PATH) as db:
            await db.execute(
                """DELETE FROM structure_payouts_history WHERE project_id = ?""",
                (self.project_id,),
            )
            await db.commit()


async def get_payout_entry(_id: int) -> Optional[PayoutEntry]:
    async with aiosqlite.connect(PATH) as db:
        async with db.execute(
                """SELECT 
                        project_id, user_id, is_payed, from_card, to_card, amount, message
                        FROM structure_payouts_history WHERE project_id = ?
                        """,
                (_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return PayoutEntry(
                entry_id=_id,
                project_id=row[0],
                user_id=row[1],
                is_payed=row[2],
                from_card=row[3],
                to_card=row[4],
                amount=row[5],
                message=row[6],
            )


async def register_payout_entry(
        project_id: int,
        user_id: int,
        is_payed: bool | int,
        from_card: int,
        to_card: int,
        amount: int,
        message: str,
) -> PayoutEntry:
    is_payed = bool(is_payed)
    async with aiosqlite.connect(PATH) as db:
        async with db.execute(
                """INSERT INTO structure_payouts_history (
                        project_id, user_id, is_payed, from_card, to_card, amount, message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (project_id, user_id, int(is_payed), from_card, to_card, amount, message),
        ) as cursor:
            await db.commit()
            return await get_payout_entry(cursor.lastrowid)


async def get_payout_entries(project_id: Optional[int] = None) -> List[PayoutEntry]:
    async with aiosqlite.connect(PATH) as db:
        async with db.execute(
                """SELECT
                        project_id, project_id, user_id, is_payed, from_card, to_card, amount, message
                        FROM structure_payouts_history """
                + ("WHERE project_id = ?" if project_id is not None else ""),
                (project_id,) if project_id is not None else (),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                PayoutEntry(
                    entry_id=row[0],
                    project_id=row[1],
                    user_id=row[2],
                    is_payed=row[3],
                    from_card=row[4],
                    to_card=row[5],
                    amount=row[6],
                    message=row[7],
                )
                for row in rows
            ]
'''
