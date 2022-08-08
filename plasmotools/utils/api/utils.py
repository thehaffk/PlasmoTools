import aiohttp


async def ping_site(site) -> bool:
    # ping site with aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get("https://" + site) as resp:
            return resp.status < 500
