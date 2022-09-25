from __future__ import annotations

import logging

import aiosqlite

from plasmotools import settings

logger = logging.getLogger(__name__)

PATH = settings.DATABASE_PATH

queries = [
    """
create table if not exists table_name
(
    id           integer not null
        constraint table_name_pk
            primary key autoincrement,
    owner_ids    text    not null,
    name         text    not null,
    banker_id    integer not null,
    moderator_id integer,
    is_art       int     default 0,
    decision     integer default 0
);""",
    """
create unique index if not exists table_name_id_uindex
    on table_name (id);
    """,
]


async def setup_database():
    logger.info("Setting up database")
    async with aiosqlite.connect(PATH) as db:
        for query in queries:
            await db.execute(query)
        await db.commit()
