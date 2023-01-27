#!/bin/bash

# set CAMOUFLAGE_HOST variable to the first line of /haproxy-files/lists/camouflage-hosts.lst
export CAMOUFLAGE_HOST=$(head -n 1 /haproxy-files/lists/camouflage-hosts.lst | xargs echo -n)
export CAMOUFLAGE_PORT="443"

if [ -z "$CAMOUFLAGE_HOST" ]; then
    export CAMOUFLAGE_HOST="127.0.0.1"
    export CAMOUFLAGE_PORT="11111"
fi

pidfile=/var/run/haproxy.pid

function reload
{
    echo "Reloading haproxy..."
    
    export CAMOUFLAGE_HOST=$(head -n 1 /haproxy-files/lists/camouflage-hosts.lst | xargs echo -n)
    export CAMOUFLAGE_PORT="443"

    if [ -z "$CAMOUFLAGE_HOST" ]; then
        export CAMOUFLAGE_HOST="127.0.0.1"
        export CAMOUFLAGE_PORT="11111"
    fi

    haproxy -W -db -f /usr/local/etc/haproxy/haproxy.cfg -p $pidfile -sf $(cat $pidfile) &
    wait
}


trap reload SIGHUP
trap "kill -TERM $(cat $pidfile) || exit 1" SIGTERM SIGINT
haproxy -W -db -f /usr/local/etc/haproxy/haproxy.cfg -p $pidfile &
wait
