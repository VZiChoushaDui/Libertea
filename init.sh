#!/bin/bash

set -e

# if not elevated, elevate
if [ "$EUID" -ne 0 ]; then
    sudo "$0" "$@"
    exit
fi

LIBERTEA_IRAN=0
POSITIONAL=()
for arg in "$@"; do
    case "$arg" in
        --iran-blackout|--restricted-network|--iran) LIBERTEA_IRAN=1 ;;
        *) POSITIONAL+=("$arg") ;;
    esac
done
COMMAND="${POSITIONAL[0]:-}"

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
    libertea_restricted_require_files main
    libertea_restricted_apply
fi

COMPOSE_FILE_ARGS=""
compose() {
    if [ "$LIBERTEA_IRAN" = "1" ]; then
        docker-compose $COMPOSE_FILE_ARGS "$@"
    else
        docker compose $COMPOSE_FILE_ARGS "$@"
    fi
}

# A build-cache record whose snapshot is no longer on disk (interrupted build,
# full disk, unclean shutdown) makes the same layer fail on every run, and one
# failed image cancels the rest of the build. Dropping the cache is the only
# way out, so do it here instead of leaving the install half-finished.
compose_build() {
    if compose build "$@"; then
        return 0
    fi
    echo "    - Build failed. Clearing the Docker build cache and retrying once..."
    docker builder prune -af >/dev/null 2>&1 || true
    compose build --no-cache "$@"
}

echo ""
echo " _      _ _               _              "
echo "| |    (_) |             | |             "
echo "| |     _| |__   ___ _ __| |_ ___  __ _  "
echo "| |    | | '_ \ / _ \ '__| __/ _ \/ _\` | "
echo "| |____| | |_) |  __/ |  | ||  __/ (_| | "
echo "|______|_|_.__/ \___|_|   \__\___|\__,_| "
echo ""
echo ""
echo ""

# if .libertea.proxy file exists, then this is a proxy server. don't install main
if [ -f .libertea.proxy ]; then
    echo "This is a Libertea proxy server. You can't install both main and proxy on the same server."
    exit 1
fi

touch .libertea.main
export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a

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

# if ! command -v certbot &> /dev/null; then
#     echo "    - Installing certbot..."
#     if [ "$(lsb_release -rs)" == "20.04" ]; then
#         # if ubuntu version is 20.04, add certbot repository
#         add-apt-repository -y ppa:certbot/certbot > /dev/null
#     fi
#     apt-get update > /dev/null
#     apt-get install -qq -y certbot > /dev/null
# fi

echo "    - Installing core dependencies..."
apt-get install -q -y ufw dnsutils uuid-runtime openssl jq coreutils build-essential cron | sed 's/^/        /'

echo "    - Installing python..."
apt-get install -q -y python3 python3-dev python3-pip | sed 's/^/        /'

echo "    - Installing python dependencies..."
export PIP_BREAK_SYSTEM_PACKAGES=1
set +e
if [ "$(pip3 --version 2>&1 | grep X509_V_FLAG)" ]; then
    pip3 --version > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "    - Applying pip openssl fix..."
        python3 -m easy_install "$DIR/bash-tools/pip/pyOpenSSL-22.1.0-py3-none-any.whl" | sed 's/^/        /'

        # Fix dependencies
        pip3 install pyopenssl==22.1.0 | sed 's/^/        /'
    fi
    pip3 --version > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "    - Applying pip openssl fix 2..."
        python3 -m easy_install "$DIR/bash-tools/pip/pyOpenSSL-24.0.0-py3-none-any.whl" | sed 's/^/        /'

        # Fix dependencies
        pip3 install pyopenssl==24.0.0 | sed 's/^/        /'
    fi
fi


pip3 install -r panel/requirements.txt
if [ $? -ne 0 ]; then
    echo "Failed to install requirements. Trying to fix it..."
    pip3 install -r panel/requirements.txt --force-reinstall --ignore-installed
    pip3 install -r panel/requirements.txt
    if [ $? -ne 0 ]; then
        echo ""
        echo ""
        echo "Failed to install requirements. Please send a bug report at"
        echo "https://github.com/VZiChoushaDui/Libertea/issues/new"
        echo "and send this log alongside it."
        echo ""
        echo ""
        exit 1
    fi
fi

if [ "$(pip3 --version 2>&1 | grep X509_V_FLAG)" ]; then
    pip3 --version > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "    - Applying pip openssl fix..."
        python3 -m easy_install "$DIR/bash-tools/pip/pyOpenSSL-22.1.0-py3-none-any.whl" | sed 's/^/        /'

        # Fix dependencies
        pip3 install pyopenssl==22.1.0 | sed 's/^/        /'
    fi
    pip3 --version > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "    - Applying pip openssl fix 2..."
        python3 -m easy_install "$DIR/bash-tools/pip/pyOpenSSL-24.0.0-py3-none-any.whl" | sed 's/^/        /'

        # Fix dependencies
        pip3 install pyopenssl==24.0.0 | sed 's/^/        /'
    fi
