import aiohttp
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
            self.session = aiohttp.ClientSession(headers=HEADERS)
            
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

        # Extraire les parametres de recherche de l'URL
        parsed_url = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        # Vinted ajoute des parametres "time" et "search_id" qui figent les resultats dans le temps !
        # Il faut imperativement les retirer pour que l'API renvoie des NOUVELLES annonces.
        params_to_remove = ['time', 'search_id', 'page']
        for p in params_to_remove:
            if p in query_params:
                del query_params[p]
                
        # Reconstruire la query string sans les parametres bloquants
        clean_query = urllib.parse.urlencode(query_params, doseq=True)
        
        api_url = f"https://www.vinted.fr/api/v2/catalog/items?{clean_query}"
        
        try:
            async with self.session.get(api_url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("items", [])
                elif resp.status in (401, 403):
                    print(f"[VintedClient] Erreur {resp.status} (Cloudflare / Cookie invalide)")
                    self.cookie_valid = False
                    return []
                else:
                    print(f"[VintedClient] Erreur API {resp.status}")
                    return []
        except Exception as e:
            print(f"[VintedClient] Erreur lors de l'appel API: {e}")
            return []

    async def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Recupere les details complets d'un article, notamment la description et les photos additionnelles."""
        await self._init_session()
        if not self.cookie_valid:
            return None
            
        api_url = f"https://www.vinted.fr/api/v2/items/{item_id}"
        
        try:
            async with self.session.get(api_url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("item")
                else:
                    return None
        except Exception as e:
            print(f"[VintedClient] Erreur get_item: {e}")
            return None

    async def close(self):
        if self.session:
            await self.session.close()

# Instance globale pour une utilisation facile
vinted_client = VintedClient()
