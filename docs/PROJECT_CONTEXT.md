# Contexte du Projet VintedBot

## Architecture Générale
- **Bot Discord (`main.py`)** : Gère l'interface Discord, la surveillance en temps réel (boucle de sniping via asyncio), et les commandes.
- **Client Vinted (`utils/vinted.py`)** : Gère les requêtes vers l'API Vinted. Implémente le contournement du blocage Cloudflare en téléchargeant le code HTML brut de l'annonce pour y extraire la description avec Regex.
- **Analyse IA (`utils/gemini.py`)** : Utilise Google Gemini (Flash) pour analyser la description et le titre, extraire la rentabilité, estimer les coûts de réparation, et filtrer sémantiquement selon les règles définies dans `critere.md`.
- **Mémoire & Contexte de Marché (`utils/database.py`)** : Base SQLite locale (`market_data.db`). Stocke en continu toutes les annonces Vinted (avec politique de suppression > 3 semaines) et les prix des composants (récupérés automatiquement via Cron Job).

## Ajouts Récents
- **Base de données SQLite** : Pour contrer les hallucinations de l'IA sur les estimations de prix, le bot enregistre l'historique des prix Vinted. L'IA utilise une méthode Just-In-Time (JIT) : lors de l'analyse d'une annonce, si une pièce de rechange est requise et que son prix est inconnu ou date de plus de 14 jours dans la base, l'IA estime elle-même le prix sur le moment et le bot l'enregistre immédiatement dans SQLite. Ces données sont injectées dynamiquement dans le contexte de l'IA lors de l'analyse d'une annonce.
