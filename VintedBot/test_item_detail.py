import asyncio
from utils.vinted import vinted_client
import json
import sys

async def main():
    item_id = "40942377749" # Let's use a real active item id from the previous output: 40942377756? No, the item id was 9678005634 for "Pantalon de jogging Nike". Wait, let me fetch catalog first and get the first item ID.
    
    url = "https://www.vinted.fr/catalog?search_text=nike"
    items = await vinted_client.search(url)
    if not items:
        print("No items found")
        return
        
    item_id = items[0]['id']
    print(f"Fetching {item_id}")
    
    api_url = f"https://www.vinted.fr/api/v2/items/{item_id}"
    try:
        async with vinted_client.session.get(api_url, timeout=10) as resp:
            print(f"Status: {resp.status}")
            data = await resp.json()
            with open("item_detail.json", "w") as f:
                json.dump(data, f, indent=2)
            print("Done")
    except Exception as e:
        print(f"Error: {e}")
            
    await vinted_client.close()

asyncio.run(main())
