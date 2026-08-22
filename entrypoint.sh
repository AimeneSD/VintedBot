#!/bin/bash
echo "Démarrage du système MegaBot..."

# Workaround : Wireproxy crash si /dev/log n'existe pas à cause de landlock
touch /dev/log

# Gestion du fichier de configuration Wireguard
if [ -n "$WG0_CONF_RAW" ]; then
    echo "Creation de wg0.conf depuis la variable d'environnement WG0_CONF_RAW..."
    echo "$WG0_CONF_RAW" > /app/wg0.conf
elif [ -n "$WG0_CONF_B64" ]; then
    echo "Creation de wg0.conf depuis la variable d'environnement WG0_CONF_B64..."
    echo "$WG0_CONF_B64" | tr -d '\n\r ' | base64 -d > /app/wg0.conf
fi

if [ -s "/app/wg0.conf" ]; then
    # On vérifie si la section [Socks5] existe déjà. Sinon, on l'ajoute.
    if ! grep -q "\[Socks5\]" "/app/wg0.conf"; then
        echo -e "\n[Socks5]\nBindAddress = 127.0.0.1:1080" >> /app/wg0.conf
        echo "Section [Socks5] ajoutée automatiquement."
    fi

    echo "Démarrage de Wireproxy..."
    /usr/local/bin/wireproxy -c /app/wg0.conf &
    # Attendre que le proxy soit prêt
    sleep 3
else
    echo "ATTENTION: wg0.conf introuvable ou vide, le proxy ne sera pas demarré. Vérifiez WG0_CONF_RAW ou WG0_CONF_B64."
fi

echo "Démarrage de VintedBot..."
cd /app/VintedBot && python main.py &
VINTED_PID=$!

echo "Démarrage de CrousBot..."
cd /app/CrousBot && python main.py &
CROUS_PID=$!

# Attendre indéfiniment que les processus se terminent
wait $VINTED_PID $CROUS_PID
