import asyncio
from utils.vinted import vinted_client

async def main():
    url = "https://www.vinted.fr/catalog?page=1&time=1786910456&search_by_image_uuid=&search_by_image_id=&search_id=2053708287&order=newest_first&search_text=nike"
    items = await vinted_client.search(url)
    print(f"Found {len(items)} items")
    if items:
        print(f"First: {items[0]['title']} ({items[0]['id']})")
    
    # Run twice to test cache
    await asyncio.sleep(2)
    items2 = await vinted_client.search(url)
    print(f"Found {len(items2)} items on second run")
    if items2:
        print(f"First: {items2[0]['title']} ({items2[0]['id']})")

    await vinted_client.close()

asyncio.run(main())
