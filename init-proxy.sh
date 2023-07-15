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
PROXY_TYPE="$4"
DOCKERIZED_PROXY="0"
IS_UPDATING="0"

DIR="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
cd "$DIR"

if [ "$1" == "update" ]; then
    . .env
    IS_UPDATING="1"
fi

if [ -z "$CONN_PROXY_IP" ] || [ -z "$PANEL_SECRET_KEY" ] || [ -z "$PROXY_REGISTER_ENDPOINT" ]; then
    echo "Usage: $0 <CONN_PROXY_IP> <PANEL_SECRET_KEY> <PROXY_REGISTER_ENDPOINT> <PROXY_TYPE>"
    echo "    or $0 update"
    exit 1
fi

if [ -z "$PROXY_TYPE" ]; then
    PROXY_TYPE="auto"
fi

if [ "$PROXY_TYPE" == "tcp-docker" ]; then
    DOCKERIZED_PROXY="1"
elif [ "$PROXY_TYPE" == "tcp" ] || [ "$PROXY_TYPE" == "ssh" ] || [ "$PROXY_TYPE" == "https" ]; then
    DOCKERIZED_PROXY="0"
elif [ "$PROXY_TYPE" == "auto" ]; then
    echo "Determining proxy type..."
    # get country code
    set +e
    COUNTRY_CODE=$(curl -s --fail --max-time 3 https://ifconfig.io/country_code)
    if [ -z "$COUNTRY_CODE" ]; then
        COUNTRY_CODE=$(curl -s --fail --max-time 3 https://ifconfig.io/country_code)
    fi
    if [ -z "$COUNTRY_CODE" ]; then
        COUNTRY_CODE=$(curl -s --fail --max-time 3 http://ifconfig.io/country_code)
    fi
    if [ -z "$COUNTRY_CODE" ]; then
        COUNTRY_CODE=$(curl -s --fail --max-time 3 https://ipapi.co/country_code)
    fi
    if [ -z "$COUNTRY_CODE" ]; then
        COUNTRY_CODE=$(curl -s --fail --max-time 3 https://ipinfo.io/country)
    fi
    if [ -z "$COUNTRY_CODE" ]; then
        apt-get update
        apt-get install -y jq
        COUNTRY_CODE=$(curl -s --fail --max-time 3 https://api.myip.com/ | jq -r .cc)
    fi
    set -e
    if [ -z "$COUNTRY_CODE" ]; then
        echo "Could not get country code. Will use ssh proxy."
        PROXY_TYPE="ssh"
    else
        countries=("CN" "CU" "TH" "TM" "IR" "SY" "SA" "TR")

        if [[ " ${countries[@]} " =~ " ${COUNTRY_CODE} " ]]; then
            echo "Will use ssh proxy because server is in $COUNTRY_CODE"
            PROXY_TYPE="ssh"
        else
            echo "Will use tcp proxy"
            PROXY_TYPE="tcp"
        fi
    fi
elif [ "$PROXY_TYPE" == "same" ]; then
    if [ -f .libertea.proxy_type ]; then
        PROXY_TYPE=$(cat .libertea.proxy_type)
    else
        echo "Could not determine proxy type. Please run the install script again on this server."
        exit 1
    fi
else
    echo "Invalid proxy type. Valid proxy types: auto, tcp, ssh, https"
    exit 1
fi

# if .libertea.main file exists, then this is a main server. don't install proxy
if [ -f .libertea.main ]; then
    echo "This is a main Libertea server. You need to install Libertea secondary proxy on a different server."
    exit 1
fi

touch .libertea.proxy
export DEBIAN_FRONTEND=noninteractive

echo " ** Installing dependencies..."

if ! command -v sed &> /dev/null; then
    apt-get update -q
else
    apt-get update -q | sed 's/^/        /'
fi


if ! command -v sed &> /dev/null; then
    echo "    - Installing sed..."
    apt-get install -q -y sed
fi

if ! command -v ufw &> /dev/null; then
    echo "    - Installing ufw..."
    apt-get install -q -y ufw | sed 's/^/        /'
fi

echo "    - Initializing firewall..."
set +e
yes | /usr/share/ufw/check-requirements >/dev/null
if [ $? -ne 0 ]; then
    echo "       WARNING: UFW requirements not met. Disabling UFW."
    yes | ufw disable >/dev/null
else
    ufw allow ssh >/dev/null
    ufw allow http >/dev/null
    ufw allow https >/dev/null
    yes | ufw enable >/dev/null
fi
set -e

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
    echo "    - Installing python, haproxy, autossh..."
    apt-get install -q -y python3 python3-dev python3-pip haproxy autossh | sed 's/^/        /'
    
    echo "    - Installing python dependencies..."
    export PIP_BREAK_SYSTEM_PACKAGES=1
    pip3 install -r proxy-register/requirements.txt | sed 's/^/        /'
fi

echo " ** Creating .env file..."
if [ -f .env ]; then
    rm -f .env.bak
    mv .env .env.bak
fi
echo "CONN_PROXY_IP=$CONN_PROXY_IP" >> .env
echo "PANEL_SECRET_KEY=$PANEL_SECRET_KEY" >> .env
echo "PROXY_REGISTER_ENDPOINT=$PROXY_REGISTER_ENDPOINT" >> .env
echo "PROXY_TYPE=$PROXY_TYPE" >> .env

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

# check if ssh key exists for user
if [ ! -f /root/.ssh/id_rsa.pub ]; then
    echo " ** Generating ssh key..."
    ssh-keygen -t rsa -b 4096 -N "" -f /root/.ssh/id_rsa >/dev/null
fi

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
    systemctl stop libertea-proxy-ssh-tunnel-0.service >/dev/null
    systemctl stop libertea-proxy-ssh-tunnel-1.service >/dev/null
    systemctl stop libertea-proxy-ssh-tunnel-2.service >/dev/null
    systemctl stop libertea-proxy-ssh-tunnel-3.service >/dev/null
    systemctl stop libertea-proxy-ssh-tunnel-4.service >/dev/null
    systemctl disable libertea-proxy-ssh-tunnel-0.service >/dev/null
    systemctl disable libertea-proxy-ssh-tunnel-1.service >/dev/null
    systemctl disable libertea-proxy-ssh-tunnel-2.service >/dev/null
    systemctl disable libertea-proxy-ssh-tunnel-3.service >/dev/null
    systemctl disable libertea-proxy-ssh-tunnel-4.service >/dev/null
    systemctl stop libertea-proxy-fake-traffic.service >/dev/null
    systemctl disable libertea-proxy-fake-traffic.service >/dev/null
    set -e

    echo " ** Installing services..."
    echo "     - proxy-register"
    cp proxy-register/libertea-proxy-register.service /etc/systemd/system/libertea-proxy-register.service
    sed -i "s|{rootpath}|$DIR|g" /etc/systemd/system/libertea-proxy-register.service
    systemctl daemon-reload
    systemctl enable libertea-proxy-register.service
    systemctl restart libertea-proxy-register.service

    if [ "$PROXY_TYPE" == "ssh" ]; then
        echo "     - proxy-ssh-tunnel-tls"
        ./proxy-ssh-tunnel/install-services.sh "$CONN_PROXY_IP" "8443" "libertea" 10001 3

        set +e
        CPU_COUNT=$(grep -c ^processor /proc/cpuinfo)
        if [ "$CPU_COUNT" == "1" ]; then
            systemctl stop libertea-proxy-ssh-tunnel-2.service
            systemctl disable libertea-proxy-ssh-tunnel-2.service
        fi
        set -e
    fi

    echo "     - haproxy"
    set +e
    systemctl stop haproxy
    set -e
    rm -f /etc/haproxy/haproxy.cfg
    if [ "$PROXY_TYPE" == "ssh" ]; then
        cp proxy-haproxy/haproxy.ssh.cfg /etc/haproxy/haproxy.cfg
    elif [ "$PROXY_TYPE" == "tcp" ]; then
        cp proxy-haproxy/haproxy.tcp.cfg /etc/haproxy/haproxy.cfg
    elif [ "$PROXY_TYPE" == "https" ]; then
        cp proxy-haproxy/haproxy.https.cfg /etc/haproxy/haproxy.cfg
    else
        echo "ERROR: Invalid proxy type: $PROXY_TYPE"
        exit 1
    fi
    sed -i "s|\${CONN_PROXY_IP}|$CONN_PROXY_IP|g" /etc/haproxy/haproxy.cfg
    systemctl enable haproxy
    systemctl start haproxy
fi

echo " ** Done! The proxy is now running and connected to your main Libertea server at $CONN_PROXY_IP."
