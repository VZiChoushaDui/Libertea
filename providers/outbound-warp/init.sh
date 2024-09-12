#!/bin/bash

DIR="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
cd "$DIR"

if [ -f config.json ]; then
    rm config.json
fi

PORT="$1"
ENDPOINT="$2" 
PRIVATE_KEY="$3"
ADDRESSES="$4"
PUBLIC_KEY="$5"
MTU="$6"

if [ -z "$PORT" ] || [ -z "$ENDPOINT" ] || [ -z "$PRIVATE_KEY" ] || [ -z "$ADDRESSES" ] || [ -z "$PUBLIC_KEY" ] || [ -z "$MTU" ]; then
    echo "Usage: $0 <port> <endpoint> <private_key> <addresses> <public_key> <mtu>"
    exit 1
fi

# Create config.json from config.json.sample
cp config.json.sample config.json
sed -i "s|{port}|$PORT|g" config.json
sed -i "s|{endpoint}|$ENDPOINT|g" config.json
sed -i "s|{private_key}|$PRIVATE_KEY|g" config.json
sed -i "s|{addresses}|$ADDRESSES|g" config.json
sed -i "s|{public_key}|$PUBLIC_KEY|g" config.json
sed -i "s|{mtu}|$MTU|g" config.json
