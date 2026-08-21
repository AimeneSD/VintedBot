# Contexte du Projet : CrousBot

Ce document sert de mémoire continue à l'agent. Il décrit l'architecture du projet et le rôle de chaque fichier, afin de recharger le contexte efficacement lors d'une nouvelle conversation.

## Architecture et Rôles des Fichiers

- **`main.py`** : Point d'entrée principal du bot Discord. Gère l'initialisation (`bot.run()`), les commandes interactives (`/crous`, `/surveiller`, `/stop_surveillance`), et intègre la boucle asynchrone (`@tasks.loop`) qui vérifie les offres 24/7 en arrière-plan.
- **`utils/crous.py`** : Moteur de recherche et logique métier. S'occupe d'obtenir les coordonnées géographiques ou la "Bounding Box" d'une ville (via Nominatim/OSM) et de chercher les logements CROUS disponibles (soit de manière stricte dans la boîte, soit par algorithme de rayon kilométrique).
- **`utils/discord_embed.py`** : Moteur de rendu. Transforme les données brutes des logements (issues de `crous.py`) en messages Discord formatés (Embeds), prêts à être envoyés sur les salons. Le format reproduit fidèlement la mise en page du site officiel du CROUS.
- **`utils/storage.py`** : Gestionnaire de persistance locale. S'occupe de lire et d'écrire des fichiers JSON pour sauvegarder l'état du bot entre deux redémarrages.
- **`utils/keep_alive.py`** : Micro-serveur web (`aiohttp`) exposant une route HTTP `/health`. Indispensable pour garder le bot éveillé sur des hébergements gratuits (comme Render) via un service de ping tel que UptimeRobot.
- **`offres_connues.json`** : Fichier de cache persistant. Contient la liste des ID des offres déjà notifiées, pour éviter de spammer le canal à chaque boucle.
- **`config_surveillance.json`** : Fichier de configuration persistant. Mémorise les salons où la surveillance automatique est activée, avec la ville, les coordonnées, et l'ID de l'utilisateur l'ayant activée.
- **`sessions.json`** : Fichier persistant stockant les cookies `PHPSESSID` (authentification CROUS) associés à chaque utilisateur Discord (via leur `author_id`). Les sessions expirées sont détectées et supprimées automatiquement, tout en prévenant l'utilisateur en MP.
- **`credentials.json`** : Fichier stockant les identifiants CROUS (email et mot de passe) associés à chaque utilisateur Discord, obtenus via la commande `/login`. Ce fichier permet le renouvellement automatique de la session sans que l'utilisateur n'ait besoin de relancer la commande manuellement.
- **`villes_crous.json`** : Fichier de référence contenant la liste complète des 164 villes/secteurs issus de l'API officielle du CROUS pour l'auto-complétion dynamique des commandes.
- **`.env` / `.env.example`** : Gestion des secrets (Token du bot Discord) et de la configuration de l'intervalle de vérification.

## Décisions Techniques

