"""
Config file for Plasmo Tools
"""

import os
from builtins import bool
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

__version__ = "0.0.5"

DEBUG = bool(os.getenv("BOT_DEBUG", 0))
TOKEN = os.getenv("TOKEN")
ADMIN_PLASMO_TOKEN = os.getenv("PLASMO_TOKEN")


class DBConfig:
    """
    Config for plasmo db (mysql)
    """

    ip = os.getenv("DB_IP")
    port = int(os.getenv("DB_PORT"))
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")


class LogsServer:
    guild_id = 828683007635488809
    invite_url = "https://discord.gg/XYS43z7vj2"

    ban_logs_channel_id = 935571311936278599
    role_logs_channel_id = 935571360393068614
    anticheat_logs_channel_id = 960908663814492180
    death_logs_channel_id = 961632179304165396
    force_warns_logs_channel_id = 961760968315133972
    xray_logs_channel_id = 961694829316833360
    admin_commands_channel_id = 961751903488852068


class DevServer:
    """
    Config for development(logging) server (digital drugs)
    """

    guild_id = 966785796902363188
    invite_url = "https://discord.gg/B6XGDn6x3r"
    bot_logs_channel_id = 980950597203292190


class PlasmoRPGuild:
    """
    Config for Plasmo RP guild
    """

    guild_id = 672312131760291842
    invite_url = "https://discord.gg/Y8AVM3Csjw"

    admin_role_id = 704364763248984145
    president_role_id = 880065048792420403
    mko_head_role_id = 810492714235723777
    mko_helper_role_id = 826366703591620618
    interpol_role_id = 751723033357451335
    banker_role_id = 826367015014498314
    player_role_id = 746628733452025866
    monitored_roles = [
        admin_role_id,
        president_role_id,
        mko_head_role_id,
        mko_helper_role_id,
        interpol_role_id,
        banker_role_id,
    ]

    notifications_channel_id = 754644298720477264
    game_channel_id = 753619083227824319
    anticheat_logs_channel_id = 959332068993679400


class BACGuild:  # TODO: Rename BAC(Big Appeal Court) to GCA(Grand Court of Appeal)
    """
    Config for Grand Court of Appeal discord guild
    """

    guild_id = 855532780187156501
    invite_url = "https://discord.gg/KNaZPxxMHC"

    admin_role_id = 861421925317607425
    banned_role_id = 860799809123778560
    has_pass_role_id = 860799590721388574
    without_pass_role_id = 928688505033474069
    culture_member_role_id = 962479868291977327
    staff_role_id = 928698857666269305
    defendant_role_id = 861958861790511115
    committee_defendant_role_id = 989697153821724732
    juror_role_id = 894213967843581953

    announcements_channel_id = 855532780670418956
    dev_logs_channel_id = 960901660970987590
    mc_logs_channel_id = 963038030195748874


@dataclass()
class PlasmoStructureGuild:
    alias: str
    discord_id: int
    invite_url: str
    player_role_id: int
    structure_head_role_id: int
    public_chat_channel_id: int


structure_guilds = []

court_guild = PlasmoStructureGuild(
    alias="court",
    discord_id=923224449728274492,
    invite_url="https://discord.gg/qySEyGhehx",
    player_role_id=953578699075256361,
    structure_head_role_id=923238538160517141,
    public_chat_channel_id=971004067885236264,
)
structure_guilds.append(court_guild)

interpol_guild = PlasmoStructureGuild(
    alias="interpol",
    discord_id=813451608871796766,
    invite_url="https://discord.gg/asuwsDe6FY",
    player_role_id=878987593482657833,
    structure_head_role_id=813451633085120563,
    public_chat_channel_id=813451608871796770,
)
structure_guilds.append(interpol_guild)

infrastructure_guild = PlasmoStructureGuild(
    alias="infrastructure",
    discord_id=756750263351771146,
    invite_url="https://discord.gg/BGvWMkdTV7",
    player_role_id=810985435903557685,
    structure_head_role_id=810975933888200795,
    public_chat_channel_id=810985283532488714,
)
structure_guilds.append(infrastructure_guild)

economy_guild = PlasmoStructureGuild(
    alias="economy",
    discord_id=866301587525861376,
    invite_url="https://discord.gg/6sKKGPuhRk",
    player_role_id=866308194992128040,
    structure_head_role_id=866586305830715412,
    public_chat_channel_id=866310422066757672,
)
structure_guilds.append(economy_guild)

culture_guild = PlasmoStructureGuild(
    alias="culture",
    discord_id=841392525499826186,
    invite_url="https://discord.gg/vS6hzZzMFw",
    player_role_id=841403623639351316,
    structure_head_role_id=841403071887966230,
    public_chat_channel_id=841395461222432848,
)
structure_guilds.append(culture_guild)
