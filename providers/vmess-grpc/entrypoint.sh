#!/bin/sh

if [ -z "$OUTBOUND_PORT" ]; then
    OUTBOUND_PORT="2999"
fi

jq --argjson port $OUTBOUND_PORT '.outbounds[0].settings.servers[0].port = $port' /etc/xray/config.json > /etc/xray/config.tmp.json 

cat /etc/xray/config.tmp.json

# run xray
echo " ** Starting Xray..."
/usr/bin/xray -config /etc/xray/config.tmp.json