fi
set -e

echo "    - Installing docker..."
if ! command -v docker &> /dev/null; then
    if [ "$LIBERTEA_IRAN" = "1" ]; then
        apt-get install -q -y docker.io | sed 's/^/        /'
    else
        curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
        sh /tmp/get-docker.sh | sed 's/^/        /' >/dev/null
    fi
fi
echo "    - Installing docker compose..."
if [ "$LIBERTEA_IRAN" = "1" ]; then
    apt-get install -q -y docker-compose | sed 's/^/        /'
else
    apt-get install -q -y docker-compose-plugin | sed 's/^/        /'
fi

# if docker version is 23.x, apply apparmor fix: https://stackoverflow.com/q/75346313
if [[ $(docker --version | cut -d ' ' -f 3 | cut -d '.' -f 1) == "23" ]]; then
    echo "    - Applying apparmor fix..."
    apt-get install -q -y apparmor apparmor-utils | sed 's/^/        /'
    service docker restart
fi

if ! command -v openvpn >/dev/null 2>&1; then
    echo "    - Installing openvpn (optional, for OpenVPN outbounds)..."
    apt-get install -q -y openvpn | sed 's/^/        /' || echo "       WARNING: openvpn install failed; OpenVPN outbounds will be unavailable."
fi

echo "    - Initializing firewall..."
set +e
SSH_PORT=$(ss -tlpn 2>/dev/null | grep sshd | grep -oP '(?<=:)\d+(?=\s)' | head -n 1)
if [[ ! $SSH_PORT =~ ^[0-9]+$ ]]; then
    SSH_PORT=$(ss -tlpn 2>/dev/null | grep ':22' | grep -oP '(?<=:)\d+(?=\s)' | head -n 1)
fi
if [[ ! $SSH_PORT =~ ^[0-9]+$ ]]; then
    SSH_PORT=$(netstat -tulpn 2>/dev/null | grep sshd | cut -d ":" -f 2 | cut -d " " -f 1 | head -n 1)
fi
# check if SSH_PORT is a number
if [[ ! $SSH_PORT =~ ^[0-9]+$ ]]; then
    echo "       WARNING: Could not detect ssh port. Will not touch firewall."
else
    yes | /usr/share/ufw/check-requirements >/dev/null
    if [ $? -ne 0 ]; then
        echo "       WARNING: UFW requirements not met. Disabling UFW."
        yes | ufw disable >/dev/null
    else
        ufw allow "$SSH_PORT" >/dev/null
        ufw allow http >/dev/null
        ufw allow https >/dev/null
        ufw allow 8443 >/dev/null
        yes | ufw enable >/dev/null
    fi
fi
set -e

# check if cpu supports avx2 (on x86/x64 based systems)
if [[ $(uname -m) == *"x86"* ]]; then
    if [[ ! $(grep avx2 /proc/cpuinfo) ]]; then 
        echo " ** Your CPU does not support AVX2, Libertea will run in compatibility mode."
        echo "    Please consider upgrading your CPU to support AVX2."
        # change docker-compose.yml to use compatibility image
        sed -i "s|image: mongo:latest|image: mongo:4.4|g" docker-compose.yml
    fi
fi

