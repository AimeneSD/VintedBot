import asyncio
from utils.vinted import vinted_client

async def main():
    url = "https://www.vinted.fr/catalog?search_text=nike"
    items = await vinted_client.search(url)
    if items:
        import json
        print(json.dumps(items[0], indent=2))
    await vinted_client.close()

asyncio.run(main())
