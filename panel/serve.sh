#!/bin/bash

LOG_MAX_SIZE_MB=100
UWSGI_THREADS=6
PORT=1000

function log {
    cur_date=$(date +"%Y-%m-%d %H:%M:%S")
    echo "[$cur_date] $1"
    echo "[$cur_date] $1" >> /tmp/libertea-panel.log
    echo "[$cur_date] $1" >> /tmp/libertea-panel.init.log
}

log "Libertea panel serve script"

dir=$(pwd)
log "Current directory: $dir"

# check if /tmp/libertea-panel.log is bigger than LOG_MAX_SIZE_MB, if so, remove it
if [ -f /tmp/libertea-panel.log ]; then
    log_size=$(du -m /tmp/libertea-panel.log | cut -f1)
    if [ $log_size -gt $LOG_MAX_SIZE_MB ]; then
        log "Removing /tmp/libertea-panel.log"
        rm /tmp/libertea-panel.log
        log "Removed /tmp/libertea-panel.log because it was bigger than $LOG_MAX_SIZE_MB MB"
    fi
fi

log "Checking net.core.somaxconn value" 
SOMAXCONN=100
SOMAXCONN=$(sysctl -n net.core.somaxconn)
log "  net.core.somaxconn value is $SOMAXCONN"
if ! [[ $SOMAXCONN =~ ^[0-9]+$ ]]; then
    SOMAXCONN=100
fi
if [ $SOMAXCONN -gt 512 ]; then
    SOMAXCONN=512
else
    SOMAXCONN=$(($SOMAXCONN - 1))
fi

log "Checking total memory"
TOTAL_MEM=$(free -m | grep Mem | awk '{print $2}')
if [ $TOTAL_MEM -gt 3000 ]; then
    log "Total memory is greater than 3000 MB, setting uwsgi threads to 10"
    UWSGI_THREADS=10
fi

log "Starting Libertea panel via uwsgi on port $PORT with $UWSGI_THREADS threads, and listen queue size of $SOMAXCONN"
uwsgi --disable-logging --master -p $UWSGI_THREADS --need-app --http 127.0.0.1:$PORT --listen $SOMAXCONN -w serve:app --post-buffering 1 >> /tmp/libertea-panel.log 2>&1

log "Libertea panel serve script exited with code $?"
