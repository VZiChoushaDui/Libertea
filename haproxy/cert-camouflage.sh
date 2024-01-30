#!/bin/bash

set -e

CAMOUFLAGE_DOMAIN="$1"

if [ -z "$CAMOUFLAGE_DOMAIN" ]; then
    echo "Usage: $0 <domain>"
    exit 1
fi

TEMP_DIR="/tmp/libertea-$(date +%s)"
mkdir -p "$TEMP_DIR"
cd "$TEMP_DIR"

echo "Generating generic self-signed certificate... (fallback)"
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ./generic-privkey.pem \
    -out ./generic-cert.pem \
    -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" 2>/dev/null
cat ./generic-privkey.pem ./generic-cert.pem > ./fullchain.pem
mkdir -p /etc/ssl/ha-certs
cp ./fullchain.pem /etc/ssl/ha-certs/selfsigned.pem

echo "Fetching certificate for $CAMOUFLAGE_DOMAIN..."
openssl s_client -showcerts -connect $CAMOUFLAGE_DOMAIN:443 </dev/null 2>/dev/null | openssl x509 -outform PEM > $CAMOUFLAGE_DOMAIN.cert
SUBJECT=$(openssl x509 -in $CAMOUFLAGE_DOMAIN.cert -noout -subject -nameopt compat | sed 's/^subject=//g')
ISSUER=$(openssl x509 -in $CAMOUFLAGE_DOMAIN.cert -noout -issuer -nameopt compat | sed 's/^issuer=//g')

echo "Generating self-signed certificate for $CAMOUFLAGE_DOMAIN..."
openssl ecparam -out issuer.key -name prime256v1 -genkey
openssl req -new -sha256 -key issuer.key -out issuer.csr -subj "$ISSUER"
openssl x509 -req -sha256 -days 365 -in issuer.csr -signkey issuer.key -out issuer.crt

openssl ecparam -out privkey.pem -name prime256v1 -genkey
openssl req -new -sha256 -key privkey.pem -out cert.csr -subj "$SUBJECT"
openssl x509 -req -in cert.csr -CA  issuer.crt -CAkey issuer.key -CAcreateserial -out cert.pem -days 90 -sha256

cat privkey.pem cert.pem > fullchain.pem

rm /etc/ssl/ha-certs/selfsigned.pem
cp fullchain.pem /etc/ssl/ha-certs/selfsigned.pem
