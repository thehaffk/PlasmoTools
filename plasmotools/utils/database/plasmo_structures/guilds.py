import logging
from typing import Optional

import aiosqlite

from plasmotools import settings

logger = logging.getLogger(__name__)

PATH = settings.DATABASE_PATH


class Guild:
    def __init__(
        self,
        discord_id: int,
        alias: str,
        head_role_id: int,
        player_role_id: int,
        public_chat_channel_id: int,
        logs_channel_id: int,
    ):
        self.id = discord_id
        self.alias = alias
        self.head_role_id = head_role_id
        self.player_role_id = player_role_id
        self.public_chat_channel_id = public_chat_channel_id
        self.logs_channel_id = logs_channel_id

    async def push(self):
        async with aiosqlite.connect(PATH) as db:
            await db.execute(
                """
                INSERT INTO structure_guilds (
                alias, head_role_id, player_role_id, public_chat_channel_id, logs_channel_id, discord_id)
                 VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(discord_id) DO 
                UPDATE SET 
                     alias = ?,
                     head_role_id = ?,
                     player_role_id = ?,
                     public_chat_channel_id = ?,
                     logs_channel_id = ?
                WHERE discord_id = ? 
                """,
                (
                    self.alias,
                    self.head_role_id,
                    self.player_role_id,
                    self.public_chat_channel_id,
                    self.logs_channel_id,
                    self.id,
                )
                * 2,
            )
            await db.commit()

    async def edit(
        self,
        alias: Optional[str] = None,
        head_role_id: Optional[int] = None,
        player_role_id: Optional[int] = None,
        public_chat_channel_id: Optional[int] = None,
        logs_channel_id: Optional[int] = None,
    ):
        if alias is not None:
            self.alias = alias
        if head_role_id is not None:
            self.head_role_id = head_role_id
        if player_role_id is not None:
            self.player_role_id = player_role_id
        if public_chat_channel_id is not None:
            self.public_chat_channel_id = public_chat_channel_id
        if logs_channel_id is not None:
            self.logs_channel_id = logs_channel_id

        await self.push()

    async def delete(self):

        async with aiosqlite.connect(PATH) as db:
            await db.execute(
                """DELETE FROM structure_guilds WHERE discord_id = ?""",
                (self.id,),
            )
            await db.commit()


async def get_guild(discord_id: int) -> Optional[Guild]:
    async with aiosqlite.connect(PATH) as db:
        async with db.execute(
            """SELECT 
                                        discord_id, alias, player_role_id, head_role_id, public_chat_channel_id, logs_channel_id
                                        FROM structure_guilds WHERE discord_id = ?
                                        """,
            (discord_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return Guild(
                discord_id=discord_id,
                alias=row[1],
                player_role_id=row[2],
                head_role_id=row[3],
                public_chat_channel_id=row[4],
                logs_channel_id=row[5],
            )


async def register_guild(
    discord_id: int,
    alias: str,
    player_role_id: int,
    head_role_id: int,
    public_chat_channel_id: int,
    logs_channel_id: int,
) -> Guild:
    guild = Guild(
        discord_id=discord_id,
        alias=alias,
        player_role_id=player_role_id,
        head_role_id=head_role_id,
        public_chat_channel_id=public_chat_channel_id,
        logs_channel_id=logs_channel_id,
    )
    await guild.push()
    return guild


async def get_all_guilds():
    async with aiosqlite.connect(PATH) as db:
        async with db.execute(
            """SELECT 
                                        discord_id
                                        FROM structure_guilds
                                        """,
        ) as cursor:
            rows = await cursor.fetchall()
            return [await get_guild(row[0]) for row in rows]
