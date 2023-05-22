#!/bin/bash

TARGET_IP="$1"
TARGET_PORT="$2"
TARGET_USER="$3"
LOCAL_PORT_START="$4"
CONNECTIONS_COUNT="$5"
SERVICE_POSTFIX="$6"

DIR="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
cd "$DIR"

# Install CONNECTIONS_COUNT variants of systemd service

for i in $(seq 0 $(($CONNECTIONS_COUNT - 1))); do
    LOCALPORT=$(($LOCAL_PORT_START + $i))

    cp template.service /etc/systemd/system/libertea-proxy-ssh-tunnel-$i.service

    sed -i "s/LOCALPORT/$LOCALPORT/g" /etc/systemd/system/libertea-proxy-ssh-tunnel-$i$SERVICE_POSTFIX.service
    sed -i "s/TARGETIP/$TARGET_IP/g" /etc/systemd/system/libertea-proxy-ssh-tunnel-$i$SERVICE_POSTFIX.service
    sed -i "s/TARGETPORT/$TARGET_PORT/g" /etc/systemd/system/libertea-proxy-ssh-tunnel-$i$SERVICE_POSTFIX.service
    sed -i "s/TARGETUSER/$TARGET_USER/g" /etc/systemd/system/libertea-proxy-ssh-tunnel-$i$SERVICE_POSTFIX.service
    
    systemctl daemon-reload
    systemctl enable libertea-proxy-ssh-tunnel-$i$SERVICE_POSTFIX.service
    systemctl restart libertea-proxy-ssh-tunnel-$i$SERVICE_POSTFIX.service
done