echo " ** Detecting server IP address..."
set +e
my_ip=""
for ip_url in https://ifconfig.io/ip https://api.ipify.org https://icanhazip.com https://ident.me https://checkip.amazonaws.com; do
    my_ip=$(curl -s --ipv4 --fail --max-time 3 "$ip_url")
    if [[ $my_ip =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        echo "    Public IP $my_ip (from $ip_url)"
        break
    fi
    my_ip=""
done

if [[ ! $my_ip ]]; then
    echo "    Public IP lookup failed. Trying local interfaces..."
    for iface in eth0 ens3 ens4 ens5 enp0s3 enp0s5 enp1s0 enp3s0 ens18 ens160 eno1 bond0; do
        candidate=$(ip -4 addr show "$iface" 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -n1)
        if [[ $candidate && ! $candidate =~ ^127\. ]]; then
            my_ip="$candidate"
            echo "    Detected IP $my_ip on interface $iface"
            break
        fi
    done
fi
if [[ ! $my_ip ]]; then
    my_ip=$(ip -4 addr show 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '^127\.' | head -n1)
    if [[ $my_ip ]]; then
        echo "    Detected IP $my_ip (fallback)"
    fi
fi
set -e

if [[ "$COMMAND" != "update" ]]; then
    echo ""
    if [[ $my_ip ]]; then
        read -r -p "    Use $my_ip as this server's public IP? [Y/n]: " ip_confirm
        ip_confirm="${ip_confirm:-Y}"
        if [[ "$ip_confirm" =~ ^[Nn] ]]; then
            my_ip=""
        fi
    fi
    if [[ ! $my_ip ]]; then
        read -r -p "    Enter this server's public IP address: " my_ip
        while ! [[ "$my_ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; do
            echo "    Invalid IP address. Please enter a valid IPv4 address:"
            read -r my_ip
        done
    fi
    echo ""
elif [[ ! $my_ip ]]; then
    echo " ** Failed to get public IP. Please check your internet connection."
    exit 1
fi


# if .env does not exist, copy sample.env and fill it with random values
if [ ! -f .env ]; then
    echo " ** Generating .env..."

    while IFS= read -r line; do
        # if line does not end with =, then it is a comment, so just copy it
        if [[ $line != *"=" ]]; then
            echo "$line" >> .env
            continue
        fi

        if [[ $line == *"UUID"* ]]; then
            echo "$line$(uuidgen)" >> .env
        elif [[ $line == *"URL"* ]]; then
            echo "$line$(openssl rand -hex 16)" >> .env
        else
            echo "$line$(openssl rand -hex 32)" >> .env
        fi
    done < sample.env
else
    echo " ** Updating .env..."

    if grep -q "FIREWALL_OUTBOUND_TCP_PORTS=\"22 53 80 8080 443 8443 3389\"" .env; then
        echo "    - Removing old default FIREWALL_OUTBOUND_TCP_PORTS from .env..."
        sed -i '/FIREWALL_OUTBOUND_TCP_PORTS="22 53 80 8080 443 8443 3389"/d' .env
    fi

    if grep -q "FIREWALL_OUTBOUND_TCP_PORTS=\"22 53 80 8080 443 8443 3389 5222\"" .env; then
        echo "    - Removing old default FIREWALL_OUTBOUND_TCP_PORTS from .env..."
        sed -i '/FIREWALL_OUTBOUND_TCP_PORTS="22 53 80 8080 443 8443 3389 5222"/d' .env
    fi

    if grep -q "FIREWALL_OUTBOUND_UDP_PORTS=\"53 443 123 19302:19309\"" .env; then
        echo "    - Removing old default FIREWALL_OUTBOUND_UDP_PORTS from .env..."
        sed -i '/FIREWALL_OUTBOUND_UDP_PORTS="53 443 123 19302:19309"/d' .env
    fi

    # The variable-adding loop below only fills in missing variables, so an
    # empty value left over from a hand-edited .env has to be healed here.
    if grep -q "^STATIC_RESOURCE_UUID=[[:space:]]*$" .env; then
        echo "    - Filling empty STATIC_RESOURCE_UUID in .env..."
        sed -i "s|^STATIC_RESOURCE_UUID=[[:space:]]*$|STATIC_RESOURCE_UUID=$(uuidgen)|" .env
    fi

    # If a variable is missing from .env, add it and fill it with value
    while IFS= read -r line; do
        if [[ $line != *"=" ]]; then
            # line does not end with =, check if it's a predefined variable with regex, and add it to .env if not exists
            if [[ $line =~ ^[a-zA-Z0-9_]+=[a-zA-Z0-9\.\-_\(\)\:\"\ \t]+(\#.*)?$ ]]; then
                var_name=$(echo "$line" | cut -d '=' -f 1)
                if ! grep -q "$var_name=" .env; then
                    echo "    - Adding $var_name to .env..."
                    echo "$line" >> .env
                fi
            fi
            continue
        fi

        if ! grep -q "$line" .env; then
            echo "    - Adding $line to .env and filling it..."
            if [[ $line == *"UUID"* ]]; then
                echo "$line$(uuidgen)" >> .env
            elif [[ $line == *"URL"* ]]; then
                echo "$line$(openssl rand -hex 16)" >> .env
            else
                echo "$line$(openssl rand -hex 32)" >> .env
            fi
        fi
    done < sample.env
fi

set +e
BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD)
if [ $? -ne 0 ]; then
    BRANCH_NAME="master"
fi
if [ -z "$BRANCH_NAME" ]; then
    BRANCH_NAME="master"
fi
cat .env | grep -v "LIBERTEA_BRANCH_NAME=" > .env.tmp
mv .env.tmp .env
echo "LIBERTEA_BRANCH_NAME=$BRANCH_NAME" >> .env

if [[ "$COMMAND" == "update" ]] && grep -qE '^SERVER_IP=[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' .env; then
    my_ip=$(grep "^SERVER_IP=" .env | cut -d '=' -f 2-)
    echo "    Using SERVER_IP=$my_ip from .env"
else
    grep -v "^SERVER_IP=" .env > .env.tmp && mv .env.tmp .env
    echo "SERVER_IP=$my_ip" >> .env
fi
set -e

if [ "$BRANCH_NAME" != "master" ]; then
    export ENVIRONMENT="dev"
fi

# if [ ! -f tools/flarectl ]; then
#     echo " ** Installing flarectl..."
#     mkdir tools
#     wget https://github.com/cloudflare/cloudflare-go/releases/download/v0.58.0/flarectl_0.58.0_linux_amd64.tar.xz -O tools/flarectl.tar.xz >/dev/null 2>&1
#     tar -xf tools/flarectl.tar.xz -C tools >/dev/null
#     rm tools/flarectl.tar.xz
#     chmod +x tools/flarectl
# fi

# mkdir -p tools
# if [ ! -f tools/wgcf ]; then
#     echo " ** Installing wgcf..."
#     set +e
#     if [[ $(uname -m) == *"x86"* ]]; then
#         wget https://github.com/ViRb3/wgcf/releases/download/v2.2.22/wgcf_2.2.22_linux_amd64 -O tools/wgcf >/dev/null 2>&1
#     else
#         wget https://github.com/ViRb3/wgcf/releases/download/v2.2.22/wgcf_2.2.22_linux_arm64 -O tools/wgcf >/dev/null 2>&1
#     fi

#     chmod +x tools/wgcf
#     set -e
# fi

# if [ ! -f tools/wgcf-account.toml ] || [ ! -f tools/wgcf-profile.conf ]; then
#     set +e
#     echo " ** Configuring Cloudflare WARP..."
#     yes | tools/wgcf register >/dev/null 2>&1
#     tools/wgcf generate >/dev/null 2>&1
#     mv wgcf-account.toml tools/wgcf-account.toml
#     mv wgcf-profile.conf tools/wgcf-profile.conf
#     set -e
# fi

# if command is update, then skip the following steps
if [ "$COMMAND" != "update" ]; then
    echo ""
    # echo "Please enter your Cloudflare email:"
    # read -r cloudflare_email
    # while ! [[ "$cloudflare_email" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$ ]]; do
    #     echo "Invalid email. Please enter a valid email:"
    #     read -r cloudflare_email
    # done
    # sed -i "s|CLOUDFLARE_EMAIL=.*|CLOUDFLARE_EMAIL=$cloudflare_email|g" .env

    # echo "Please enter your Cloudflare API key:"
    # read -r cloudflare_api_key
    # while ! [[ "$cloudflare_api_key" =~ ^[a-zA-Z0-9]+$ ]]; do
    #     echo "Invalid API key. Please enter a valid API key:"
    #     read -r cloudflare_api_key
    # done
    # sed -i "s|CLOUDFLARE_API_KEY=.*|CLOUDFLARE_API_KEY=$cloudflare_api_key|g" .env

    echo "Welcome to **Libertea** installation script."
    echo ""
    echo "To get started, you need a domain name configured on a CDN (e.g. Cloudflare) and configured to point to $my_ip"
    echo "Also, make sure that SSL/TLS encryption mode is set to *Full*."
    echo ""
    echo "Please enter your panel domain name (e.g. mydomain.com):"
    read -r panel_domain
    while ! [[ "$panel_domain" =~ ^[a-zA-Z0-9.-]+$ ]]; do
        echo "Invalid domain name. Please enter a valid domain name:"
        read -r panel_domain
    done
    sed -i "s|PANEL_DOMAIN=.*|PANEL_DOMAIN=$panel_domain|g" .env
    
    echo "Please enter a password for admin user:"
    read -r admin_password
    # check it is not empty and is at least 8 characters long
    while ! [[ "$admin_password" =~ ^.{8,}$ ]]; do
        echo "Invalid password. Please enter a password at least 8 characters long:"
        read -r admin_password
    done
    sed -i "s|PANEL_ADMIN_PASSWORD=.*|PANEL_ADMIN_PASSWORD=$admin_password|g" .env
    
    echo ""
fi

# load environment variables from .env
echo " ** Loading environment variables..."
set -a
. .env
set +a

# echo " ** Initializing certbot..."
# ./haproxy/certbot-init.sh >/dev/null

# Generate self-signed certificate to a single file

mkdir -p /etc/ssl/ha-certs
chmod +x haproxy/cert-camouflage.sh

# if /etc/ssl/ha-certs/selfsigned.pem does not exist
if [ ! -f /etc/ssl/ha-certs/selfsigned.pem ]; then
    echo " ** Generating self-signed certificate..."
    mkdir -p data/certs/selfsigned
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout data/certs/selfsigned/privkey.pem \
        -out data/certs/selfsigned/cert.pem \
        -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" 2>/dev/null
    cat data/certs/selfsigned/privkey.pem data/certs/selfsigned/cert.pem > data/certs/selfsigned/fullchain.pem
    cp data/certs/selfsigned/fullchain.pem /etc/ssl/ha-certs/selfsigned.pem
fi

echo " ** Initializing ssh tunnel..."
# create a user for ssh tunnel named "libertea" if not exists
if ! id -u libertea >/dev/null 2>&1; then
    useradd -m -s /bin/bash libertea
    echo "libertea:$(openssl rand -hex 32)" | chpasswd
fi
# Add ssh restrictions to sshd_config if not exists
if ! grep -q "Match User libertea" /etc/ssh/sshd_config; then
    echo "Match User libertea" >> /etc/ssh/sshd_config
    echo "    AllowTcpForwarding yes" >> /etc/ssh/sshd_config
    echo "    X11Forwarding no" >> /etc/ssh/sshd_config
    echo "    PermitTunnel yes" >> /etc/ssh/sshd_config
    echo "    AllowAgentForwarding no" >> /etc/ssh/sshd_config
    echo "    ForceCommand /bin/false" >> /etc/ssh/sshd_config
    set +e
    systemctl reload sshd
    systemctl reload ssh
    set -e
fi

echo " ** Initializing providers..."
echo "    - trojan-ws..."
./providers/trojan-ws/init.sh 2001 12001 "$CONN_TROJAN_WS_URL" "$CONN_TROJAN_WS_AUTH_PASSWORD"
echo "    - trojan-grpc..."
./providers/trojan-grpc/init.sh 2004 "$CONN_TROJAN_GRPC_URL" "$CONN_TROJAN_GRPC_AUTH_PASSWORD"
echo "    - shadowsocks-v2ray-ws..."
./providers/shadowsocks-v2ray/init.sh 2003 "$CONN_SHADOWSOCKS_V2RAY_URL" "$CONN_SHADOWSOCKS_V2RAY_AUTH_PASSWORD"
# echo "    - shadowsocks-grpc..."
# ./providers/vless-grpc/init.sh 2006 "$CONN_VLESS_GRPC_URL" "$CONN_VLESS_GRPC_AUTH_UUID"
echo "    - vless-ws..."
./providers/vless-ws/init.sh 2002 12002 "$CONN_VLESS_WS_URL" "$CONN_VLESS_WS_AUTH_UUID"
echo "    - vless-grpc..."
./providers/vless-grpc/init.sh 2005 "$CONN_VLESS_GRPC_URL" "$CONN_VLESS_GRPC_AUTH_UUID"
echo "    - vmess-grpc..."
./providers/vmess-grpc/init.sh 2007 "$CONN_VMESS_GRPC_URL" "$CONN_VMESS_GRPC_AUTH_UUID"


echo "    - outbound-warp..."
set +e
bash ./warp-reg.sh >/tmp/warp.json
private_key=$(jq -r '.private_key' /tmp/warp.json)
public_key=$(jq -r '.public_key' /tmp/warp.json)
endpoint=$(jq -r '.endpoint.host' /tmp/warp.json)
address_v4=$(jq -r '.v4' /tmp/warp.json)
address_v6=$(jq -r '.v6' /tmp/warp.json)
addresses="\"$address_v4/32\",\"$address_v6/128\""
reserved_array=$(jq -rc '.reserved_dec' /tmp/warp.json)
mtu="1280"
./providers/outbound-warp/init.sh 2997 "$endpoint" "$private_key" "$addresses" "$public_key" "$mtu" "$reserved_array"
set -e

echo "    - outbound-direct (sing-box 1.13.1)..."
./providers/outbound-direct/init.sh

echo " ** Installing web panel..."
mkdir -p ./data
mkdir -p "$DIR/certs"
touch ./data/all-domains-ever.lst
cp panel/libertea-panel.service /etc/systemd/system/
# replace {rootpath} with the path to the root of the project
sed -i "s|{rootpath}|$DIR|g" /etc/systemd/system/libertea-panel.service
systemctl daemon-reload
set +e
systemctl enable libertea-panel.service
pkill -9 -f uwsgi
systemctl kill libertea-panel.service
pkill -9 -f uwsgi
set -e
systemctl restart libertea-panel.service

COMPOSE_BUILD_ARGS=""
if [ "$LIBERTEA_IRAN" = "1" ]; then
    COMPOSE_BUILD_ARGS="--build-arg DOCKER_REGISTRY=${LIBERTEA_DOCKER_REGISTRY} --build-arg ALPINE_MIRROR=${LIBERTEA_ALPINE_MIRROR} --build-arg UBUNTU_MIRROR=${LIBERTEA_UBUNTU_MIRROR} --build-arg DEBIAN_MIRROR=${LIBERTEA_DEBIAN_MIRROR} --build-arg PIP_INDEX_URL=${PIP_INDEX_URL} --build-arg PIP_TRUSTED_HOST=${PIP_TRUSTED_HOST}"
fi

if [ "$ENVIRONMENT" == "dev" ]; then
    COMPOSE_FILE_ARGS="-f docker-compose.dev.yml"
    if [ "$LIBERTEA_IRAN" = "1" ]; then
        COMPOSE_FILE_ARGS="$COMPOSE_FILE_ARGS -f docker-compose.iran.yml"
    fi
    echo " ** Building docker containers..."
    compose_build $COMPOSE_BUILD_ARGS
else
    COMPOSE_FILE_ARGS=""
    if [ "$LIBERTEA_IRAN" = "1" ]; then
        COMPOSE_FILE_ARGS="-f docker-compose.yml -f docker-compose.iran.yml"
    fi
    if [ "$LIBERTEA_IRAN" = "1" ]; then
        echo " ** Building docker containers (restricted network, no Docker Hub pull)..."
        compose_build $COMPOSE_BUILD_ARGS
    else
        echo " ** Pulling docker containers..."
        compose pull
        compose_build
    fi
fi

# Services to start. Empty means "all of them". Compose resolves the image of
# every service in the file on `up`, pulling the ones it cannot build, and it
# does so even for services scaled to 0 -- so a service whose image is out of
# reach has to be left out of the list instead of scaled down.
# Listed by hand (same names in docker-compose.yml and docker-compose.dev.yml)
# so this works with apt's docker-compose 1.x, which we install in iran mode.
# `config --services` exists on 1.25+ but interpolates the whole file and is
# easy to break; a static list does not.
COMPOSE_UP_SERVICES=""
if [ "$LIBERTEA_IRAN" = "1" ]; then
    # provider-shadowsocks-v2ray's Dockerfile wget's xray-plugin and
    # shadowsocks-rust from GitHub, so its image can be neither built nor pulled.
    echo "    - Skipping provider-shadowsocks-v2ray (image needs GitHub)"
    COMPOSE_UP_SERVICES="mongodb rsyslog log-parser haproxy camouflage-nginx-fallback provider-trojan-ws provider-trojan-grpc provider-vless-ws provider-vless-grpc provider-vmess-grpc"
fi

echo " ** Starting docker containers..."
set +e
# --remove-orphans also clears out containers of services that no longer exist,
# such as the outbound-warp and outbound-direct providers replaced by the
# host sing-box. Left behind they would keep running with restart: always.
compose down --remove-orphans >/dev/null
set -e

echo "    - Starting MongoDB..."
compose up -d mongodb
sleep 3
if docker logs libertea-mongodb 2>&1 | grep -q "UPGRADE PROBLEM"; then
    echo "    - MongoDB data files need a version upgrade..."
    set +e
    ./bash-tools/upgrade-mongodb.sh
    upgrade_rc=$?
    set -e
    if [ "$upgrade_rc" -ne 0 ]; then
        echo "ERROR: MongoDB data-file upgrade failed."
        exit 1
    fi
    compose up -d mongodb
fi
echo -n "    - Waiting for MongoDB..."
for i in $(seq 1 60); do
    if (echo > /dev/tcp/localhost/27017) 2>/dev/null; then
        break
    fi
    echo -n "."
    sleep 2
    if [ "$i" -eq 60 ]; then
        echo ""
        echo "ERROR: MongoDB port 27017 never opened."
        exit 1
    fi
done

echo ""
echo "    - Waiting for MongoDB to accept auth..."
mongo_ready=0
for i in $(seq 1 60); do
    if docker exec libertea-mongodb mongosh --quiet --username root --password "$PANEL_MONGODB_PASSWORD" --authenticationDatabase admin --eval "db.adminCommand({ ping: 1 })" >/dev/null 2>&1; then
        mongo_ready=1
        break
    fi

    # Mongo is up but has no root user (init was interrupted, then skipped
    # because data/db already existed). Localhost exception can create it.
    if docker exec libertea-mongodb mongosh --quiet --eval "db.adminCommand({ ping: 1 })" >/dev/null 2>&1; then
        echo ""
        echo "    - Creating missing MongoDB root user..."
        docker exec libertea-mongodb mongosh --quiet --eval "
            db.getSiblingDB('admin').createUser({
                user: 'root',
                pwd: '$PANEL_MONGODB_PASSWORD',
                roles: [{ role: 'root', db: 'admin' }]
            })
        " 2>&1 | sed 's/^/        /'
        if docker exec libertea-mongodb mongosh --quiet --username root --password "$PANEL_MONGODB_PASSWORD" --authenticationDatabase admin --eval "db.adminCommand({ ping: 1 })" >/dev/null 2>&1; then
            mongo_ready=1
            echo "    - Root user created successfully."
            break
        fi
    fi

    echo -n "."
    sleep 2
done
if [ "$mongo_ready" -ne 1 ]; then
    echo ""
    echo "ERROR: MongoDB did not become ready in time."
    exit 1
fi
echo ""
echo "    - Starting remaining containers..."
# camouflage-nginx-fallback and rsyslog are the only services not on host
# networking, so they're the only ones whose port docker just released on
# `compose down` above; the docker-proxy for it can take a moment to exit,
# making the first `up` here racy. Retry instead of failing the whole update.
set +e
compose_up_ok=0
for i in $(seq 1 5); do
    if compose up -d $COMPOSE_UP_SERVICES; then
        compose_up_ok=1
        break
    fi
    echo "    - Containers failed to start (a port from the previous run may still be closing), retrying in 3s..."
    sleep 3
done
set -e
if [ "$compose_up_ok" -ne 1 ]; then
    echo "ERROR: Failed to start docker containers after multiple attempts."
    exit 1
fi

mkdir -p ./data/haproxy-lists
touch ./data/haproxy-lists/camouflage-hosts.lst
touch ./data/haproxy-lists/domains.lst
touch ./data/haproxy-lists/valid-panel-endpoints.lst
touch ./data/haproxy-lists/valid-user-endpoints.lst
touch ./data/haproxy-lists/cgnat-enabled.lst

echo " ** Adding auto-update cronjob..."
# create a cronjob to run ./autoupdate.sh on bash and save the output to /tmp/libertea-autoupdate.log
if ! crontab -l | grep -q "autoupdate.sh"; then
    (crontab -l 2>/dev/null; echo "") | crontab -
    (crontab -l 2>/dev/null; echo "0 0 * * * bash $DIR/autoupdate.sh >> /tmp/libertea-autoupdate.log 2>&1") | crontab -
fi

echo " ** Waiting for services to start..."

# check status of the docker containers with name starting with "libertea" (max 30 seconds) and log each one that has been up for at least 5 seconds
containers=$(docker ps --format "{{.Names}}" | grep -E "^libertea")

# move libertea-haproxy to the end of the list
containers=$(echo "$containers" | grep -v "libertea-haproxy")
containers="$containers libertea-haproxy"

start_time=$(date +%s)
for container in $containers; do
    echo -ne "    ⌛ $container\r"
    # check if the container is running and has been up for at least 5 seconds
    while [ "$(docker inspect -f '{{.State.Running}}' "$container")" != "true" ] || \
        [ $(( $(date -d "$(docker inspect -f '{{.State.StartedAt}}' $container)" +%s) - $(date +%s) + 5 )) -gt 0 ]; do
        sleep 1
        if [ $(( $(date +%s) - start_time )) -gt 45 ]; then
            echo "*******************************************************"
            echo "ERROR: Timeout while waiting for $container to start."
            echo "       Please open an issue on https://github.com/VZiChoushaDui/Libertea/issues/new"
            echo "       and include the following information:"
            echo "       - component name: $container"
            echo "       - OS: $(cat /etc/os-release | grep -E "^NAME=" | cut -d "=" -f 2)"
            echo "       - OS version: $(cat /etc/os-release | grep -E "^VERSION_ID=" | cut -d "=" -f 2)"
            echo "       - Docker version: $(docker --version)"
            echo "       Also include the output of the following command:"
            echo "           docker logs $container | tail -n 100"
            echo ""
            exit 1
        fi
    done
    echo "    ✅ $container started"
done

# wait for the panel to start (up to 5 restarts, 15s/30s/45s per attempt)
echo -ne "    ⌛ libertea-panel\r"
MAX_PANEL_TRIES=5
try_count=0
response_code="0"
panel_try_start=$(date +%s)
set +e
response_code="$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:1000/$PANEL_ADMIN_UUID/" 2>/dev/null)"
set -e
while [ "$response_code" != "200" ] && [ "$response_code" != "302" ]; do
    sleep 1
    elapsed_try=$(( $(date +%s) - panel_try_start ))

    if [ $try_count -eq 0 ]; then
        timeout_threshold=15
    elif [ $try_count -eq 1 ]; then
        timeout_threshold=30
    else
        timeout_threshold=45
    fi

    if [ $elapsed_try -gt $timeout_threshold ]; then
        if [ $try_count -lt $MAX_PANEL_TRIES ]; then
            try_count=$(( try_count + 1 ))
            echo "    ❌ libertea-panel failed to start. Retrying ($try_count/$MAX_PANEL_TRIES)..."

            set +e
            pkill -9 -f uwsgi
            systemctl kill libertea-panel.service
            pkill -9 -f uwsgi
            set -e
            systemctl restart libertea-panel.service

            panel_try_start=$(date +%s)
            echo -ne "    ⌛ libertea-panel\r"
        else
            echo "*******************************************************"
            echo "ERROR: Timeout while waiting for panel to start."
            echo "       Please open an issue on https://github.com/VZiChoushaDui/Libertea/issues/new"
            echo "       and include the following information:"
            echo ""
            set +e
            PANEL_LISTENING="True"
            if [ "$(curl --max-time 3 -s -o /dev/null -w "%{http_code}" "http://localhost:1000/" 2>/dev/null)" == "000" ]; then
                PANEL_LISTENING="False"
            fi
            PANEL_ROOT_STATUS_CODE="$(curl --max-time 3 -s -o /dev/null -w "%{http_code}" "http://localhost:1000/" 2>/dev/null)"
            PANEL_ADMIN_STATUS_CODE="$(curl --max-time 3 -s -o /dev/null -w "%{http_code}" "http://localhost:1000/$PANEL_ADMIN_UUID/" 2>/dev/null)"
            echo "       - component name: libertea-panel"
            echo "       - OS: $(cat /etc/os-release | grep -E "^NAME=" | cut -d "=" -f 2)"
            echo "       - OS version: $(cat /etc/os-release | grep -E "^VERSION_ID=" | cut -d "=" -f 2)"
            echo "       - Docker version: $(docker --version)"
            echo "       - Panel listening: $PANEL_LISTENING"
            echo "       - Panel root status code: $PANEL_ROOT_STATUS_CODE"
            echo "       - Panel admin status code: $PANEL_ADMIN_STATUS_CODE"
            echo "       Also include the output of the following command:"
            echo "           tail -n 100 /tmp/libertea-panel.log"
            echo ""
            exit 1
        fi
    fi

    set +e
    response_code="$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:1000/$PANEL_ADMIN_UUID/" 2>/dev/null)"
    set -e
done
echo "    ✅ libertea-panel started"


if [ "$PANEL_DOMAIN" != "$my_ip" ]; then
echo " ** Checking domain configuration..."
while true; do
    status=""
    set +e
    status=$(curl -k -s --max-time 5 -o /dev/null -w "%{http_code}" "https://$PANEL_DOMAIN/$PANEL_ADMIN_UUID/" 2>/dev/null)
    set -e
    if [ "$status" != "401" ]; then
        # Check if it's a redirect loop (due to Cloudflare SSL not being set to Full)
        if [ "$status" == "301" ] || [ "$status" == "302" ]; then
            echo "*******************************************************"
            echo "ERROR: Your panel domain $PANEL_DOMAIN is redirecting to itself."
            echo "       Please make sure that your CDN's SSL/TLS encryption mode is set to Full."
            echo ""
        else
            echo "*******************************************************"
            echo "ERROR: Your panel domain $PANEL_DOMAIN is not accessible."
            echo "       Please make sure that your domain DNS is pointing to the server IP ($my_ip)."
            echo ""
        fi
        echo " After you have fixed the issue, visit the following URLs to continue:"
        echo "     Panel addresses:"
        echo "       https://$PANEL_DOMAIN/$PANEL_ADMIN_UUID/"
        echo "       https://$my_ip/$PANEL_ADMIN_UUID/"
        echo "    "
        echo "     Username: admin"
        echo "     Password: $PANEL_ADMIN_PASSWORD"
        echo ""
        echo "Will retry in 10 seconds..."
        sleep 10
    else
        break
    fi
done
fi

panel_ip=$(dig +short "$PANEL_DOMAIN" | head -n 1)
panel_ip=$(echo "$panel_ip" | tr -d '[:space:]')

echo ""
echo ""
echo " Installation completed."
echo " Please visit panel to configure your VPN."
echo ""
echo " Panel addresses:"
echo "   https://$PANEL_DOMAIN/$PANEL_ADMIN_UUID/"
echo "   https://$my_ip/$PANEL_ADMIN_UUID/"
echo ""
echo " Username: admin"
echo " Password: $PANEL_ADMIN_PASSWORD"
echo ""
if [ "$panel_ip" == "$my_ip" ]; then
    echo ""
    echo "WARNING: Your panel domain name is not resolved through CDN."
    echo "         If you want to use CDN, make sure that it is enabled for your domain (orange cloud icon in Cloudflare)."
    echo ""
fi
