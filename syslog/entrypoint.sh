#!/bin/bash

export TZ=$(cat /etc/timezone) 
rsyslogd -n
