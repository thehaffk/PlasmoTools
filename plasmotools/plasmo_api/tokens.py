from typing import List

import aiohttp


async def get_token_scopes(token: str) -> List[str]:
    """
    Request GET plasmorp.com/api/oauth2/token with Authorization: Bearer <token>
    and return the scopes of the token.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://plasmorp.com/api/oauth2/token",
            headers={"Authorization": f"Bearer {token}"},
        ) as resp:
            if resp.status != 200:
                return []
            data = (await resp.json()).get("data", {})
            return data.get("scopes", [])
