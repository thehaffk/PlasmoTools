from __future__ import annotations

import logging
from typing import Optional, List

import aiosqlite

from plasmotools import settings

logger = logging.getLogger(__name__)

PATH = settings.DATABASE_PATH


class PayoutEntry:
    def __init__(
        self,
        entry_id: int,
        project_id: int,
        user_id: int,
        is_payed: bool | int,
        from_card: int,
        to_card: int,
        amount: int,
        message: str,
    ):
        is_payed = bool(is_payed)
        self.id = entry_id
        self.project_id = project_id
        self.user_id = user_id
        self.is_payed = is_payed
        self.from_card = from_card
        self.to_card = to_card
        self.amount = amount
        self.message = message

    async def push(self):
        async with aiosqlite.connect(PATH) as db:
            await db.execute(
                """
                UPDATE structure_payouts_history SET 
                     project_id = ?,
                        user_id = ?,
                        is_payed = ?,
                        from_card = ?,
                        to_card = ?,
                        amount = ?,
                        message = ?
                WHERE project_id = ? 
                """,
                (
                    self.project_id,
                    self.user_id,
                    int(self.is_payed),
                    self.from_card,
                    self.to_card,
                    self.amount,
                    self.message,
                    self.id,
                ),
            )
            await db.commit()

    async def edit(
        self,
        entry_id: Optional[int] = None,
        project_id: Optional[int] = None,
        user_id: Optional[int] = None,
        is_payed: Optional[bool] = None,
        from_card: Optional[int] = None,
        to_card: Optional[int] = None,
        amount: Optional[int] = None,
        message: Optional[str] = None,
    ):
        if entry_id is not None:
            self.id = entry_id
        if project_id is not None:
            self.project_id = project_id
        if user_id is not None:
            self.user_id = user_id
        if is_payed is not None:
            self.is_payed = is_payed
        if from_card is not None:
            self.from_card = from_card
        if to_card is not None:
            self.to_card = to_card
        if amount is not None:
            self.amount = amount
        if message is not None:
            self.message = message

        await self.push()

    async def delete(self):

        async with aiosqlite.connect(PATH) as db:
            await db.execute(
                """DELETE FROM structure_payouts_history WHERE project_id = ?""",
                (self.id,),
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


async def set_saved_card(user_id: int, card_id: Optional[int] = None):
    async with aiosqlite.connect(PATH) as db:
        async with db.execute(
            """ INSERT INTO structure_saved_cards (user_id, card_id) VALUES (?, ?) 
                            ON CONFLICT(user_id) DO UPDATE SET card_id = ? """,
            (user_id, card_id, card_id),
        ) as cursor:
            await db.commit()


async def get_saved_card(user_id: int) -> Optional[int]:
    async with aiosqlite.connect(PATH) as db:
        async with db.execute(
            """SELECT card_id FROM structure_saved_cards WHERE user_id = ?""",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return row[0]
