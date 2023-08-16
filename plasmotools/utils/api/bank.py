import logging
from typing import List, Optional, Tuple

import aiohttp
from aiohttp import ClientOSError

from plasmotools import settings
from plasmotools.utils import formatters

logger = logging.getLogger(__name__)


async def transfer(
    from_card: int,
    to_card: int,
    amount: int,
    token: str,
    message: str = "via PlasmoTools",
) -> Tuple[bool, str]:
    """
    Transfer money from one card to another.
    """
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://rp.plo.su/api/bank/transfer",
            json={
                "from": formatters.format_bank_card(from_card),
                "to": formatters.format_bank_card(to_card),
                "amount": amount,
                "message": message,
            },
            headers={
                "Authorization": f"Bearer {token}",
                "content-type": "application/json",
            },
        ) as resp:
            if resp.status != 200 or not (await resp.json()).get("status", False):
                errors = [
                    error["msg"] for error in (await resp.json()).get("error", [])
                ]
                return False, ", ".join(errors)
            return True, ""


async def search_cards(token: str, query: str, silent: bool = False) -> list:
    """
    Search cards by query.
    """
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                "https://rp.plo.su/api/bank/search/cards",
                params={"value": str(query)},
                headers={
                    "Authorization": f"Bearer {token}",
                },
            ) as resp:
                if (
                    resp.status != 200 or not (await resp.json()).get("status", False)
                ) and resp.status != 404:
                    if not silent:
                        logger.warning(
                            "Could not search cards: %s",
                            await resp.json(),
                        )
                    return []
                return (await resp.json()).get("data", [])
        except ClientOSError:
            logger.warning("Could not search cards: %s", "ClientOSError")
            return []


async def get_card_data(card_id: int, silent: bool = False) -> Optional[dict]:
    # https://rp.plo.su/api/bank/cards?ids=EB-0000
    async with aiohttp.ClientSession(
        headers={"Authorization": f"Bearer {settings.PT_PLASMO_TOKEN}"}
    ) as session:
        async with session.get(
            "https://rp.plo.su/api/bank/cards",
            params={"ids": formatters.format_bank_card(card_id)},
        ) as resp:
            response_json = {}
            if (
                resp.status != 200
                or not (response_json := await resp.json()).get("status", False)
            ) and resp.status != 404:
                if not silent:
                    logger.warning(
                        "Could not get card data: %s",
                        response_json,
                    )
                return None
            if len(response_json.get("data", [])) == 0:
                return None
            return response_json.get("data", [])[0]


async def get_penalties(tab: str = "active", offset=0) -> List[dict]:
    try:
        async with aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {settings.PT_PLASMO_TOKEN}"}
        ) as session:
            penalties = []
            offset = 0
            async with session.get(
                "https://rp.plo.su/api/bank/penalties/helper?",
                params={"tab": tab, "offset": 0, "count": 100},
            ) as resp:
                response_json = {}
                if resp.status != 200 or not (response_json := await resp.json()).get(
                    "status", False
                ):
                    if resp.status == 403:
                        logger.warning("Could not get penalties: Permission denied")
                        return []
                    logger.warning(
                        "Could not get penalties: %s",
                        await resp.json(),
                    )
                    return []
                penalties += (
                    response_json.get("data", {}).get("all", {}).get("list", [])
                )
            while offset + 100 < response_json.get("data", {}).get("all", {}).get(
                "total", 0
            ):
                penalties += await get_penalties(tab, offset + 100)
            return penalties
    except ClientOSError:
        logger.warning("Could not get penalties: %s", "ClientOSError")
        return []


async def cancel_penalty(
    penalty_id: int, token: str = settings.PT_PLASMO_TOKEN
) -> Tuple[bool, str]:
    async with aiohttp.ClientSession(
        headers={"Authorization": f"Bearer {token}"}
    ) as session:
        async with session.delete(
            "https://rp.plo.su/api/bank/penalty",
            json={"penalty": penalty_id},
        ) as resp:
            if resp.status != 200 or not (await resp.json()).get("status", False):
                return False, (await resp.json()).get("error", {}).get("msg", "")
            return True, ""
