import asyncio
import aiohttp
from aiohttp_socks import ProxyConnector

async def test():
    connector = ProxyConnector.from_url('socks5://127.0.0.1:1080')
    async with aiohttp.ClientSession(connector=connector) as session:
        # Get cookie
        await session.get("https://www.vinted.fr")
        
        # Test 1: with catalog[]
        url1 = "https://www.vinted.fr/api/v2/catalog/items?search_text=new&catalog%5B%5D=3002"
        async with session.get(url1) as resp:
            data = await resp.json()
            items = data.get("items", [])
            print(f"Test catalog[]: found {len(items)} items. First item title: {items[0]['title'] if items else 'None'}")
            
        # Test 2: with catalog_ids
        url2 = "https://www.vinted.fr/api/v2/catalog/items?search_text=new&catalog_ids=3002"
        async with session.get(url2) as resp:
            data = await resp.json()
            items = data.get("items", [])
            print(f"Test catalog_ids: found {len(items)} items. First item title: {items[0]['title'] if items else 'None'}")

asyncio.run(test())
