import logging

import disnake
from aiohttp import ClientSession
from disnake import Localized

from plasmotools import settings
from plasmotools.utils import formatters

logger = logging.getLogger(__name__)


async def search_bank_cards_autocompleter(
    inter: disnake.ApplicationCommandInteraction, value: str
):
    """
    Returns a list of the cards for given query
    """
    if len(value) == 0:
        value = inter.author.display_name or inter.author.name
    elif len(value) <= 2:
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
                response_cards = response_json["data"][:25]
                cards = {
                    (
                        "💳 "
                        + formatters.format_bank_card(
                            card["id"], bank_prefix=card["bank_code"]
                        )
                        + " - "
                        + card["holder"]
                        + " - "
                        + card["name"]
                    ): formatters.format_bank_card(
                        card["id"], bank_prefix=card["bank_code"]
                    )
                    for card in response_cards
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
                return [
                    Localized(
                        "🔎 Nothing was found",
                        key="SEARCH_CARDS_AUTOCOMPLETE_NOT_FOUND",
                    )
                ]
