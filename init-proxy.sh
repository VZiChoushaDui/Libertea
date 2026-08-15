#!/bin/bash

set -e

# if not elevated, elevate
if [ "$EUID" -ne 0 ]; then
    sudo "$0" "$@"
    exit
fi

export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a

LIBERTEA_IRAN=0
POSITIONAL=()
for arg in "$@"; do
    case "$arg" in
        --iran-blackout|--restricted-network|--iran) LIBERTEA_IRAN=1 ;;
        *) POSITIONAL+=("$arg") ;;
    esac
done

CONFIGURATION_URL="${POSITIONAL[0]:-}"
PROXY_TYPE="${POSITIONAL[1]:-}"
DOCKERIZED_PROXY="0"
IS_UPDATING="0"

OTHER_PARAM="${POSITIONAL[2]:-}"
if [ ! -z "$OTHER_PARAM" ]; then
    echo "Legacy mode detected. Switching to legacy mode..."
    bash init-proxy.legacy.sh "${POSITIONAL[@]}"
    exit
fi

DIR="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
cd "$DIR"

# shellcheck source=bash-tools/restricted-network.sh
. "$DIR/bash-tools/restricted-network.sh"

if [ "$LIBERTEA_IRAN" != "1" ] && [ -f "$DIR/$LIBERTEA_RESTRICTED_MARKER" ]; then
    echo " ** Existing Iran blackout install detected (.libertea.iran)"
    LIBERTEA_IRAN=1
fi
if [ "$LIBERTEA_IRAN" != "1" ] && libertea_restricted_detect; then
    if libertea_restricted_prompt_autodetect; then
        LIBERTEA_IRAN=1
    fi
fi
if [ "$LIBERTEA_IRAN" = "1" ]; then
    libertea_restricted_require_files proxy
    libertea_restricted_apply
fi

set +e
MAIN_IP=$(curl --fail -s "$CONFIGURATION_URL/main-ip")
PANEL_DOMAIN=$(curl --fail -s "$CONFIGURATION_URL/panel-domain")
PANEL_SECRET_KEY=$(curl --fail -s "$CONFIGURATION_URL/panel-secret-key")
PROXY_CONNECT_UUID=$(curl --fail -s "$CONFIGURATION_URL/proxy-connect-uuid")
set -e

if [ "$CONFIGURATION_URL" == "update" ]; then
    . .env
    IS_UPDATING="1"
fi

if [ -z "$MAIN_IP" ] || [ -z "$PANEL_SECRET_KEY" ] || [ -z "$PANEL_DOMAIN" ] || [ -z "$PROXY_CONNECT_UUID" ]; then
    echo "Failed to get configuration from $CONFIGURATION_URL"
    exit 1
fi

echo "Installing Libertea proxy..."
echo "  Main server is $PANEL_DOMAIN ($MAIN_IP)"

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
        if [ "$LIBERTEA_IRAN" = "1" ]; then
            apt-get install -q -y docker.io >/dev/null
        else
            curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
            sh /tmp/get-docker.sh >/dev/null
        fi
    fi
    echo " ** Installing docker compose..."
    if [ "$LIBERTEA_IRAN" = "1" ]; then
        apt-get install -q -y docker-compose >/dev/null
    else
        apt-get install -q -y docker-compose-plugin >/dev/null
    fi

    # if docker version is 23.x, apply apparmor fix: https://stackoverflow.com/q/75346313
    if [[ $(docker --version | cut -d ' ' -f 3 | cut -d '.' -f 1) == "23" ]]; then
        echo "    - Applying apparmor fix..."
        apt-get install -qq -y apparmor apparmor-utils >/dev/null
        service docker restart
    fi
else
    echo "    - Installing python, haproxy, autossh, build-essential, cron..."
    apt-get install -q -y python3 python3-dev python3-pip haproxy autossh build-essential cron | sed 's/^/        /'
    
    echo "    - Installing python dependencies..."
    export PIP_BREAK_SYSTEM_PACKAGES=1
    pip3 install -r proxy-register/requirements.txt | sed 's/^/        /'
fi

echo " ** Creating .env file..."
if [ -f .env ]; then
    rm -f .env.bak
    mv .env .env.bak
fi
echo "MAIN_IP=$MAIN_IP" >> .env
echo "PANEL_SECRET_KEY=$PANEL_SECRET_KEY" >> .env
# echo "PROXY_REGISTER_ENDPOINT=$PROXY_REGISTER_ENDPOINT" >> .env
echo "PROXY_CONNECT_UUID=$PROXY_CONNECT_UUID" >> .env
echo "PANEL_DOMAIN=$PANEL_DOMAIN" >> .env
echo "PROXY_TYPE=$PROXY_TYPE" >> .env

# Generate self-signed certificate to a single file
mkdir -p /etc/ssl/ha-certs
echo " ** Generating self-signed certificate..."
mkdir -p data/certs/selfsigned
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout data/certs/selfsigned/privkey.pem \
    -out data/certs/selfsigned/cert.pem \
    -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.google.com" 2>/dev/null
cat data/certs/selfsigned/privkey.pem data/certs/selfsigned/cert.pem > data/certs/selfsigned/fullchain.pem
cp data/certs/selfsigned/fullchain.pem /etc/ssl/ha-certs/selfsigned.pem

