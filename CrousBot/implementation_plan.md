# Intégration d'un client VPN (WireGuard) dans le conteneur Docker

L'objectif est de configurer le conteneur Docker du bot pour qu'il se connecte automatiquement au serveur WireGuard de la Freebox avant de lancer le script Python. Ainsi, tout le trafic du bot passera par l'IP résidentielle de la Freebox.

## User Review Required

> [!IMPORTANT]
> **Privilèges Docker** : Cette configuration nécessite d'ajouter les droits administrateur réseau (`NET_ADMIN`) au conteneur. Cela fonctionnera parfaitement en local sur votre machine ou sur un VPS classique. Cependant, si vous déployez ceci sur un service Cloud strict (comme le tier gratuit de Render), il est fort probable que le déploiement échoue car ils interdisent souvent le privilège `NET_ADMIN`.

> [!CAUTION]
> Vous devez générer manuellement un fichier de configuration WireGuard depuis votre interface Freebox avant de lancer le test.

## Open Questions

1. Avez-vous déjà généré un fichier de configuration client WireGuard depuis l'onglet "Utilisateurs" de votre Freebox ? (Il nous faudra ce fichier, que nous nommerons `wg0.conf`, pour que le conteneur puisse se connecter).
2. Souhaitez-vous que l'on procède avec WireGuard (recommandé car plus rapide et moderne) ou préférez-vous OpenVPN ?

## Proposed Changes

---

### Docker 

#### [MODIFY] [Dockerfile](file:///home/aimenedeb/projects/CrousBot/Dockerfile)
- Ajout de l'installation des paquets `wireguard-tools`, `iproute2` et `openresolv`.
- Remplacement de la commande de démarrage directe par un script `entrypoint.sh`.

#### [NEW] [entrypoint.sh](file:///home/aimenedeb/projects/CrousBot/entrypoint.sh)
- Script bash qui exécutera `wg-quick up wg0` pour monter le tunnel VPN, puis lancera `python -u main.py`.

#### [MODIFY] [docker-compose.yml](file:///home/aimenedeb/projects/CrousBot/docker-compose.yml)
- Ajout de `cap_add: - NET_ADMIN` pour autoriser la gestion du réseau.
- Ajout de `sysctls: - net.ipv4.conf.all.src_valid_mark=1` (requis par WireGuard).
- Montage du fichier de configuration VPN (`./wg0.conf:/etc/wireguard/wg0.conf`).

## Verification Plan

### Manual Verification
1. Vous devrez placer votre fichier de configuration de la Freebox dans le dossier sous le nom `wg0.conf`.
2. Nous lancerons `docker compose up --build`.
3. Nous vérifierons les logs du conteneur pour confirmer que l'interface `wg0` s'est bien connectée à la Freebox.
4. Nous pourrons faire un appel test dans le code Python (ex: `requests.get("https://api.ipify.org")`) pour vérifier que l'IP vue par internet est bien celle de votre domicile.
