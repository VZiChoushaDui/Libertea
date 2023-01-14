#!/bin/bash

set -e

function get_cert() {
    domain="$1"

    echo "Requesting certificate for $domain"

    random_email="$(openssl rand -hex 16)@hotmail.com"

    sudo certbot certonly --standalone --agree-tos --no-eff-email -m "$random_email" \
        --non-interactive --http-01-port=8987 --preferred-challenges tls-sni \
        -d "$domain"

    sudo cat "/etc/letsencrypt/live/$domain/fullchain.pem" \
        "/etc/letsencrypt/live/$domain/privkey.pem" \
        | sudo tee "/etc/ssl/ha-certs/$domain.pem"
}

DIR="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

while IFS= read -r line; do

    if [[ $line =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        echo "Skipping $line because it is an ip address"
        continue
    fi

    get_cert "$line"

done < "$DIR/../data/haproxy-lists/domains.lst"

docker kill -s HUP libertea-haproxy
