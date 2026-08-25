# VintedBot Context

Ce fichier permet de garder une trace des choix d'architecture et des mécanismes critiques.

## Filtres et Limites de requêtes
- **Tri Vinted (`order=newest_first`)** : Toutes les URL surveillées doivent inclure ce tri pour éviter les vieilles annonces.
- **Cache mémoire (1000 items)** : L'API de Vinted a tendance à mélanger légèrement les annonces sur la première page à cause de problèmes de cohérence (ElasticSearch). Pour éviter que le bot n'oublie une annonce qui recule en page 2 puis revient en page 1, on garde les 1000 derniers ID en mémoire (`cogs/sniper.py`).
- **Timestamp des annonces** : L'API Vinted ne donne pas l'heure de publication exacte sans charger la page web complète. À la place, on utilise le timestamp de la photo principale (`photo.high_resolution.timestamp`), qui correspond à l'heure d'upload de la photo (quelques minutes avant la publication). Les annonces dont la photo a plus de 60 minutes sont ignorées pour éviter d'envoyer des requêtes inutiles à Gemini sur d'anciennes annonces réapparues suite à un bug de Vinted.
