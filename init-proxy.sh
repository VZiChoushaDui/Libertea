#!/bin/bash

set -e

# if not elevated, elevate
if [ "$EUID" -ne 0 ]; then
    sudo "$0" "$@"
    exit
fi

CONN_PROXY_IP="$1"
PANEL_SECRET_KEY="$2"
PROXY_REGISTER_ENDPOINT="$3"

if [ -z "$CONN_PROXY_IP" ] || [ -z "$PANEL_SECRET_KEY" ] || [ -z "$PROXY_REGISTER_ENDPOINT" ]; then
    echo "Usage: $0 <CONN_PROXY_IP> <PANEL_SECRET_KEY> <PROXY_REGISTER_ENDPOINT>"
    exit 1
fi

DIR="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
cd "$DIR"

# if .libertea.main file exists, then this is a main server. don't install proxy
if [ -f .libertea.main ]; then
    echo "This is a main Libertea server. You need to install Libertea secondary proxy on a different server."
    exit 1
fi

touch .libertea.proxy

echo " ** Initializing firewall..."
ufw allow ssh >/dev/null
ufw allow http >/dev/null
ufw allow https >/dev/null
yes | ufw enable >/dev/null

echo " ** Installing docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sh /tmp/get-docker.sh >/dev/null
fi
echo " ** Installing docker compose..."
apt-get install docker-compose-plugin >/dev/null

echo " ** Creating .env file..."
if [ -f .env ]; then
    rm -f .env.bak
    mv .env .env.bak
fi
echo "CONN_PROXY_IP=$CONN_PROXY_IP" >> .env
echo "PANEL_SECRET_KEY=$PANEL_SECRET_KEY" >> .env
echo "PROXY_REGISTER_ENDPOINT=$PROXY_REGISTER_ENDPOINT" >> .env

# Generate self-signed certificate to a single file
echo " ** Generating self-signed certificate..."
mkdir -p data/certs/selfsigned
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout data/certs/selfsigned/privkey.pem \
    -out data/certs/selfsigned/cert.pem \
    -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.google.com" 2>/dev/null
cat data/certs/selfsigned/privkey.pem data/certs/selfsigned/cert.pem > data/certs/selfsigned/fullchain.pem
mkdir -p /etc/ssl/ha-certs
cp data/certs/selfsigned/fullchain.pem /etc/ssl/ha-certs/selfsigned.pem

# proxy-docker-compose.yml
echo " ** Building docker images..."
docker compose -f proxy-docker-compose.yml build >/dev/null

echo " ** Starting docker containers..."
docker compose -f proxy-docker-compose.yml down >/dev/null
docker compose -f proxy-docker-compose.yml up -d

echo " ** Done! The proxy is now running and connected to your main Libertea server at $CONN_PROXY_IP."