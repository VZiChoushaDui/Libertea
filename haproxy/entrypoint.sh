#!/bin/bash

export SOCKS_OUTBOUND_PORT=$(head -n 1 /haproxy-files/lists/socks-outbound-port.lst | xargs echo -n)
if [ -z "$SOCKS_OUTBOUND_PORT" ]; then
    export SOCKS_OUTBOUND_PORT="2998"
fi

export CAMOUFLAGE_PORT=$(head -n 1 /haproxy-files/lists/camouflage-port.lst | xargs echo -n)
if [ -z "$CAMOUFLAGE_PORT" ]; then
    export CAMOUFLAGE_PORT="443"
fi

export CAMOUFLAGE_HOST=$(head -n 1 /haproxy-files/lists/camouflage-hosts.lst | xargs echo -n)
if [ -z "$CAMOUFLAGE_HOST" ]; then
    export CAMOUFLAGE_HOST="127.0.0.1"
    export CAMOUFLAGE_PORT="25898"
fi

export CAMOUFLAGE_IP="127.0.0.1"
export CAMOUFLAGE_OVERRIDE_HOST=true
if [[ $CAMOUFLAGE_HOST =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    export CAMOUFLAGE_IP=$CAMOUFLAGE_HOST
    export CAMOUFLAGE_OVERRIDE_HOST=false
else
    ip=$(dig +short $CAMOUFLAGE_HOST A | head -n 1)
    if [ -z "$ip" ]; then
        echo "Could not resolve $CAMOUFLAGE_HOST"
        export CAMOUFLAGE_IP="127.0.0.1"
        export CAMOUFLAGE_PORT="25898"
    else
        echo "Resolved $CAMOUFLAGE_HOST to $ip"
        export CAMOUFLAGE_IP="$ip"
    fi
fi
if [ "$CAMOUFLAGE_IP" == "localhost" ]; then
    export CAMOUFLAGE_OVERRIDE_HOST=false
fi

pidfile=/var/run/haproxy.pid

function reload
{
    echo "Reloading haproxy..."

    export SOCKS_OUTBOUND_PORT=$(head -n 1 /haproxy-files/lists/socks-outbound-port.lst | xargs echo -n)
    if [ -z "$SOCKS_OUTBOUND_PORT" ]; then
        export SOCKS_OUTBOUND_PORT="2998"
    fi

    export CAMOUFLAGE_PORT=$(head -n 1 /haproxy-files/lists/camouflage-port.lst | xargs echo -n)
    if [ -z "$CAMOUFLAGE_PORT" ]; then
        export CAMOUFLAGE_PORT="443"
    fi

    export CAMOUFLAGE_HOST=$(head -n 1 /haproxy-files/lists/camouflage-hosts.lst | xargs echo -n)
    if [ -z "$CAMOUFLAGE_HOST" ]; then
        export CAMOUFLAGE_HOST="127.0.0.1"
        export CAMOUFLAGE_PORT="25898"
    fi

    export CAMOUFLAGE_IP="127.0.0.1"
    export CAMOUFLAGE_OVERRIDE_HOST=true
    if [[ $CAMOUFLAGE_HOST =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        export CAMOUFLAGE_IP=$CAMOUFLAGE_HOST
        export CAMOUFLAGE_OVERRIDE_HOST=false
    else
        ip=$(dig +short $CAMOUFLAGE_HOST A | head -n 1)
        if [ -z "$ip" ]; then
            echo "Could not resolve $CAMOUFLAGE_HOST"
            export CAMOUFLAGE_IP="127.0.0.1"
            export CAMOUFLAGE_PORT="25898"
        else
            echo "Resolved $CAMOUFLAGE_HOST to $ip"
            export CAMOUFLAGE_IP="$ip"
        fi
    fi
    if [ "$CAMOUFLAGE_HOST" == "localhost" ]; then
        export CAMOUFLAGE_OVERRIDE_HOST=false
    fi

    # haproxy -W -db -f /usr/local/etc/haproxy/haproxy.cfg -p $pidfile -sf $(cat $pidfile) &

    date
    echo "Killing haproxy..."
    killall haproxy

    echo "Starting haproxy..."
    echo "  CAMOUFLAGE_HOST: $CAMOUFLAGE_HOST"
    echo "  CAMOUFLAGE_IP: $CAMOUFLAGE_IP"
    echo "  CAMOUFLAGE_PORT: $CAMOUFLAGE_PORT"
    echo "  CAMOUFLAGE_OVERRIDE_HOST: $CAMOUFLAGE_OVERRIDE_HOST"

    haproxy -W -db -f /usr/local/etc/haproxy/haproxy.cfg -p $pidfile &

    wait
}

date
echo "Starting haproxy..."
echo "  CAMOUFLAGE_HOST: $CAMOUFLAGE_HOST"
echo "  CAMOUFLAGE_IP: $CAMOUFLAGE_IP"
echo "  CAMOUFLAGE_PORT: $CAMOUFLAGE_PORT"
echo "  CAMOUFLAGE_OVERRIDE_HOST: $CAMOUFLAGE_OVERRIDE_HOST"

trap reload SIGHUP
trap "kill -TERM $(cat $pidfile) || exit 1" SIGTERM SIGINT
haproxy -W -db -f /usr/local/etc/haproxy/haproxy.cfg -p $pidfile &
wait
