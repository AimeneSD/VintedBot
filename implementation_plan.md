# Plan d'Implémentation : Intégration IA (Gemini) dans VintedBot

Ce plan décrit l'approche pour intégrer l'analyse LLM sans sacrifier la vitesse de *snipe*, en utilisant l'API Google Gemini (Free Tier).

## Architecture "Post-puis-Edit" (Priorité Vitesse)
Pour garantir que tu sois le premier sur l'annonce, le LLM ne doit **jamais** bloquer l'envoi initial.
1. **Instant Snipe** : Dès qu'une offre est trouvée, le bot l'envoie **immédiatement** sur Discord avec l'embed brut (Prix, Lien, Image) et un statut `⏳ Analyse IA en cours...`
2. **File d'attente (Queue)** : Le message Discord envoyé est poussé dans une file d'attente asynchrone (`asyncio.Queue`).
3. **Analyse Asynchrone** : Une tâche de fond (Worker) dépile les annonces, contacte l'API Gemini avec la description et les photos.
4. **Mise à jour en direct** : Dès la réponse de Gemini, le bot **édite** le message Discord initial pour remplacer le "⏳" par l'audit complet.

## Les Fonctionnalités de l'IA (Le Prompt)
Nous allons concevoir un prompt "Expert Revente/Réparation". Le LLM fera 3 choses :
1. **Traduction Intelligente** : Traduire la description en français propre (bien mieux que Google Trad), en comprenant le jargon technique ("broken screen", "scratches", etc.).
2. **Analyse de Rentabilité / Réparation** : L'IA lira la description (et potentiellement regardera la photo) pour lister les pièces à changer et donner un verdict (ex: 🟢 Fonce, 🟠 Risqué, 🔴 À fuir).
3. **Analyse Vendeur** : Évaluer la note du vendeur (ex: 4.8/5) pour alerter sur d'éventuels scams.

## Gestion des Quotas (Free Tier)
Les limites de l'API gratuite Google (ex: 15 RPM pour Gemini 1.5 Flash) imposent des règles strictes :
1. **Rate Limiter** : Le worker asynchrone espacera les requêtes (ex: 1 requête toutes les 4 secondes) pour ne pas déclencher de `429 Too Many Requests` côté Google.
2. **Gestion des Crashs** : Si Google refuse de répondre, le message Discord sera édité avec `⚠️ L'IA est surchargée, traduction non disponible`.

## Open Questions
> [!IMPORTANT]
> - Préfères-tu utiliser la version texte seule (très rapide) ou donner les **photos** de l'annonce à l'IA pour qu'elle détecte les écrans cassés/rayures (un peu plus lent et consomme plus de tokens) ?
> - Est-ce que tu as déjà généré une **clé API Google AI Studio** ? (Il faudra l'ajouter dans ton fichier `.env`).
> - Tu as mentionné "Gemini 2.5 Flash". Leurs limites gratuites actuelles (Preview) sont parfois hyper strictes (ex: 20 requêtes par jour). Si c'est le cas, on risque d'être bloqués vite. Es-tu d'accord pour qu'on utilise `Gemini 1.5 Flash` (qui autorise 1500 requêtes gratuites par jour) comme valeur par défaut ?

## Proposed Changes
### `utils/gemini_analyzer.py`
- [NEW] Fichier dédié contenant la logique d'appel à `google-generativeai`.
- Gestion du prompt expert et traitement de la réponse.

### `main.py`
- [MODIFY] Création d'une `asyncio.Queue` pour stocker les `(message_discord, item_data)`.
- [MODIFY] Création d'une `@tasks.loop` (Worker IA) qui dépile la Queue, appelle Gemini, et fait un `message.edit(embed=new_embed)`.

### `.env`
- [MODIFY] Ajout de `GEMINI_API_KEY`.
