#!/bin/bash

DIR="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
cd "$DIR"

if [ -f config.json ]; then
    rm config.json
fi

PORT="$1"
PORT_INTERNAL="$2"
URL="$3"
PASSWORD="$4"

if [ -z "$PORT" ] || [ -z "$PORT_INTERNAL" ] || [ -z "$URL" ] || [ -z "$PASSWORD" ]; then
    echo "Usage: $0 <port> <port_internal> <url> <password>"
    exit 1
fi

# Create config.json from config.json.sample
cp config.json.sample config.json
sed -i "s|{port}|$PORT|g" config.json
sed -i "s|{port-internal}|$PORT_INTERNAL|g" config.json
sed -i "s|{url}|$URL|g" config.json
sed -i "s|{password}|$PASSWORD|g" config.json
