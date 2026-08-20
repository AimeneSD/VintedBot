FROM python:3.13-slim

WORKDIR /app

# Copie des fichiers de dépendances
COPY requirements.txt .

# Installation des dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Installation de curl et tar puis de Wireproxy
RUN apt-get update && \
    apt-get install -y curl tar && \
    curl -L -o wireproxy.tar.gz "https://github.com/octeep/wireproxy/releases/download/v1.0.7/wireproxy_linux_amd64.tar.gz" && \
    tar -xzf wireproxy.tar.gz && \
    mv wireproxy /usr/local/bin/ && \
    chmod +x /usr/local/bin/wireproxy && \
    rm wireproxy.tar.gz && \
    rm -rf /var/lib/apt/lists/*

# Copie du reste du code source
COPY . .

EXPOSE 8080

# On rend le script d'entrée exécutable
RUN chmod +x entrypoint.sh

# Utilisation du script d'entrée pour démarrer le VPN puis le bot
CMD ["./entrypoint.sh"]
