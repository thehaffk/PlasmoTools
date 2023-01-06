import logging
import time
from typing import List

import aiohttp
from aiohttp import ClientOSError

from plasmotools import settings

logger = logging.getLogger(__name__)


async def get_banker_transactions(days: int):
    logger.debug("Running get_banker_transactions")
    return await _get_banker_transactions(days)


async def _get_banker_transactions(days, to: int = 0) -> List[dict]:
    logger.debug("Running _get_banker_transactions with days=%i, to=%i", days, to)
    try:
        async with aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {settings.PT_PLASMO_TOKEN}"}
        ) as session:
            transactions = []
            async with session.get(
                "https://rp.plo.su/api/bank/banker/transactions",
                params={"to": to, "count": 100},
            ) as resp:
                response_json = {}
                if resp.status != 200 or not (response_json := await resp.json()).get(
                    "status", False
                ):
                    logger.warning(
                        "Could not get transactions: %s",
                        response_json.get("error", {}).get("msg", ""),
                    )
                    return []
                unfiltred_transactions = response_json.get("data", {}).get("list", [])
                if len(unfiltred_transactions) == 0:
                    return []
                for transaction in unfiltred_transactions:
                    if transaction.get("date", 0) < (time.time() - days * 60 * 60 * 24):
                        return transactions
                    transactions.append(transaction)

                if to == 0:
                    return transactions + await _get_banker_transactions(
                        days, to=(response_json.get("data", {}).get("total")) - 100
                    )
                elif to <= 100:
                    return transactions
                else:
                    return transactions + await _get_banker_transactions(
                        days, to=to - 100
                    )

    except ClientOSError:
        logger.warning("Could not get transactions: %s", "ClientOSError")
        return []
