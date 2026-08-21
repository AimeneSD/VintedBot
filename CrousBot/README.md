---
title: CrousBot
emoji: 🎓
colorFrom: blue
colorTo: indigo
sdk: docker
app_file: main.py
pinned: false
---
# CrousBot — Bot Discord de surveillance des logements CROUS 24/7

Un bot Discord automatique et ultra-rapide qui scrute le site du CROUS et vous alerte **dès qu'un logement est disponible**.

---

## Fonctionnalités
- **Surveillance 24/7** : Scanne les offres CROUS en arrière-plan toutes les 30 secondes sans bloquer.
- **Alertes instantanées** : Envoie un message avec embed détaillé (loyer, surface, adresse, lien direct) dans votre salon Discord.
- **Persistance anti-doublon** : Sauvegarde les annonces notifiées pour éviter tout spammage en cas de redémarrage.
- **Commandes Discord faciles** :
  - `/crous <ville>` : Effectue une recherche manuelle instantanée.
  - `/crous <ville> <rayon_en_km>` : Effectue une recherche manuelle instantanée avec un rayon personnalisé.
  - `/surveiller <ville> <rayon_en_km>` : Active la surveillance 24/7 pour une ville dans le salon actuel avec un rayon personnalisé.
  - `/surveiller <ville>` : Active la surveillance 24/7 pour une ville dans le salon actuel.
  - `/stop_surveillance` : Arrête la surveillance dans le salon actuel.


---

## Installation & Lancement

### 1. Installation des dépendances
```bash
pip install -r requirements.txt
```

### 2. Configuration (`.env`)
Créez un fichier `.env` à la racine (ou dupliquez `.env.example`) :
```env
TOKEN_BOT_DISCORD=votre_token_discord_ici
CHECK_INTERVAL=30
```

### 3. Démarrage du bot
```bash
python bot.py
```

---

## Déploiement 24h/24 sans PC allumé

- **Docker** : `docker compose up -d --build`
- **Render / Railway / Koyeb** : Connectez votre dépôt Git, sélectionnez un **Background Worker** avec la commande `python bot.py`.