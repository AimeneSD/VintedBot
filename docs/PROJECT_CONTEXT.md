# Architecture du projet VintedBot

## Composants Principaux
- `main.py` : Le coeur du bot Discord. Il gere les commandes Slash (`/vinted_add`, `/vinted_remove`, `/vinted_list`) et contient la boucle de surveillance asynchrone (`vinted_sniper_loop`) qui verifie regulierement l'apparition de nouvelles annonces. Il genere des Embeds Discord riches (jusqu'a 5 images) et traduit le contenu etranger en francais avec `deep-translator`.
- `utils/vinted.py` : Moteur de recherche Vinted. Il recupere un cookie valide en bypassant Cloudflare grace au proxy, interroge l'API de catalogue Vinted et nettoie les URL pour eviter de figer la requete dans le temps. Contient aussi une requete unitaire `get_item` pour recuperer la description complete d'une annonce.
- `data/config_vinted.json` : Base de donnees des URLs surveillees par utilisateur.
- `data/offres_connues.json` : Cache contenant les 100 derniers IDs de chaque recherche pour eviter de notifier des doublons.

## Choix Techniques
- **Bypass Cloudflare** : Vinted bloque les requetes de datacenter. La solution adoptee est un conteneur `wireproxy` (VPN WireGuard -> proxy SOCKS5) couple a un conteneur Python. Tout le trafic du conteneur Python est route vers le proxy.
- **Traduction a la volee** : Utilisation de `deep-translator` dans un Thread asynchrone pour ne pas bloquer l'Event Loop de `discord.py` lors des appels reseau a l'API de traduction.
- **Limites Discord** : Contournement des 100 caracteres max pour les valeurs d'autocompletion (`/vinted_remove`) en utilisant l'index du tableau plutot que l'URL complete. Les Embeds Discord multiples avec la meme URL sont utilises pour afficher une galerie de plusieurs photos Vinted.
