# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased] - 2026-08-01

### Removed
- Suppression des fichiers de tests inutilisés (`test_cookies.py`, `test_crous.py`, `test_crous2.py`, `test_crous3.py`, `test_env.py`, `fix_sync.py`) et vérification de l'absence de code mort pour assainir le projet.

### Added
- Implémentation du flux d'authentification automatisé complet (contournement du système anti-bot). Le bot résout nativement les défis mathématiques **Altcha** (Preuve de Travail / Proof-of-Work par hash SHA-256) pour récupérer automatiquement les cookies `PHPSESSID` valides à partir des identifiants stockés via la nouvelle commande `/login`, sans aucune intervention manuelle de l'utilisateur.
- Intégration d'un client VPN (WireGuard) directement dans le conteneur Docker via un `entrypoint.sh` spécifique. Le bot est capable de se connecter automatiquement à un nœud de sortie (ex: Freebox) pour router tout son trafic via une IP résidentielle. Ceci résout le problème du blocage par Cloudflare sur les infrastructures serveurs (comme Render).
- Ajout d'une "API Health" (serveur web `aiohttp` sur `/health`) en arrière-plan permettant l'hébergement gratuit sur des plateformes comme Render via le maintien d'activité par UptimeRobot.
- Ajout de la commande `/mes_surveillances` permettant à un utilisateur de lister toutes ses surveillances actives à travers les différents salons.

### Changed
- **Refonte majeure de l'architecture des surveillances** : Le bot associe désormais les villes surveillées à **l'utilisateur** plutôt qu'au salon. Un même utilisateur peut ainsi surveiller plusieurs villes simultanément (cumulables) directement depuis ses Messages Privés.
- La commande `/stop_surveillance` accepte désormais un argument optionnel `ville` pour arrêter une ville précise, ou arrête toutes les villes de l'utilisateur si laissé vide.
- La boucle de surveillance recherche désormais globalement par utilisateur et regroupe l'envoi des notifications.
- Les commandes `/crous` et `/surveiller` sont désormais bloquées si l'utilisateur n'a pas configuré de cookie de session (`PHPSESSID`) valide via `/setcookie`.
- Les résultats de la commande `/crous` sont désormais envoyés directement par message privé, avec une confirmation éphémère dans le salon (repli sur un affichage éphémère si les MP sont bloqués).
- Intégration de l'auto-complétion dynamique des villes CROUS (`villes_crous.json`) via l'endpoint officiel `/api/fr/sectors` sur les commandes slash `/crous` et `/surveiller`.
- Redirection des notifications automatiques de logements vers les messages privés (MP) Discord de l'utilisateur qui a configuré la surveillance, avec basculement automatique sur le salon en cas de MP bloqués.
- Ajout d'une vérification de la validité de la session (`PHPSESSID`) via l'endpoint `/api/fr/user` du CROUS. Si la session expire, le bot supprime l'entrée invalide de `sessions.json` et prévient l'utilisateur concerné par message privé.
- Mise en place d'un environnement virtuel (`.venv`) pour isoler les dépendances du projet.
- Création d'un document d'architecture (`crousbot_architecture.md`) décrivant la structure du projet avec un diagramme Mermaid.
- Ajout de règles de comportement pour l'agent (`.agents/AGENTS.md`) afin de forcer les explications techniques et le maintien de ce `CHANGELOG.md`.
- Ajout du fichier `config_surveillance.json` au `.gitignore`.
- Mise en place d'une pipeline d'Intégration Continue (GitHub Actions) pour vérifier la syntaxe avec `flake8` à chaque commit.
- Ajout d'une règle dans `.agents/AGENTS.md` pour forcer la réponse en français lors des prompts d'erreur générés par l'IDE.
- Création de `Dockerfile` et configuration de `docker-compose.yml` pour conteneuriser l'application.

### Fixed
- Harmonisation de l'idTool de l'API Crous (passage de 47 à 42) dans `utils/crous.py` et `utils/discord_embed.py`.
- Résolution du problème de duplication des commandes slash dans Discord en supprimant la boucle de synchronisation locale (`bot.guilds`) pour ne conserver que la synchronisation globale.
- Formatage du titre des `embeds` Discord pour imiter le site du CROUS : affichage exclusif du nom de la résidence en titre, et déplacement du label technique dans un champ "Type" secondaire.
- Application de la logique "Bounding Box" stricte à la boucle de surveillance 24/7 en arrière-plan (`config_surveillance.json`), qui utilisait auparavant à tort un rayon par défaut.
- Correction du texte des messages Discord pour afficher correctement "(frontières strictes)" au lieu d'un rayon de 25 km, éliminant ainsi la confusion lors des recherches par ville.
- Résolution d'un bug majeur où des erreurs réseau temporaires (429 Too Many Requests, 503, timeouts) déclenchaient à tort la suppression de la session de l'utilisateur et l'envoi répété de messages d'erreur de session expirée. Le bot ignore désormais silencieusement ces erreurs temporaires et retente à la prochaine itération sans perturber la surveillance.

### Changed
- Regroupement des réponses de logements par paquets de 10 `embeds` (limite Discord) dans la commande `/crous` et la boucle de surveillance, optimisant l'envoi de messages et évitant le spam.
- Retrait de l'ensemble des émojis présents dans la base de code (`README.md`, `main.py`, `utils/discord_embed.py`, `utils/storage.py`) pour adopter un style plus formel.
- Suppression de la limite d'affichage des 5 premiers résultats pour la commande `/crous`. Le bot affiche désormais tous les résultats avec une pause de 3 secondes entre chaque message pour éviter le spam.
- Revert de l'idTool CROUS : passage de 42 à 47 selon la préférence de l'utilisateur pour cibler cette campagne spécifique.
- Changement de l'API de géocodage : remplacement de `api-adresse.data.gouv.fr` par `Nominatim (OpenStreetMap)`. Le bot utilise désormais la Bounding Box (frontières administratives exactes) par défaut pour correspondre au comportement strict du site officiel, sauf si un rayon kilométrique est explicitement demandé.
- Ajout du support de la variable d'environnement `CROUS_PHPSESSID` dans `.env` permettant au bot de s'authentifier auprès du CROUS et d'accéder aux logements restreints (comme la campagne 47).
- Refonte complète de l'interface utilisateur Discord : remplacement des anciennes commandes textuelles par les **Slash Commands** (`discord.app_commands`). Les commandes bénéficient désormais de l'auto-complétion native, d'un typage strict des arguments (ville obligatoire, rayon optionnel) et de l'affichage sécurisé (ephemeral) pour la commande `/setcookie`.

- Ajout de la commande `/logout` permettant à l'utilisateur de se déconnecter et de supprimer ses identifiants et sa session de la mémoire du bot.
- Résolution d'un bug majeur où les offres de logement n'étaient envoyées qu'à un seul utilisateur si plusieurs surveillaient la même ville (individualisation du cache des offres).

