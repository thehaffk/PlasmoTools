import logging
from typing import Optional

import aiohttp

from plasmotools import plasmo_api, settings

logger = logging.getLogger(__name__)


async def _get_chat_info(nickname: str) -> Optional[dict]:
    # /api/mesenger/chats/user/{nickname}
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://plasmorp.com/api/messenger/chats/user/{nickname}",
            cookies={
                "rp_token": settings.PT_PLASMO_COOKIES,
            },
        ) as resp:
            if resp.status != 200 or not (await resp.json()).get("status", False):
                logger.warning(
                    "Unable to get chat_id: %s",
                    (await resp.json()).get("error", {}).get("msg", ""),
                )
                return None
            return (await resp.json()).get("data", {})


async def send_mc_message(
    message: str,
    discord_id: Optional[int] = None,
    nickname: Optional[str] = None,
    plasmo_id: Optional[int] = None,
    even_if_offline: bool = False,
) -> bool:
    if len(message) > 255:
        raise ValueError("message must be less than 256 symbols")

    user_data = await plasmo_api.user.get_user_data(
        discord_id=discord_id, plasmo_id=plasmo_id, nick=nickname
    )
    if user_data is None:
        logger.warning(
            "Unable to get user data for did: %s pid: %s nick %s",
            discord_id,
            plasmo_id,
            nickname,
        )
        return False
    nickname = user_data.get("nick", None)
    if nickname is None:
        logger.warning(
            "Unable to get nickname for did: %s pid: %s", discord_id, plasmo_id
        )
        return False

    chat_data = await _get_chat_info(nickname=nickname)
    if chat_data is None:
        logger.warning("Unable to get chat data for %s", nickname)
        return False
    chat_id = chat_data["id"]

    player_is_online = user_data["stats"]["on_server"] == "sur"

    if not player_is_online and not even_if_offline:
        # logger.debug("Unable to send message bc user is offline: %s", nickname)
        return False

    logger.info("PlasmoTools -> %s: %s", nickname, message)
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://plasmorp.com/api/messenger/send",
            json={
                "chat_id": chat_id,
                "content": message,
            },
            cookies={
                "rp_token": settings.PT_PLASMO_COOKIES,
            },
        ) as resp:
            if resp.status != 200 or not (await resp.json()).get("status", False):
                logger.warning(
                    "Unable to send plasmo message to %s, error: %s",
                    nickname,
                    (await resp.json()).get("error", {}).get("msg", ""),
                )
                return False
            return True
