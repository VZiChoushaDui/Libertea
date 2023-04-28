#!/bin/bash

set -e

# if not elevated, elevate
if [ "$EUID" -ne 0 ]; then
    sudo "$0" "$@"
    exit
fi

COMMAND="$1"

DIR="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
cd "$DIR"

# if .libertea.proxy file exists, then this is a proxy server. don't install main
if [ -f .libertea.proxy ]; then
    echo "This is a Libertea proxy server. You can't install both main and proxy on the same server."
    exit 1
fi

touch .libertea.main
export DEBIAN_FRONTEND=noninteractive

echo " ** Installing dependencies..."
apt-get update >/dev/null

# if ! command -v certbot &> /dev/null; then
#     echo "    - Installing certbot..."
#     if [ "$(lsb_release -rs)" == "20.04" ]; then
#         # if ubuntu version is 20.04, add certbot repository
#         add-apt-repository -y ppa:certbot/certbot > /dev/null
#     fi
#     apt-get update > /dev/null
#     apt-get install -qq -y certbot > /dev/null
# fi

if ! command -v ufw &> /dev/null; then
    echo "    - Installing ufw..."
    apt-get install -qq -y ufw >/dev/null
fi

if ! command -v sed &> /dev/null; then
    echo "    - Installing sed..."
    apt-get install -qq -y sed >/dev/null
fi

if ! command -v dig &> /dev/null; then
    echo "    - Installing dnsutils..."
    apt-get install -qq -y dnsutils >/dev/null
fi

if ! command -v uuidgen &> /dev/null; then
    echo "    - Installing uuidgen..."
    apt-get install -qq -y uuid-runtime >/dev/null
fi

if ! command -v openssl &> /dev/null; then
    echo "    - Installing openssl..."
    apt-get install -qq -y openssl >/dev/null
fi

if ! command -v jq &> /dev/null; then
    echo "    - Installing jq..."
    apt-get install -qq -y jq >/dev/null
fi

if ! command -v cut &> /dev/null; then
    echo "    - Installing coreutils..."
    apt-get install -qq -y coreutils >/dev/null
fi

echo "    - Installing build tools..."
apt-get install -qq -y build-essential >/dev/null

echo "    - Installing python..."
if ! command -v python3 &> /dev/null; then
    apt-get install -qq -y python3 >/dev/null
fi
apt-get install -qq -y python3-dev >/dev/null
if ! command -v pip3 &> /dev/null; then
    apt-get install -qq -y python3-pip >/dev/null
fi

echo "    - Installing python dependencies..."
pip3 install -r panel/requirements.txt | sed 's/^/        /'

echo "    - Installing docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sh /tmp/get-docker.sh | sed 's/^/        /' >/dev/null
fi
echo "    - Installing docker compose..."
apt-get install -qq docker-compose-plugin | sed 's/^/        /'

# if docker version is 23.x, apply apparmor fix: https://stackoverflow.com/q/75346313
if [[ $(docker --version | cut -d ' ' -f 3 | cut -d '.' -f 1) == "23" ]]; then
    echo "    - Applying apparmor fix..."
    apt-get install -qq -y apparmor apparmor-utils >/dev/null
    service docker restart
fi

echo " ** Initializing firewall..."
ufw allow ssh >/dev/null
ufw allow http >/dev/null
ufw allow https >/dev/null
yes | ufw enable >/dev/null

# check if cpu supports avx2, or true
if [[ ! $(grep avx2 /proc/cpuinfo) ]]; then 
    echo " ** Your CPU does not support AVX2, Libertea will run in compatibility mode."
    echo "    Please consider upgrading your CPU to support AVX2."
    # change docker-compose.yml to use compatibility image
    sed -i "s|image: mongo:latest|image: mongo:4.4|g" docker-compose.yml
fi

