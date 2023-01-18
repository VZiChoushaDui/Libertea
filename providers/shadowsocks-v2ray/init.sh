#!/bin/bash

DIR="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
cd "$DIR"

if [ -f config.env ]; then
    rm config.env
fi

PORT="$1"
URL="$2"
PASSWORD="$3"

if [ -z "$PORT" ] || [ -z "$URL" ] || [ -z "$PASSWORD" ]; then
    echo "Usage: $0 <port> <url> <password>"
    exit 1
fi

# Create config.json from config.json.sample
cp config.env.sample config.env
sed -i "s|{port}|$PORT|g" config.env
sed -i "s|{url}|$URL|g" config.env
sed -i "s|{password}|$PASSWORD|g" config.env
