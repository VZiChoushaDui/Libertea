#!/bin/bash

set -e

DIR="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
cd "$DIR/panel/panel/templates/rules"

countries=("cn" "ru" "cu" "th" "tm" "ir" "sy" "sa" "tr")

for country in "${countries[@]}"; do
    echo " ** Generating rules for $country..."
    curl -ss "https://raw.githubusercontent.com/herrbischoff/country-ip-blocks/master/ipv4/$country.cidr" -o $country.ipv4.cidr
    curl -ss "https://raw.githubusercontent.com/herrbischoff/country-ip-blocks/master/ipv6/$country.cidr" -o $country.ipv6.cidr >/dev/null
    # combine ipv4 and ipv6
    cat "$country.ipv4.cidr" "$country.ipv6.cidr" > "$country.cidr"

    rm -f "$country-direct.yaml"

    echo "  # $country rules" >> "$country-direct.yaml"
    while IFS= read -r line; do
        echo "  - IP-CIDR,$line,DIRECT" >> "$country-direct.yaml"
    done < "$country.cidr"
    echo "" >> "$country-direct.yaml"

    rm -f "$country.cidr"
    rm -f "$country.ipv4.cidr"
    rm -f "$country.ipv6.cidr"
done
