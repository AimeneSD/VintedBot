import aiohttp
from aiohttp_socks import ProxyConnector
import asyncio
import urllib.parse
from typing import Optional, List, Dict, Any

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
}

class VintedClient:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.cookie_valid = False

    async def _init_session(self):
        if not self.session:
            connector = ProxyConnector.from_url('socks5://127.0.0.1:1080')
            self.session = aiohttp.ClientSession(connector=connector, headers=HEADERS)
            
        if not self.cookie_valid:
            try:
                async with self.session.get("https://www.vinted.fr", timeout=10) as resp:
                    if resp.status == 200:
                        self.cookie_valid = True
                        print("[VintedClient] Cookie recupere avec succes.")
                    else:
                        print(f"[VintedClient] Echec de la recuperation du cookie: {resp.status}")
            except Exception as e:
                print(f"[VintedClient] Erreur de connexion: {e}")

    async def search(self, url: str) -> List[Dict[str, Any]]:
        await self._init_session()
        if not self.cookie_valid:
            return []

        parsed_url = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        params_to_remove = ['time', 'search_id', 'page']
        for p in params_to_remove:
            if p in query_params:
                del query_params[p]
                
        clean_query = urllib.parse.urlencode(query_params, doseq=True)
        api_url = f"https://www.vinted.fr/api/v2/catalog/items?{clean_query}"
        
        try:
            async with self.session.get(api_url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    items = data.get("items", [])
                    # Exclure les annonces boostées / dressing en vitrine
                    return [
                        item for item in items 
                        if not item.get("promoted") and not item.get("is_promoted")
                    ]
                elif resp.status in (401, 403):
                    self.cookie_valid = False
                    return []
                else:
                    return []
        except Exception as e:
            print(f"[VintedClient] Erreur search: {e}")
            return []

    async def get_item_description(self, item_id: str) -> str:
        """Recupere la description depuis le HTML de la page web"""
        await self._init_session()
        if not self.cookie_valid:
            return ""
            
        url = f"https://www.vinted.fr/items/{item_id}"
        try:
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    import re
                    import json
                    match = re.search(r'"description":"(.*?)"', html)
                    if match:
                        try:
                            # unescape json
                            desc = json.loads('"' + match.group(1) + '"')
                            return desc
                        except:
                            return match.group(1)
        except Exception as e:
            print(f"[VintedClient] Erreur description {item_id}: {e}")
        return ""

    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Recupere les infos du vendeur (note, avis)"""
        await self._init_session()
        if not self.cookie_valid:
            return {}
            
        api_url = f"https://www.vinted.fr/api/v2/users/{user_id}"
        try:
            async with self.session.get(api_url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("user", {})
        except Exception as e:
            pass
        return {}

    async def close(self):
        if self.session:
            await self.session.close()

    async def download_image(self, url: str) -> bytes:
        """Télécharge une image en RAM"""
        await self._init_session()
        if not self.cookie_valid:
            return b""
            
        try:
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.read()
        except Exception as e:
            print(f"[VintedClient] Erreur telechargement image: {e}")
        return b""

vinted_client = VintedClient()
