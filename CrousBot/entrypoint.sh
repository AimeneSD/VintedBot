#!/bin/bash

# Configuration du réseau pour WireGuard
if [ -n "$WG0_CONF_B64" ]; then
    echo "Variable d'environnement WG0_CONF_B64 détectée. Création de /etc/wireguard/wg0.conf..."
    mkdir -p /etc/wireguard
    echo "$WG0_CONF_B64" | base64 -d > /etc/wireguard/wg0.conf
fi

# Vérifier si le fichier de configuration wg0.conf existe
if [ -f "/etc/wireguard/wg0.conf" ]; then
    echo "Fichier wg0.conf détecté. Configuration de Wireproxy..."
    
    # On vérifie si la section [Socks5] existe déjà. Sinon, on l'ajoute.
    if ! grep -q "\[Socks5\]" "/etc/wireguard/wg0.conf"; then
        echo -e "\n[Socks5]\nBindAddress = 127.0.0.1:1080" >> /etc/wireguard/wg0.conf
        echo "Section [Socks5] ajoutée automatiquement."
    fi
    
    # Workaround : Wireproxy crash si /dev/log n'existe pas à cause de landlock
    touch /dev/log
    
    # Lancement de wireproxy en arrière-plan
    wireproxy -c /etc/wireguard/wg0.conf &
    
    echo "✅ Tunnel Wireproxy démarré en arrière-plan (Proxy sur 127.0.0.1:1080) !"
    # On laisse un instant à wireproxy pour se connecter
    sleep 2
else
    echo "⚠️ Aucun fichier /etc/wireguard/wg0.conf trouvé. Démarrage sans VPN..."
fi

# Démarrage du bot Python
echo "Démarrage du bot CrousBot..."
exec python -u main.py