# check if ssh key exists for user
if [ ! -f /root/.ssh/id_rsa.pub ]; then
    echo " ** Generating ssh key..."
    ssh-keygen -t rsa -b 4096 -N "" -f /root/.ssh/id_rsa >/dev/null
fi

proxy_compose() {
    if [ "$LIBERTEA_IRAN" = "1" ]; then
        docker-compose $PROXY_COMPOSE_FILE_ARGS "$@"
    else
        docker compose $PROXY_COMPOSE_FILE_ARGS "$@"
    fi
}

# A build-cache record whose snapshot is no longer on disk (interrupted build,
# full disk, unclean shutdown) makes the same layer fail on every run, and one
# failed image cancels the rest of the build. Dropping the cache is the only
# way out, so do it here instead of leaving the install half-finished.
proxy_compose_build() {
    if proxy_compose build "$@"; then
        return 0
    fi
    echo " ** Build failed. Clearing the Docker build cache and retrying once..."
    docker builder prune -af >/dev/null 2>&1 || true
    proxy_compose build --no-cache "$@"
}

if [ "$DOCKERIZED_PROXY" == "1" ]; then
    PROXY_COMPOSE_BUILD_ARGS=""
    if [ "$LIBERTEA_IRAN" = "1" ]; then
        PROXY_COMPOSE_BUILD_ARGS="--build-arg DOCKER_REGISTRY=${LIBERTEA_DOCKER_REGISTRY} --build-arg ALPINE_MIRROR=${LIBERTEA_ALPINE_MIRROR} --build-arg UBUNTU_MIRROR=${LIBERTEA_UBUNTU_MIRROR} --build-arg DEBIAN_MIRROR=${LIBERTEA_DEBIAN_MIRROR} --build-arg PIP_INDEX_URL=${PIP_INDEX_URL} --build-arg PIP_TRUSTED_HOST=${PIP_TRUSTED_HOST}"
    fi
    if [ "$ENVIRONMENT" == "dev" ]; then
        PROXY_COMPOSE_FILE_ARGS="-f proxy-docker-compose.dev.yml"
        if [ "$LIBERTEA_IRAN" = "1" ]; then
            PROXY_COMPOSE_FILE_ARGS="$PROXY_COMPOSE_FILE_ARGS -f proxy-docker-compose.iran.yml"
        fi
        echo " ** Building docker images..."
        proxy_compose_build $PROXY_COMPOSE_BUILD_ARGS

        echo " ** Starting docker containers..."
        proxy_compose down >/dev/null
        proxy_compose up -d
    else
        PROXY_COMPOSE_FILE_ARGS="-f proxy-docker-compose.yml"
        if [ "$LIBERTEA_IRAN" = "1" ]; then
            PROXY_COMPOSE_FILE_ARGS="$PROXY_COMPOSE_FILE_ARGS -f proxy-docker-compose.iran.yml"
        fi
        if [ "$LIBERTEA_IRAN" = "1" ]; then
            echo " ** Building docker images (restricted network, no Docker Hub pull)..."
            proxy_compose_build $PROXY_COMPOSE_BUILD_ARGS
        else
            echo " ** Pulling docker images..."
            proxy_compose pull
            proxy_compose_build
        fi

        echo " ** Starting docker containers..."
        proxy_compose down >/dev/null
        proxy_compose up -d
    fi
else
    # clean up any old libertea docker containers, if any
    set +e
    echo " ** Cleaning up old Libertea proxies..."
    if [ "$LIBERTEA_IRAN" = "1" ]; then
        docker-compose -f proxy-docker-compose.yml down >/dev/null
    else
        docker compose -f proxy-docker-compose.yml down >/dev/null
    fi
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

    if [ "$LIBERTEA_PROXY_DISABLE_REGISTER" == "1" ]; then
        echo "       proxy-register is disabled"
        systemctl disable libertea-proxy-register.service
        systemctl stop libertea-proxy-register.service
        echo "LIBERTEA_PROXY_DISABLE_REGISTER=1" >> .env
    else
        systemctl enable libertea-proxy-register.service
        systemctl restart libertea-proxy-register.service
    fi

    if [ "$PROXY_TYPE" == "ssh" ]; then
        echo "     - proxy-ssh-tunnel-tls"
        ./proxy-ssh-tunnel/install-services.sh "$MAIN_IP" "8443" "libertea" 10001 3

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
    sed -i "s|\${CONN_PROXY_IP}|$MAIN_IP|g" /etc/haproxy/haproxy.cfg
    systemctl enable haproxy
    systemctl start haproxy
fi

echo " ** Adding auto-update cronjob..."
# create a cronjob to run ./libertea-autoupdate-proxy.sh on bash and save the output to /tmp/libertea-autoupdate-proxy.log
if ! crontab -l | grep -q "libertea-autoupdate-proxy.sh"; then
    (crontab -l 2>/dev/null; echo "") | crontab -
    (crontab -l 2>/dev/null; echo "0 0 * * * bash $DIR/libertea-autoupdate-proxy.sh >> /tmp/libertea-autoupdate-proxy.log 2>&1") | crontab -
fi

echo ""
echo " ** Done! The proxy is now running and connected to your main Libertea server at $MAIN_IP."
