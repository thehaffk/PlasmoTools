import logging
import os
from builtins import bool
from dataclasses import dataclass

import dotenv

logger = logging.getLogger(__name__)

dotenv.load_dotenv()
DEBUG = bool(int(os.getenv("BOT_DEBUG", "0")))
TOKEN = os.getenv("TOKEN", None)
PT_PLASMO_TOKEN = os.getenv("PLASMO_TOKEN", None)
if PT_PLASMO_TOKEN is None:
    logger.critical("PLASMO_TOKEN is missing")
PT_PLASMO_COOKIES = os.getenv("PLASMO_COOKIE", None)
if PT_PLASMO_COOKIES is None:
    logger.critical("PLASMO_COOKIE is missing")
__version__ = "1.6.1" + ("-alpha" if DEBUG else "")
DATABASE_PATH = "plasmotools.sqlite"
HELP_URL = "https://digitaldrugs.notion.site/Plasmo-Tools-ultimate-guide-a5874f7c3a56433ea2c3816527740fa0Л"
oauth2_url_for_projects = (
    "https://plasmorp.com/oauth2?client_id=FHHGpr8ZbZb35ZFvwSgD9EMbvkQF35ZFvwSgD9EMbvkQGpr8"
    "&redirect_uri=https://pt.haffk.tech/oauth/&response_type=token"
    "&scope=bank:manage%20bank:history%20bank:search%20user:notifications%20bank:penalties"
)
blocked_users_ids = [
    744193929746055168,  # TheMeko
]
owner_ids = [
    737501414141591594,  # thehaffk
    222718720127139840,  # Apehum
    191836876980748298,  # KPidS
    1017063823548616785,  # haffk alt
]

INTERPOL_UNMANAGED_PENALTIES_CHANNEL_ID = 1136128085540999188
ECONOMY_ARTODEL_LICENSE_ROLE_ID = 1003248014049165362
ECONOMY_DD_OPERATIONS_CHANNEL_ID = 1137250011416121475
ECONOMY_PATENTS_PUBLIC_CHANNEL_ID = 1122900180463784106
ECONOMY_PATENTS_MODERATOR_CHANNEL_ID = 1137536310412853380
ECONOMY_PATENTS_MODERATOR_ROLE_ID = 1139445058739912736
DD_BANK_PATENTS_CARD = "DD-0004"
ECONOMY_PATENTS_TREASURY_CARD = "EB-1530" if DEBUG else "EB-0017"
ECONOMY_MAIN_TREASURY_CARD = "EB-0014"
ECONOMY_FAILED_PAYMENTS_ROLE_ID = 1140383608062885928
ECONOMY_PATENTS_NUMBERS_CHANNEL_ID = 1122900705280266291


class LogsServer:
    guild_id = 828683007635488809
    invite_url = "https://discord.gg/XYS43z7vj2"

    ban_logs_channel_id = 935571311936278599
    role_logs_channel_id = 935571360393068614
    messages_channel_id = 1008822105200132106
    rrs_logs_channel_id = 1033768782801420340
    rrs_verification_channel_id = 1060912903257079878
    leave_logs_channel_id = 1057983888229670922
    moderators_channel_id = 1073654991417507931
    daily_check_channel_id = 1118522037565141002

    roles_notifications_role_id = 1046524223377637416
    errors_notifications_role_id = 876056190726045716
    moderator_role_id = 875736652977418292

    rrs_verifications_notifications_role_id = 843154786726445105
    rrs_alerts_role_id = 1120748226119729267

    pride_month_event_id = 1103678285570904204


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


class Gifs:
    v_durku = (
        "https://tenor.com/view/%D0%B2%D0%B4%D1%83%D1%80%D0%BA%D1%83-"
        "%D0%B4%D1%83%D1%80%D0%BA%D0%B0-%D0%BA%D0%BE%D1%82-"
        "%D0%BA%D0%BE%D1%82%D1%8D-gif-25825159"
    )
    amazed = "https://imgur.com/5pdZQMi"
    est_slova = "https://tenor.com/view/est_slova_i_emozii_tozhe-gif-25247683"
    dont_ping_me = "https://tenor.com/view/discord-komaru-gif-26032653"


