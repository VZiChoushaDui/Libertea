#!/bin/bash

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
if [[ $CAMOUFLAGE_HOST =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    export CAMOUFLAGE_IP=$CAMOUFLAGE_HOST
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

pidfile=/var/run/haproxy.pid

function reload
{
    echo "Reloading haproxy..."
    
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
    if [[ $CAMOUFLAGE_HOST =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        export CAMOUFLAGE_IP=$CAMOUFLAGE_HOST
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

    # haproxy -W -db -f /usr/local/etc/haproxy/haproxy.cfg -p $pidfile -sf $(cat $pidfile) &

    echo "  Killing haproxy..."
    killall haproxy
    echo "  Starting haproxy..."
    haproxy -W -db -f /usr/local/etc/haproxy/haproxy.cfg -p $pidfile &

    wait
}


trap reload SIGHUP
trap "kill -TERM $(cat $pidfile) || exit 1" SIGTERM SIGINT
haproxy -W -db -f /usr/local/etc/haproxy/haproxy.cfg -p $pidfile &
wait
