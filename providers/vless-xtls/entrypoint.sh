#!/bin/sh

# disable all outbound connections except common ones, to prevent abuse
echo " ** Setting up outbound firewall..."

# get docker interface name
DOCKER_INTERFACE=$(ip route | grep default | awk '{print $5}') 
echo " ** Docker interface: $DOCKER_INTERFACE"

# NOTE: -I adds the rule to the top of the chain

# drop all outbound connections (tcp udp) 
iptables -I OUTPUT -o $DOCKER_INTERFACE -p tcp --dport 0:16384 -j DROP
iptables -I OUTPUT -o $DOCKER_INTERFACE -p udp --dport 0:16384 -j DROP
# iptables -I OUTPUT -o $DOCKER_INTERFACE -p tcp -j LOG --log-prefix "XRAY DROPPED: " --log-level 6
# iptables -I OUTPUT -o $DOCKER_INTERFACE -p udp -j LOG --log-prefix "XRAY DROPPED: " --log-level 6

# except established connections and allowed ports
iptables -I OUTPUT -o $DOCKER_INTERFACE -m state --state ESTABLISHED,RELATED -j ACCEPT

for port in $(echo $FIREWALL_OUTBOUND_TCP_PORTS | tr "," "

"); do
    iptables -I OUTPUT -o $DOCKER_INTERFACE -p tcp --dport $port -j ACCEPT
    echo "    - TCP port $port"
done
for port in $(echo $FIREWALL_OUTBOUND_UDP_PORTS | tr "," "

"); do
    iptables -I OUTPUT -o $DOCKER_INTERFACE -p udp --dport $port -j ACCEPT
    echo "    - UDP port $port"
done


# run xray
echo " ** Starting Xray..."
/usr/bin/xray -config /etc/xray/config.json
