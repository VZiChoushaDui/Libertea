#!/bin/bash

### DEPRECATED ###


# get country code
COUNTRY_CODE=$(curl -s --max-time 3 https://ifconfig.io/country_code)
if [ -z "$COUNTRY_CODE" ]; then
    COUNTRY_CODE=$(curl -s --max-time 3 https://ipapi.co/country_code)
fi
if [ -z "$COUNTRY_CODE" ]; then
    COUNTRY_CODE=$(curl -s --max-time 3 https://ipinfo.io/country)
fi
if [ -z "$COUNTRY_CODE" ]; then
    COUNTRY_CODE=$(curl -s --max-time 3 https://ipapi.co/country_code)
fi
if [ -z "$COUNTRY_CODE" ]; then
    echo "Could not get country code. Will generate fake traffic."
    COUNTRY_CODE="CN"
fi

countries=("CN" "RU" "CU" "TH" "TM" "IR" "SY" "SA" "TR")

# check if country code is in the list
if [[ " ${countries[@]} " =~ " ${COUNTRY_CODE} " ]]; then
    echo "Country code $COUNTRY_CODE is in the list. Will generate fake traffic."
else
    echo "Country code $COUNTRY_CODE is not in the list."
    while true; do
        sleep 1
    done
    exit 1
fi


# generate fake traffic to $CONN_PROXY_IP port 443 so the traffic shape is not symmetric
while true; do

    for i in {1..30}; do
        
        rand=$(od -N 4 -t uL -An /dev/urandom | tr -d " ")
        RANDOM_SIZE=$(( ( $rand % 100000 )  + 1000 ))
        RANDOM_STRING=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w $RANDOM_SIZE | head -n 1)

        RANDOM_STRING_LEN=${#RANDOM_STRING}
        # echo "Sending $RANDOM_STRING_LEN bytes of random data to $CONN_PROXY_IP:443"
        
        # send random data to $CONN_PROXY_IP port 443
        echo "$RANDOM_STRING" | nc -w 1 $CONN_PROXY_IP 443
    done

    SLEEP_MS=$(( 10 * (( $rand % 300 )  + 1 ) ))
    SLEEP_S=$(echo "scale=2; $SLEEP_MS / 1000" | bc)
    echo "Sleeping for $SLEEP_S seconds"
    sleep $SLEEP_S
done
