import logging

import disnake
from aiohttp import ClientSession
from disnake import Localized

from plasmotools import settings
from plasmotools.utils import formatters

logger = logging.getLogger(__name__)


async def search_bank_cards_autocompleter(
    inter: disnake.ApplicationCommandInteraction, value: str
) -> dict[str, str]:
    """
    Returns a list of the cards for given query
    """
    if len(value) <= 2:
        return [
            Localized(
                "🔎 Request must be longer than 2 characters",
                key="SEARCH_CARDS_AUTOCOMPLETE_MUST_BE_MORE_THAN_2",
            )
        ]

    async with ClientSession(
        headers={"Authorization": f"Bearer {settings.PT_PLASMO_TOKEN}"}
    ) as session:
        async with session.get(
            "https://rp.plo.su/api/bank/search/cards",
            params={"value": value},
        ) as response:
            if (
                response.status == 200
                and (response_json := await response.json())["status"]
            ):
                cards = {
                    (
                        "💳 "
                        + formatters.format_bank_card(card["id"])
                        + " - "
                        + card["holder"]
                        + " - "
                        + card["name"]
                    ): str(card["id"])
                    for card in response_json["data"]
                }
                if len(cards) == 0:
                    cards = [
                        Localized(
                            "🔎 Nothing was found",
                            key="SEARCH_CARDS_AUTOCOMPLETE_NOT_FOUND",
                        )
                    ]
                return cards
            else:
                logger.error(
                    f"Error while searching bank cards: {response.status} {response.reason}"
                )
                return {
                    "🔎 Не удалось получить карты из банка, введите номер карты вручную": "NOTFOUND"
                }
