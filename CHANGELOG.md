# Changelog

## Phase 5 - Alertes Riches & Traductions
- Integration de `deep-translator` pour traduire automatiquement les titres et descriptions des annonces etrangeres en francais.
- Ajout de la methode `get_item` dans le client Vinted pour recuperer la description et les photos additionnelles d'un article.
- Remplacement du message texte brut par une galerie d'Embeds Discord supportant jusqu'a 5 images par article.
- Ajout de champs detailles dans l'Embed : Prix, Taille, Marque, Vendeur.
- Ajout d'un bouton d'interaction Discord (`discord.ui.Button`) pointant vers la page d'achat Vinted.
- Retrait total des caracteres emojis conformement aux regles utilisateurs.

## Patch - Correction de l'Autocompletion Discord
- Correction du bug empechant l'utilisation de `/vinted_remove` avec de longues URLs (limite de 100 caracteres de Discord).
- L'autocompletion affiche desormais un titre raccourci numéroté, et utilise l'index interne comme valeur de selection pour une suppression robuste.

## [Unreleased]
### Added
- Added SQLite database for Vinted history (3 weeks retention) and component prices.
- Added daily cron job (AI scraper) to update AliExpress component prices.
- Injected market context into Gemini prompt for better profit estimations.

## [Unreleased]
### Changed
- Switched AliExpress component price scraping from Daily Cron Job to Single-Call JIT (Just-In-Time) evaluation. Gemini now estimates missing or stale (>14 days) component prices on the fly during the final verdict analysis and automatically persists them into SQLite.

## [Unreleased]
### Added
- Added Keep-Alive web server via aiohttp for Render.com hosting compatibility.
