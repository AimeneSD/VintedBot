import asyncio
from utils.vinted import vinted_client
import json

async def main():
    # item_id from earlier logs: 9678005634
    item_id = "9678005634"
    await vinted_client._init_session()
    
    api_url = f"https://www.vinted.fr/api/v2/items/{item_id}"
    async with vinted_client.session.get(api_url, timeout=10) as resp:
        print(resp.status)
        if resp.status == 200:
            data = await resp.json()
            print(list(data.keys()))
            if "item" in data:
                print("Description:", data["item"].get("description"))
                print("Photos count:", len(data["item"].get("photos", [])))
        else:
            print("Failed")
            
    await vinted_client.close()

asyncio.run(main())
