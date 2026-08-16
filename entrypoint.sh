#!/bin/bash

# Configuration du réseau pour WireGuard
if [ -n "$WG0_CONF_B64" ]; then
    echo "Variable d'environnement WG0_CONF_B64 détectée. Création de /etc/wireguard/wg0.conf..."
    mkdir -p /etc/wireguard
    echo "$WG0_CONF_B64" | base64 -d > /etc/wireguard/wg0.conf
fi

# Vérifier si le fichier wg0.conf existe (injecté via volume ou variable)
if [ -f "wg0.conf" ]; then
    mkdir -p /etc/wireguard
    cp wg0.conf /etc/wireguard/wg0.conf
fi

if [ -f "/etc/wireguard/wg0.conf" ]; then
    echo "Fichier wg0.conf détecté. Configuration de Wireproxy..."
    
    if ! grep -q "\[Socks5\]" "/etc/wireguard/wg0.conf"; then
        echo -e "\n[Socks5]\nBindAddress = 127.0.0.1:1080" >> /etc/wireguard/wg0.conf
        echo "Section [Socks5] ajoutée automatiquement."
    fi
    
    touch /dev/log
    wireproxy -c /etc/wireguard/wg0.conf &
    
    echo "✅ Tunnel Wireproxy démarré en arrière-plan (Proxy sur 127.0.0.1:1080) !"
    sleep 2
else
    echo "⚠️ Aucun fichier wg0.conf trouvé. Démarrage sans VPN..."
fi

echo "Démarrage du bot VintedBot..."
exec python -u main.py
