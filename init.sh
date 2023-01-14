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

echo " ** Initializing firewall..."
ufw allow ssh >/dev/null
ufw allow http >/dev/null
ufw allow https >/dev/null
yes | ufw enable >/dev/null

my_ip=$(curl -s https://api.ipify.org)

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
    echo "To get started, you need a domain name configured on a CDN (e.g. CloudFlare) and configured to point to $my_ip"
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

echo " ** Installing dependencies..."
apt-get update >/dev/null


# if ! command -v certbot &> /dev/null; then
#     echo "    - Installing certbot..."
#     if [ "$(lsb_release -rs)" == "20.04" ]; then
#         # if ubuntu version is lower than 22.04, add certbot repository
#         add-apt-repository -y ppa:certbot/certbot > /dev/null
#     fi
#     sudo apt-get update > /dev/null
#     sudo apt-get install -qq -y certbot > /dev/null
# fi


if ! command -v openssl &> /dev/null; then
    echo "    - Installing openssl..."
    apt-get install -qq -y openssl >/dev/null
fi

if ! command -v jq &> /dev/null; then
    echo "    - Installing jq..."
    apt-get install -qq -y jq >/dev/null
fi

echo "    - Installing python..."
if ! command -v python3 &> /dev/null; then
    apt-get install -qq -y python3 >/dev/null
fi
if ! command -v pip3 &> /dev/null; then
    apt-get install -qq -y python3-pip >/dev/null
fi

echo "    - Installing python dependencies..."
pip3 install -r panel/requirements.txt >/dev/null

echo "    - Installing docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sh /tmp/get-docker.sh >/dev/null
fi
echo " ** Installing docker compose..."
apt-get install -qq docker-compose-plugin >/dev/null

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
echo "    - vless-ws..."
./providers/vless-ws/init.sh 2002 12002 "$CONN_VLESS_WS_URL" "$CONN_VLESS_WS_AUTH_UUID"

echo " ** Installing web panel..."
cp panel/libertea-panel.service /etc/systemd/system/
# replace {rootpath} with the path to the root of the project
sed -i "s|{rootpath}|$DIR|g" /etc/systemd/system/libertea-panel.service
systemctl enable libertea-panel.service
systemctl restart libertea-panel.service

echo " ** Building docker containers..."
docker compose build

echo " ** Starting docker containers..."
docker compose down >/dev/null
docker compose up -d

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
