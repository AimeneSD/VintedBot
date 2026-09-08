import asyncio
from utils.database import load_known_items
import json

async def main():
    cache = await load_known_items()
    found = False
    for url, ids in cache.items():
        if 9828213943 in ids or "9828213943" in ids:
            print(f"FOUND IN CACHE FOR URL: {url}")
            found = True
    if not found:
        print("NOT FOUND IN CACHE")

asyncio.run(main())
