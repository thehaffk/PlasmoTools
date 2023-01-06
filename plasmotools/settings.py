"""
Config file for Plasmo Tools
"""

import os
from builtins import bool
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


DEBUG = bool(os.getenv("BOT_DEBUG", 0))
TOKEN = os.getenv("TOKEN")
PT_PLASMO_TOKEN = os.getenv("PLASMO_TOKEN")
DATABASE_PATH = "./data.sqlite"

__version__ = "1.5.8" + ("a" if DEBUG else "")

# todo: update version?


class LogsServer:
    guild_id = 828683007635488809
    invite_url = "https://discord.gg/XYS43z7vj2"

    ban_logs_channel_id = 935571311936278599
    role_logs_channel_id = 935571360393068614
    messages_channel_id = 1008822105200132106
    rrs_logs_channel_id = 1033768782801420340
    leave_logs_channel_id = 1057983888229670922

    roles_notifications_role_id = 1046524223377637416


class Emojis:
    plasmo_sync_logo = "<:PlasmoSync:996079144825794560>"
    plasmo_tools = "<:PlasmoTools:1037338470277988373>"
    enabled = "<:enabled:969672429981016084>"
    disabled = "<:disabled:969672065160474684>"
    diamond = "<:dia:1004883678326956043>"
    loading = "<a:loading:995519205380198400>"
    loading2 = "<a:loading2:995519203140456528>"
    online = "<:online:1006310758415605920>"
    offline = " <:offline:1006310760898629702>"
    site_offline = "<:site_offline:1006321494575550514>"
    site_online = "<:site_online:1006320686693879929>"
    s1mple = "<:S1mple:1048173667781193738>"
    komaru = "<:KOMAP:995730375504568361>"
    diana = "<:DIANA:1053604789147160656>"
    ru_flag = "🇷🇺"


word_emojis = {
    "симпл": Emojis.s1mple,
    "ДИАНА": Emojis.diana,
    "помидоры": Emojis.ru_flag,
}


class DevServer:
    """
    Config for development(logging) server (digital drugs)
    """

    guild_id = 966785796902363188

    bot_logs_channel_id = 980950597203292190
    errors_channel_id = 996245098067144704
    transactions_channel_id = 1005052807302348871
    penalty_logs_channel_id = 1005254395635716217

    support_invite = "https://discord.gg/Xn7Ya9gv5a"


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
    keeper_role_id = 1003276423747874896
    ne_komar_role_id = 956884028533919774
    fusion_role_id = 751722994170331136
    helper_role_id = 1023622804794527805

    monitored_roles = [
        admin_role_id,
        president_role_id,
        mko_head_role_id,
        mko_helper_role_id,
        interpol_role_id,
        banker_role_id,
        keeper_role_id,
        helper_role_id,
    ]

    notifications_channel_id = 754644298720477264
    game_channel_id = 753619083227824319
    anticheat_logs_channel_id = 959332068993679400
    server_logs_channel_id = 1008814971926364300
    logs_channel_id = 959332068993679400

    messages_channel_id = 1049768431009935481


disallowed_to_rrs_roles = [
    PlasmoRPGuild.player_role_id,
    PlasmoRPGuild.helper_role_id,
    PlasmoRPGuild.fusion_role_id,
    PlasmoRPGuild.president_role_id,
    PlasmoRPGuild.admin_role_id,
]

api_roles = {
    "admin": PlasmoRPGuild.admin_role_id,
    "president": PlasmoRPGuild.president_role_id,
    "supa_helper": PlasmoRPGuild.mko_head_role_id,
    "soviet-helper": PlasmoRPGuild.mko_helper_role_id,
    "interpol": PlasmoRPGuild.interpol_role_id,
    "banker": PlasmoRPGuild.banker_role_id,
    "keeper": PlasmoRPGuild.keeper_role_id,
    "player": PlasmoRPGuild.player_role_id,
    "fusion": PlasmoRPGuild.fusion_role_id,
}


class GCAGuild:
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
