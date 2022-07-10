import logging

import aiosqlite

# from plasmotools.utils.plasmo_structures.projects import *
# from plasmotools.utils.plasmo_structures.roles import *
import plasmotools.settings as settings
from plasmotools.utils.plasmo_structures.guilds import (
    Guild,
    get_guild,
    register_guild,
    get_all_guilds,
)
from plasmotools.utils.plasmo_structures.payouts import (
    PayoutEntry,
    get_payout_entry,
    get_payout_entries,
    register_payout_entry,
)

PATH = settings.DATABASE_PATH
logger = logging.getLogger(__name__)

queries = [
    """
create table if not exists structure_guilds 
(
    discord_id             integer not null,
    alias                  text    not null,
    player_role_id         integer not null,
    head_role_id           integer not null,
    public_chat_channel_id integer not null,
    logs_channel_id        integer not null
);
""",
    """
    create unique index if not exists structure_guilds_discord_id_uindex
    on structure_guilds (discord_id);
    """,
    """
create table if not exists structure_roles
(
    alias            text    not null
        constraint structure_roles_pk
            primary key,
    name             text    not null,
    guild_discord_id integer not null,
    role_discord_id  integer not null,
    available        integer default 0 not null,
    webhook_url      text
);
""",
    """
create table if not exists structure_projects
(
    id                  integer not null
        constraint structure_projects_pk
            primary key autoincrement,
    name                text    not null,
    is_active           integer default 0 not null,
    guild_discord_id    integer not null,
    from_card           integer,
    plasmo_bearer_token text,
    webhook_url         text    not null
); 
""",
    """

create table if not exists structure_payouts_history
(
    id         integer not null
        constraint structure_payouts_history_pk
            primary key autoincrement,
    project_id integer not null,
    user_id    integer not null,
    is_payed integer default 0 not null,
    from_card  integer not null,
    to_card    integer,
    amount     integer not null,
    message    integer
);
""",
    """

create table if not exists payouts_user_info_dg_tmp
(
    user_id integer not null,
    card_id integer
);""",
]


async def setup_database():
    logger.info("Setting up database")
    async with aiosqlite.connect(PATH) as db:
        for query in queries:
            await db.execute(query)
        await db.commit()
