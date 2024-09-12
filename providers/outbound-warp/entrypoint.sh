#!/bin/sh

if [ -z "$FIREWALL_OUTBOUND_TCP_PORTS" ]; then
    FIREWALL_OUTBOUND_TCP_PORTS="0-65535"
fi
if [ -z "$FIREWALL_OUTBOUND_UDP_PORTS" ]; then
    FIREWALL_OUTBOUND_UDP_PORTS="0-65535"
fi
if [ -z "$FIREWALL_BITTORRENT_ENABLE" ]; then
    FIREWALL_BITTORRENT_ENABLE="false"
fi

FIREWALL_OUTBOUND_TCP_PORTS=$(echo $FIREWALL_OUTBOUND_TCP_PORTS | tr ' ' ',' | tr ':' '-')
FIREWALL_OUTBOUND_UDP_PORTS=$(echo $FIREWALL_OUTBOUND_UDP_PORTS | tr ' ' ',' | tr ':' '-')

cp /etc/xray/config.json /etc/xray/config.tmp.json

# Change config.json based on environment variables FIREWALL_OUTBOUND_TCP_PORTS and FIREWALL_OUTBOUND_UDP_PORTS
jq --arg ports "$FIREWALL_OUTBOUND_TCP_PORTS" '.routing.rules[0].port = $ports' /etc/xray/config.tmp.json > /etc/xray/config.tmp2.json && mv -f /etc/xray/config.tmp2.json /etc/xray/config.tmp.json
jq --arg ports "$FIREWALL_OUTBOUND_UDP_PORTS" '.routing.rules[1].port = $ports' /etc/xray/config.tmp.json > /etc/xray/config.tmp2.json && mv -f /etc/xray/config.tmp2.json /etc/xray/config.tmp.json

if [ "$FIREWALL_BITTORRENT_ENABLE" == "true" ]; then
    jq --arg tag "web" '.routing.rules[2].outboundTag = $tag' /etc/xray/config.tmp.json > /etc/xray/config.tmp.json
else
    jq --arg tag "block" '.routing.rules[2].outboundTag = $tag' /etc/xray/config.tmp.json > /etc/xray/config.tmp2.json && mv -f /etc/xray/config.tmp2.json /etc/xray/config.tmp.json
fi

cat /etc/xray/config.tmp.json

# run xray
echo " ** Starting Xray..."
/usr/bin/xray -config /etc/xray/config.tmp.json
