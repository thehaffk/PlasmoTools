import aiohttp


async def ping_site(site) -> bool:
    # ping site with aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get("https://" + site) as resp:
            return resp.status < 500


async def get_pay2_stats() -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get("https://pay2.plo.su/app/stats?app=mc_rp") as resp:
            return (await resp.content.read()).decode("utf-8")