- **Slash Commands** : Le projet utilise `discord.app_commands` pour gérer les commandes interactives (`/crous`, `/surveiller`, `/stop_surveillance`, `/setcookie`). Cela permet l'auto-complétion native et le typage strict des arguments. La synchronisation est gérée uniquement de manière globale pour éviter les doublons sur les serveurs Discord.
- **Boucle Asynchrone** : Le projet repose sur `discord.ext.tasks` pour la vérification périodique, garantissant que le bot reste réactif aux commandes manuelles pendant les vérifications.
- **Persistance Légère** : Utilisation de JSON via `storage.py` au lieu d'une base de données complexe (SQL/NoSQL) car l'état à conserver (salons surveillés et IDs des offres déjà vues) est minimal.
- **Séparation des Préoccupations (MVC-like)** : La logique de scraping/API (Modèle - `crous.py`), la logique Discord (Contrôleur - `main.py`) et l'affichage (Vue - `discord_embed.py`) sont proprement séparés dans le dossier `utils/`.
- **Stratégie de Géocodage Hybride** : Pour simuler le comportement du site officiel, le bot privilégie la "Bounding Box" (frontières administratives exactes via Nominatim) lorsqu'aucun rayon n'est spécifié, et bascule sur un calcul mathématique de périmètre (Cercle autour d'un point central GPS) quand l'utilisateur demande explicitement un rayon (`rayon_km`).
- **Authentification Automatisée Individuelle** : Pour éviter à l'utilisateur de fournir manuellement son cookie `PHPSESSID`, le bot implémente le flux complet d'authentification OAuth2/CAS du CROUS. La sécurité anti-bot **Altcha** (basée sur une Preuve de Travail / Proof-of-Work) est résolue nativement en Python via une boucle de hachage SHA-256 (bruteforce du sel). L'utilisateur fournit ses accès via la commande `/login` stockée dans `credentials.json`, ce qui permet d'isoler les recherches pour chaque étudiant.
- **Optimisation des flux Discord (Chunking)** : Pour éviter le spam et le dépassement de limite de l'API (Rate Limit), l'affichage de multiples logements via `main.py` est géré par paquets de 10 `embeds` simultanés par message (limite maximale autorisée par Discord), plutôt que d'envoyer un message par logement.

## Conteneurisation (Docker)

L'application est configurée pour tourner dans un environnement isolé via Docker :
- **`Dockerfile`** : Construit une image basée sur `python:3.13-slim`. Il copie le code source, installe les dépendances via `requirements.txt` ainsi que les outils réseaux (`wireguard-tools`, `iproute2`, `iptables`). Le point d'entrée est délégué au script `entrypoint.sh`.
- **`entrypoint.sh`** : Script d'amorçage bash. Son rôle est de lire une configuration VPN optionnelle (`wg0.conf`), d'établir un tunnel réseau chiffré (WireGuard) via `wg-quick` en contournant les restrictions de privilèges de sysctl, puis de lancer le bot Python.
- **`docker-compose.yml`** : Orchestre le conteneur. Il s'occupe de monter les fichiers JSON en tant que volumes pour que les données survivent aux redémarrages, ainsi que le fichier de configuration VPN. Il ajoute les privilèges systèmes obligatoires (`cap_add: NET_ADMIN`) et injecte le Token Discord via le fichier `.env`.
## Commandes utilisateur
- `/login` : Enregistre les identifiants en toute sécurité.
- `/logout` : Supprime les identifiants et le cookie de session de la mémoire.

- **Programmation Asynchrone (asyncio)** : Les requêtes HTTP (via `requests`) et le calcul intensif (Altcha PoW) sont encapsulés dans des threads séparés via `asyncio.to_thread` afin de ne jamais bloquer la boucle d'événements de discord.py. Cela garantit que les commandes Slash et les requêtes d'auto-complétion répondent en moins de 3 secondes.
- **Différé (Defer)** : Toutes les commandes réseau-dépendantes (`/crous`, `/surveiller`, `/login`) utilisent systématiquement `await interaction.response.defer()` dès la première ligne pour éviter l'erreur de Timeout Discord (404 Unknown interaction).
- **Géocodage Nominatim** : Amélioration de la recherche de coordonnées en supprimant les suffixes spécifiques au Crous (ex: *Centre - Ouest*, *Sud-Est*) qui faussaient l'API OpenStreetMap (Nominatim).
- **Envoi immédiat (UX)** : Lors de l'ajout d'une surveillance (`/surveiller`), le bot fait désormais une requête synchrone en arrière-plan pour envoyer *immédiatement* les offres déjà disponibles, même si l'utilisateur les avait déjà reçues dans le passé. Cela permet de toujours avoir un point d'étape.
- **Autocomplétion (UX)** : La recherche de ville dans `/surveiller` est désormais insensible à la casse et **aux accents** (ex: *orleans* trouve *Orléans*). Ajout d'un alias intelligent pour que la recherche *Nice* propose *Agglomération Niçoise*.
- **Nettoyage des Noms de Villes** : Suppression des suffixes complexes dans `villes_crous.json` (ex: *Agglomération Niçoise* devient *Nice*, *Paris intra-muros* devient *Paris*) pour une interface utilisateur beaucoup plus propre.

## Gestion des sessions et résilience réseau
Le bot maintient l'état des sessions de manière intelligente :
- **Expiration réelle vs Erreur Réseau** : L'endpoint `/api/fr/user` du CROUS est utilisé pour vérifier la session. S'il renvoie `200 OK` avec un body `null`, ou une erreur d'autorisation (401, 403), la session est considérée comme réellement expirée, ce qui déclenche le renouvellement automatique (Altcha + OAuth2). En revanche, s'il renvoie un code de type "Too Many Requests" (429) ou "Service Unavailable" (503) dû à un blocage temporaire (ban IP Cloudflare passager ou surcharge CROUS), le bot l'identifie comme une **Erreur réseau temporaire**. Il ignore silencieusement la boucle de vérification sans supprimer la session, évitant ainsi le spam de messages d'erreur "Session Expirée" en MP à l'utilisateur, jusqu'à ce que la connexion soit rétablie à l'itération suivante.
