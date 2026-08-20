import asyncio
from utils.vinted import vinted_client
import json
import re

async def main():
    item_id = "9683312809"
    url = f"https://www.vinted.fr/items/{item_id}"
    await vinted_client._init_session()
    
    try:
        async with vinted_client.session.get(url, timeout=10) as resp:
            html = await resp.text()
            # Try to find the JSON in the HTML
            # It's usually inside a <script class="js-react-on-rails-component" data-component-name="ItemApp">
            # or data-component-name="ItemState"
            # Or inside window.__INITIAL_STATE__
            
            # Let's search for "feedback_reputation" in the HTML
            idx = html.find("feedback_reputation")
            if idx != -1:
                print("Found feedback_reputation at", idx)
                # print a snippet around it
                print(html[idx-100:idx+200])
            else:
                print("Not found in HTML")
    except Exception as e:
        print(f"Error: {e}")
            
    await vinted_client.close()

asyncio.run(main())