echo " ** Getting public IP..."
set +e
my_ip=$(curl -s --max-time 3 https://ifconfig.io/ip)
if [[ ! $my_ip ]]; then
    my_ip=$(curl -s --max-time 3 https://api.ipify.org)
fi
if [[ ! $my_ip ]]; then
    my_ip=$(curl -s --max-time 3 https://icanhazip.com)
fi
if [[ ! $my_ip ]]; then
    my_ip=$(curl -s --max-time 3 https://ident.me)
fi
if [[ ! $my_ip ]]; then
    my_ip=$(curl -s --max-time 3 https://checkip.amazonaws.com)
fi
if [[ ! $my_ip ]]; then
    echo " ** Failed to get public IP. Please check your internet connection."
    exit 1
fi
set -e


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

# if [ ! -f tools/flarectl ]; then
#     echo " ** Installing flarectl..."
#     mkdir tools
#     wget https://github.com/cloudflare/cloudflare-go/releases/download/v0.58.0/flarectl_0.58.0_linux_amd64.tar.xz -O tools/flarectl.tar.xz >/dev/null 2>&1
#     tar -xf tools/flarectl.tar.xz -C tools >/dev/null
#     rm tools/flarectl.tar.xz
#     chmod +x tools/flarectl
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
echo " ** Generating self-signed certificate..."
mkdir -p data/certs/selfsigned
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout data/certs/selfsigned/privkey.pem \
    -out data/certs/selfsigned/cert.pem \
    -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.google.com" 2>/dev/null
cat data/certs/selfsigned/privkey.pem data/certs/selfsigned/cert.pem > data/certs/selfsigned/fullchain.pem
mkdir -p /etc/ssl/ha-certs
cp data/certs/selfsigned/fullchain.pem /etc/ssl/ha-certs/selfsigned.pem

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


echo " ** Installing web panel..."
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

if [ "$ENVIRONMENT" == "dev" ]; then
    echo " ** Building docker containers..."
    docker compose -f docker-compose.dev.yml build

    echo " ** Starting docker containers..."
    set +e
    docker compose -f docker-compose.dev.yml down >/dev/null
    set -e
    docker compose -f docker-compose.dev.yml up -d
else
    echo " ** Pulling docker containers..."
    docker compose pull
    docker compose build

    echo " ** Starting docker containers..."
    set +e
    docker compose down >/dev/null
    set -e
    docker compose up -d
fi

touch ./data/haproxy-lists/camouflage-hosts.lst
touch ./data/haproxy-lists/domains.lst
touch ./data/haproxy-lists/valid-panel-endpoints.lst
touch ./data/haproxy-lists/valid-user-endpoints.lst

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

# wait for the panel to start 
echo -ne "    ⌛ libertea-panel\r"
try_count=0
while [ "$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:1000/$PANEL_ADMIN_UUID/" 2>/dev/null)" != "200" ]; do
    sleep 1
    if [ $(($try_count)) -eq 0 ] && [ $(( $(date +%s) - start_time )) -gt 45 ]; then
        echo "    ❌ libertea-panel failed to start. Retrying..."
        try_count=1

        # restart the panel
        set +e
        pkill -9 -f uwsgi
        systemctl kill libertea-panel.service
        pkill -9 -f uwsgi
        set -e
        systemctl restart libertea-panel.service

        echo -ne "    ⌛ libertea-panel\r"
    fi

    if [ $(($try_count)) -gt 0 ] && [ $(( $(date +%s) - start_time )) -gt 100 ]; then
        echo "*******************************************************"
        echo "ERROR: Timeout while waiting for panel to start."
        echo "       Please open an issue on https://github.com/VZiChoushaDui/Libertea/issues/new"
        echo "       and include the following information:"
        echo ""
        
        PANEL_LISTENING="True"
        PANEL_ROOT_STATUS_CODE=""
        PANEL_ADMIN_STATUS_CODE=""
        if [ "$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:1000/" 2>/dev/null)" == "000" ]; then
            # check if localhost:1000 is open at all or it's refusing connections
            PANEL_LISTENING="False"
        fi
        PANEL_ROOT_STATUS_CODE="$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:1000/" 2>/dev/null)"
        PANEL_ADMIN_STATUS_CODE="$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:1000/$PANEL_ADMIN_UUID/" 2>/dev/null)"

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
done
echo "    ✅ libertea-panel started"

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
    echo "         Please make sure that CDN is enabled for your domain (orange cloud icon in Cloudflare)."
    echo ""
fi

