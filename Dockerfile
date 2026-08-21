FROM python:3.10-slim

# Install wget for Wireproxy
RUN apt-get update && apt-get install -y wget && rm -rf /var/lib/apt/lists/*

# Install Wireproxy
RUN wget https://github.com/octeep/wireproxy/releases/download/v1.0.8/wireproxy_linux_amd64.tar.gz && \
    tar -xzf wireproxy_linux_amd64.tar.gz && \
    mv wireproxy /usr/local/bin/ && \
    chmod +x /usr/local/bin/wireproxy && \
    rm wireproxy_linux_amd64.tar.gz

WORKDIR /app

# Install all dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy both bots
COPY VintedBot /app/VintedBot
COPY CrousBot /app/CrousBot

# Copy root entrypoint and config
COPY entrypoint.sh /app/
COPY wg0.conf /app/

RUN chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