word_emojis = {
    "симпл": Emojis.s1mple,
    "ДИАНА": Emojis.diana,
    "помидоры": Emojis.ru_flag,
    "комар": Emojis.komaru,
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
    new_player_role_id = 1122893850692829184
    keeper_role_id = 1003276423747874896
    ne_komar_role_id = 956884028533919774
    fusion_role_id = 751722994170331136
    helper_role_id = 1023622804794527805
    moderator_role_id = 813670327376805889

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
    moderators_channel_id = 860449950726881341

    messages_channel_id = 1049768431009935481


disallowed_to_rrs_roles = [
    PlasmoRPGuild.player_role_id,
    PlasmoRPGuild.new_player_role_id,
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
    "new_player": PlasmoRPGuild.new_player_role_id,
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
    name: str
    discord_id: int
    invite_url: str
    player_role_id: int
    structure_head_role_id: int
    public_chat_channel_id: int
    pt_logs_channel_id: int
    original_avatar_url: str


structure_guilds = []

interpol_guild = PlasmoStructureGuild(
    alias="interpol",
    name="Интерпол",
    discord_id=813451608871796766,
    invite_url="https://discord.gg/asuwsDe6FY",
    player_role_id=878987593482657833,
    structure_head_role_id=813451633085120563,
    public_chat_channel_id=813451608871796770,
    pt_logs_channel_id=957050026100666428,
    original_avatar_url="https://i.imgur.com/lpUKyvx.png",
)
structure_guilds.append(interpol_guild)

economy_guild = PlasmoStructureGuild(
    alias="economy",
    name="Экономика",
    discord_id=866301587525861376,
    invite_url="https://discord.gg/6sKKGPuhRk",
    player_role_id=866308194992128040,
    structure_head_role_id=866586305830715412,
    public_chat_channel_id=866310422066757672,
    pt_logs_channel_id=996269148738945064,
    original_avatar_url="https://i.imgur.com/uFDbkB4.png",
)
structure_guilds.append(economy_guild)

infrastructure_guild = PlasmoStructureGuild(
    alias="infrastructure",
    name="Инфраструктура",
    discord_id=756750263351771146,
    invite_url="https://discord.gg/BGvWMkdTV7",
    player_role_id=810985435903557685,
    structure_head_role_id=810975933888200795,
    public_chat_channel_id=810985283532488714,
    pt_logs_channel_id=996263550324588644,
    original_avatar_url="https://i.imgur.com/p1xzKXD.png",
)
structure_guilds.append(infrastructure_guild)

court_guild = PlasmoStructureGuild(
    alias="court",
    name="Суд",
    discord_id=923224449728274492,
    invite_url="https://discord.gg/qySEyGhehx",
    player_role_id=953578699075256361,
    structure_head_role_id=923238538160517141,
    public_chat_channel_id=971004067885236264,
    pt_logs_channel_id=996268192349569066,
    original_avatar_url="https://i.imgur.com/nsB3iXj.png",
)
structure_guilds.append(court_guild)

culture_guild = PlasmoStructureGuild(
    alias="culture",
    name="Культура",
    discord_id=841392525499826186,
    invite_url="https://discord.gg/vS6hzZzMFw",
    player_role_id=841403623639351316,
    structure_head_role_id=841403071887966230,
    public_chat_channel_id=841395461222432848,
    pt_logs_channel_id=922174128675504148,  # чердак
    original_avatar_url="https://i.imgur.com/Rivylr8.png",
)
structure_guilds.append(culture_guild)

mko_guild = PlasmoStructureGuild(
    alias="mko",
    name="МКО",
    discord_id=814490777526075433,
    invite_url="https://discord.gg/yTzj56CXpp",
    player_role_id=874736916686319718,
    structure_head_role_id=1046142021343137802,
    public_chat_channel_id=874736383279919144,
    pt_logs_channel_id=1005216573419696218,
    original_avatar_url="https://i.imgur.com/Mssu73W.png",
)
structure_guilds.append(mko_guild)

gca_guild = PlasmoStructureGuild(
    alias="gca",
    name="Большой Апелляционный Суд",
    discord_id=855532780187156501,
    invite_url="https://discord.gg/6A9AtFKz8b",
    player_role_id=860799590721388574,
    structure_head_role_id=928698857666269305,
    public_chat_channel_id=860511686490325042,
    pt_logs_channel_id=960901660970987590,
    original_avatar_url="https://i.imgur.com/N66WYog.png",
)
structure_guilds.append(gca_guild)
