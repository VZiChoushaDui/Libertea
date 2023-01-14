#!/bin/sh

# disable all outbound connections except common ones, to prevent abuse
echo " ** Setting up outbound firewall..."

# get docker interface name
DOCKER_INTERFACE=$(ip route | grep default | awk '{print $5}') 
echo " ** Docker interface: $DOCKER_INTERFACE"

# NOTE: -I adds the rule to the top of the chain

# drop all outbound connections (tcp udp) 
iptables -I OUTPUT -o $DOCKER_INTERFACE -p tcp -j DROP
iptables -I OUTPUT -o $DOCKER_INTERFACE -p udp -j DROP

# iptables -I OUTPUT -o $DOCKER_INTERFACE -p tcp -j LOG --log-prefix "XRAY DROPPED: " --log-level 6
# iptables -I OUTPUT -o $DOCKER_INTERFACE -p udp -j LOG --log-prefix "XRAY DROPPED: " --log-level 6

# except these ports:
iptables -I OUTPUT -o $DOCKER_INTERFACE -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -I OUTPUT -o $DOCKER_INTERFACE -p tcp --dport 22 -j ACCEPT # ssh
iptables -I OUTPUT -o $DOCKER_INTERFACE -p tcp --dport 53 -j ACCEPT # dns
iptables -I OUTPUT -o $DOCKER_INTERFACE -p udp --dport 53 -j ACCEPT # dns
iptables -I OUTPUT -o $DOCKER_INTERFACE -p tcp --dport 80 -j ACCEPT # http
iptables -I OUTPUT -o $DOCKER_INTERFACE -p tcp --dport 8080 -j ACCEPT # http
iptables -I OUTPUT -o $DOCKER_INTERFACE -p tcp --dport 443 -j ACCEPT # https
iptables -I OUTPUT -o $DOCKER_INTERFACE -p tcp --dport 8443 -j ACCEPT # https
iptables -I OUTPUT -o $DOCKER_INTERFACE -p udp --dport 123 -j ACCEPT # ntp
iptables -I OUTPUT -o $DOCKER_INTERFACE -p tcp --dport 3389 -j ACCEPT # rdp

# run xray
echo " ** Starting Xray..."
/usr/bin/xray -config /etc/xray/config.json
