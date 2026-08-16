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
        """Initialise la session et récupère le cookie Vinted si nécessaire."""
        if not self.session:
            # On active le support de proxy si wireproxy est là. On n'utilise pas de proxy dans le code python
            # car wireproxy route tout le trafic de docker, mais au cas où.
            self.session = aiohttp.ClientSession(headers=HEADERS)
            
        if not self.cookie_valid:
            try:
                async with self.session.get("https://www.vinted.fr", timeout=10) as resp:
                    if resp.status == 200:
                        self.cookie_valid = True
                        print("[VintedClient] Cookie récupéré avec succès.")
                    else:
                        print(f"[VintedClient] Échec de la récupération du cookie: {resp.status}")
            except Exception as e:
                print(f"[VintedClient] Erreur de connexion: {e}")

    async def search(self, url: str) -> List[Dict[str, Any]]:
        """
        Prend une URL Vinted classique et interroge l'API pour récupérer les annonces.
        Retourne une liste de dictionnaires représentant les articles.
        """
        await self._init_session()
        if not self.cookie_valid:
            return []

        # Extraire les paramètres de recherche de l'URL
        parsed_url = urllib.parse.urlparse(url)
        query = parsed_url.query
        
        # Si l'url fournie n'a pas de paramètres, on essaie de l'utiliser telle quelle
        if not query:
            # Ex: https://www.vinted.fr/vetements?search_text=nike -> query is empty if no ?
            pass

        api_url = f"https://www.vinted.fr/api/v2/catalog/items?{query}"
        
        try:
            async with self.session.get(api_url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("items", [])
                elif resp.status == 401 or resp.status == 403:
                    print(f"[VintedClient] Erreur {resp.status} (Cloudflare / Cookie invalide)")
                    # Le cookie est peut-être périmé
                    self.cookie_valid = False
                    return []
                else:
                    print(f"[VintedClient] Erreur API {resp.status}")
                    return []
        except Exception as e:
            print(f"[VintedClient] Erreur lors de l'appel API: {e}")
            return []

    async def close(self):
        """Ferme la session proprement."""
        if self.session:
            await self.session.close()

# Instance globale pour une utilisation facile
vinted_client = VintedClient()
