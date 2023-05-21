#!/bin/bash

TARGET_IP="$1"
TARGET_PORT="$2"
TARGET_USER="$3"

CONNECTIONS_COUNT=4

DIR="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
cd "$DIR"

# Install CONNECTIONS_COUNT variants of systemd service

for i in $(seq 1 $CONNECTIONS_COUNT); do
    LOCALPORT=$((10000 + $i))

    cp template.service /etc/systemd/system/libertea-proxy-ssh-tunnel-$i.service

    sed -i "s/LOCALPORT/$LOCALPORT/g" /etc/systemd/system/libertea-proxy-ssh-tunnel-$i.service
    sed -i "s/TARGETIP/$TARGET_IP/g" /etc/systemd/system/libertea-proxy-ssh-tunnel-$i.service
    sed -i "s/TARGETPORT/$TARGET_PORT/g" /etc/systemd/system/libertea-proxy-ssh-tunnel-$i.service
    sed -i "s/TARGETUSER/$TARGET_USER/g" /etc/systemd/system/libertea-proxy-ssh-tunnel-$i.service
    
    systemctl daemon-reload
    systemctl enable libertea-proxy-ssh-tunnel-$i.service
    systemctl restart libertea-proxy-ssh-tunnel-$i.service
done
