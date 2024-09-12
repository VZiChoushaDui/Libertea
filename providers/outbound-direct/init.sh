#!/bin/bash

DIR="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
cd "$DIR"

if [ -f config.json ]; then
    rm config.json
fi

PORT="$1"

if [ -z "$PORT" ]; then
    echo "Usage: $0 <port>"
    exit 1
fi

# Create config.json from config.json.sample
cp config.json.sample config.json
sed -i "s|{port}|$PORT|g" config.json
