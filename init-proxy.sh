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
DOCKERIZED_PROXY="0"

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
export DEBIAN_FRONTEND=noninteractive

echo " ** Installing dependencies..."
apt-get update >/dev/null

if ! command -v ufw &> /dev/null; then
    echo "    - Installing ufw..."
    apt-get install -qq -y ufw >/dev/null
fi

echo " ** Initializing firewall..."
ufw allow ssh >/dev/null
ufw allow http >/dev/null
ufw allow https >/dev/null
yes | ufw enable >/dev/null

if [ "$DOCKERIZED_PROXY" == "1" ]; then
    echo " ** Installing docker..."
    if ! command -v docker &> /dev/null; then
        curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
        sh /tmp/get-docker.sh >/dev/null
    fi
    echo " ** Installing docker compose..."
    apt-get install docker-compose-plugin >/dev/null

    # if docker version is 23.x, apply apparmor fix: https://stackoverflow.com/q/75346313
    if [[ $(docker --version | cut -d ' ' -f 3 | cut -d '.' -f 1) == "23" ]]; then
        echo "    - Applying apparmor fix..."
        apt-get install -qq -y apparmor apparmor-utils >/dev/null
        service docker restart
    fi
else
    echo "    - Installing python..."
    if ! command -v python3 &> /dev/null; then
        apt-get install -qq -y python3 >/dev/null
    fi
    apt-get install -qq -y python3-dev >/dev/null
    if ! command -v pip3 &> /dev/null; then
        apt-get install -qq -y python3-pip >/dev/null
    fi

    echo "    - Installing python dependencies..."
    pip3 install -r proxy-register/requirements.txt | sed 's/^/        /'

    echo "    - Installing haproxy..."
    apt-get install -qq -y haproxy >/dev/null
fi


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

if [ "$DOCKERIZED_PROXY" == "1" ]; then
    if [ "$ENVIRONMENT" == "dev" ]; then
        echo " ** Building docker images..."
        docker compose -f proxy-docker-compose.dev.yml build

        echo " ** Starting docker containers..."
        docker compose -f proxy-docker-compose.dev.yml down >/dev/null
        docker compose -f proxy-docker-compose.dev.yml up -d
    else
        echo " ** Pulling docker images..."
        docker compose -f proxy-docker-compose.yml pull
        docker compose -f proxy-docker-compose.yml build

        echo " ** Starting docker containers..."
        docker compose -f proxy-docker-compose.yml down >/dev/null
        docker compose -f proxy-docker-compose.yml up -d
    fi
else
    # clean up any old libertea docker containers, if any
    set +e
    echo " ** Cleaning up old Libertea proxies..."
    docker compose -f proxy-docker-compose.yml down >/dev/null
    set -e

    echo " ** Installing services..."
    echo "     - proxy-register"
    cp proxy-register/libertea-proxy-register.service /etc/systemd/system/libertea-proxy-register.service
    sed -i "s|{rootpath}|$DIR|g" /etc/systemd/system/libertea-proxy-register.service
    systemctl daemon-reload
    systemctl enable libertea-proxy-register.service
    systemctl restart libertea-proxy-register.service

    echo "     - proxy-fake-traffic"
    cp proxy-fake-traffic/libertea-proxy-fake-traffic.service /etc/systemd/system/libertea-proxy-fake-traffic.service
    sed -i "s|{rootpath}|$DIR|g" /etc/systemd/system/libertea-proxy-fake-traffic.service
    systemctl daemon-reload
    systemctl enable libertea-proxy-fake-traffic.service
    systemctl restart libertea-proxy-fake-traffic.service

    echo "    - proxy-ssh-tunnel"
    ./proxy-ssh-tunnel/install-services.sh "$CONN_PROXY_IP" "443" "root" # TODO: Replace user with non-root user

    echo "     - haproxy"
    systemctl stop haproxy
    rm -f /etc/haproxy/haproxy.cfg
    cp proxy-haproxy/haproxy.cfg /etc/haproxy/haproxy.cfg
    sed -i "s|\${CONN_PROXY_IP}|$CONN_PROXY_IP|g" /etc/haproxy/haproxy.cfg
    systemctl enable haproxy
    systemctl start haproxy
fi

echo " ** Done! The proxy is now running and connected to your main Libertea server at $CONN_PROXY_IP."
