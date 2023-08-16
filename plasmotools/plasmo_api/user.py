import logging
from typing import Optional

import aiohttp
from aiohttp import ClientOSError

logger = logging.getLogger(__name__)


async def get_user_data(
    nick: str = None,
    discord_id: int = None,
    plasmo_id: int = None,
    fields: tuple[str] = ("stats", "warns", "teams"),
) -> Optional[dict]:
    """
    Get user data by nick, discord_id or plasmo_id.
    """
    if nick is None and discord_id is None and plasmo_id is None:
        return None

    params = {}
    if nick is not None:
        params["nick"] = nick
    if discord_id is not None:
        params["discord_id"] = discord_id
    if plasmo_id is not None:
        params["plasmo_id"] = plasmo_id
    params["fields"] = ",".join(fields)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://plasmorp.com/api/user/profile", params=params
            ) as resp:
                if resp.status != 200 or not (response_json := await resp.json()).get(
                    "status", False
                ):
                    return None
                return response_json.get("data", {})
    except ClientOSError:
        return None
