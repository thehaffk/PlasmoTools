import asyncio
import logging
from typing import List, Optional, Tuple

import aiohttp
from aiohttp import ClientOSError

from plasmotools import settings
from plasmotools.cogs.error_handler import BankAPIError

logger = logging.getLogger(__name__)


async def transfer(
    from_card_str: str,
    to_card_str: str,
    amount: int,
    token: str,
    message: str = "via PlasmoTools",
) -> Tuple[bool, str]:
    """
    Transfer money from one card to another.
    """
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://plasmorp.com/api/bank/transfer",
            json={
                "from": from_card_str,
                "to": to_card_str,
                "amount": amount,
                "message": message,
            },
            headers={
                "Authorization": f"Bearer {token}",
            },
        ) as resp:
            if resp.status != 200 or not (await resp.json()).get("status", False):
                errors = (await resp.json()).get("error", [])
                if isinstance(errors, dict):
                    errors = [errors]

                return False, ", ".join([error["msg"] for error in errors])
            return True, ""


async def bill(
    from_card_str: str,
    to_card_str: str,
    amount: int,
    token: str,
    message: str = "via PlasmoTools",
):
    # POST plasmorp.com/api/bank/bill
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://plasmorp.com/api/bank/bill",
            json={
                "from": from_card_str,
                "to": to_card_str,
                "amount": amount,
                "message": message,
            },
            headers={
                "Authorization": f"Bearer {token}",
            },
        ) as resp:
            if resp.status != 200 or not (resp_json := await resp.json()).get(
                "status", False
            ):
                errors = (await resp.json()).get("error", [])
                if isinstance(errors, dict):
                    errors = [errors]
                raise BankAPIError(
                    "Unable to make a bill: "
                    + ", ".join([error["msg"] for error in errors])
                )
            return resp_json["data"]


async def wait_for_bill(
    card_str: str, bill_id: int, token: str, time=300
) -> tuple[bool, bool]:
    """
    Wait for bill to be paid.

    Returns: (is_paid, is_declined)
    """

    for _ in range(time // 10):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://plasmorp.com/api/bank/cards/{card_str}/bill/{bill_id}/status",
                headers={
                    "Authorization": f"Bearer {token}",
                    "content-type": "application/json",
                },
            ) as resp:
                if resp.status != 200 or not (resp_json := await resp.json()).get(
                    "status", False
                ):
                    errors = (await resp.json()).get("error", [])
                    if isinstance(errors, dict):
                        errors = [errors]
                    logger.error(
                        "Unable to get bill data: "
                        + ", ".join([error["msg"] for error in errors])
                    )
                    return False, False
                bill_status = resp_json["data"]["status"]
                if bill_status == "PAID":
                    return True, False
                elif bill_status == "DECLINED":
                    return False, True
                elif bill_status == "CANCELLED":
                    return False, False
                await asyncio.sleep(10)
    return False, False


async def cancel_bill(card_str: str, bill_id: int, token: str):
    """
    Cancel bill.
    """
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"https://plasmorp.com/api/bank/cards/{card_str}/bill/{bill_id}/cancel",
            headers={
                "Authorization": f"Bearer {token}",
                "content-type": "application/json",
            },
        ) as resp:
            if resp.status != 200 or not (await resp.json()).get("status", False):
                errors = (await resp.json()).get("error", [])
                if isinstance(errors, dict):
                    errors = [errors]
                logger.error(
                    "Unable to cancel a bill: "
                    + ", ".join([error["msg"] for error in errors])
                )


async def search_cards(token: str, query: str, silent: bool = False) -> list:
    """
    Search cards by query.
    """
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                "https://plasmorp.com/api/bank/search/cards",
                params={"value": str(query)[:16]},
                headers={
                    "Authorization": f"Bearer {token}",
                },
            ) as resp:
                if (
                    resp.status != 200 or not (await resp.json()).get("status", False)
                ) and resp.status != 404:
                    if not silent:
                        logger.warning(
                            "Unable to search cards: %s",
                            await resp.json(),
                        )
                    return []
                return (await resp.json()).get("data", [])
        except ClientOSError:
            logger.warning("Unable to search cards: %s", "ClientOSError")
            return []


async def get_card_data(
    card_str: str, supress_warnings: bool = False
) -> Optional[dict]:
    # https://plasmorp.com/api/bank/cards?ids=??-0000
    async with aiohttp.ClientSession(
        headers={"Authorization": f"Bearer {settings.PT_PLASMO_TOKEN}"}
    ) as session:
        async with session.get(
            "https://plasmorp.com/api/bank/cards",
            params={"ids": card_str},
        ) as resp:
            response_json = {}
            if (
                resp.status != 200
                or not (response_json := await resp.json()).get("status", False)
            ) and resp.status != 404:
                if not supress_warnings:
                    logger.warning(
                        "Unable to get card data: %s",
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
            async with session.get(
                "https://plasmorp.com/api/bank/penalties/helper?",
                params={"tab": tab, "offset": 0, "count": 100},
            ) as resp:
                if resp.status != 200 or not (response_json := await resp.json()).get(
                    "status", False
                ):
                    if resp.status == 403:
                        logger.warning("Unable to get penalties: Permission denied")
                        return []
                    logger.warning(
                        "Unable to get penalties: %s",
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
        logger.warning("Unable to get penalties: %s", "ClientOSError")
        return []


async def cancel_penalty(
    penalty_id: int, token: str = settings.PT_PLASMO_TOKEN
) -> Tuple[bool, str]:
    async with aiohttp.ClientSession(
        headers={"Authorization": f"Bearer {token}"}
    ) as session:
        async with session.delete(
            "https://plasmorp.com/api/bank/penalty",
            json={"penalty": penalty_id},
        ) as resp:
            if resp.status != 200 or not (await resp.json()).get("status", False):
                return False, (await resp.json()).get("error", {}).get("msg", "")
            return True, ""
