#!/bin/bash

# set timezone based on host
if [ -e /etc/timezone ]; then
    cp /etc/timezone /etc/localtime
fi

rsyslogd -n
