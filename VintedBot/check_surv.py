import asyncio
from utils.database import load_config
import json

async def main():
    config = await load_config()
    print(json.dumps(config, indent=2))

asyncio.run(main())
