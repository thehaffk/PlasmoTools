from typing import Tuple

import aiohttp

from plasmotools.utils import formatters


async def transfer(
        from_card: int,
        to_card: int,
        amount: int,
        token: str,
        message: str = "By PlasmoTools",
) -> Tuple[bool, str]:
    """
    Transfer money from one card to another.
    """
    async with aiohttp.ClientSession() as session:
        async with session.post(
                "https://rp.plo.su/api/bank/transfer",
                json={
                    "from_card": formatters.format_bank_card(from_card),
                    "to_card": formatters.format_bank_card(to_card),
                    "amount": amount,
                    "message": message,
                },
                headers={"Authorization": f"Bearer {token}"},
        ) as resp:
            if resp.status != 200 or not (await resp.json()).get("status", False):
                return False, (await resp.json()).get("error", {}).get("msg", "")
            return True, ""


async def search_cards(token: str, query: str) -> list:
    """
    Search cards by query.
    """
    async with aiohttp.ClientSession() as session:
        async with session.post(
                "https://rp.plo.su/api/bank/search/cards",
                params={"value": query},
                headers={"Authorization": f"Bearer {token}"},
        ) as resp:
            if resp.status != 200:
                return []
            return (await resp.json()).get("data", [])
