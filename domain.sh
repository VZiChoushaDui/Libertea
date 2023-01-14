#!/bin/bash

COMMAND="$1"

# load .env file
set -o allexport
source .env
set +o allexport


if [[ "$COMMAND" == "add" ]]; then
    DOMAIN="$2"
    if [[ -z "$DOMAIN" ]]; then
        echo "Please provide a name for the new domain"
        exit 1
    fi

    echo "Adding domain: $DOMAIN"

    # send a POST request to localhost:1000/api/addDomain with X-API-KEY header
    # and the domain as the form body, and get the response code
    # if response code is 200, then the domain was created successfully
    # if response code is 409, then the domain already exists

    response_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "X-API-KEY: $HOSTCONTROLLER_API_KEY" -F "domain=$DOMAIN" http://localhost:1000/api/addDomain)

    if [[ "$response_code" == "200" ]]; then
        echo "Domain added successfully"
    elif [[ "$response_code" == "409" ]]; then
        echo "Domain already exists"
    elif [[ "$response_code" == "501" ]]; then
        echo "Failed to get SSL certificate for domain. Make sure DNS is configured correctly, and try again later."
    else
        echo "Failed to add domain: $response_code"
    fi
elif [[ "$COMMAND" == "remove" ]]; then
    DOMAIN="$2"
    if [[ -z "$DOMAIN" ]]; then
        echo "Please provide a name for the domain to remove"
        exit 1
    fi

    echo "Removing domain: $DOMAIN"

    # send a POST request to localhost:1000/api/removeDomain with X-API-KEY header
    # and the domain as the form body, and get the response code
    # if response code is 200, then the domain was removed successfully
    # if response code is 404, then the domain does not exist

    response_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "X-API-KEY: $HOSTCONTROLLER_API_KEY" -F "domain=$DOMAIN" http://localhost:1000/api/removeDomain)

    if [[ "$response_code" == "200" ]]; then
        echo "Domain removed successfully"
    elif [[ "$response_code" == "404" ]]; then
        echo "Domain does not exist"
    else
        echo "Failed to remove domain"
    fi
elif [[ "$COMMAND" == "list" ]]; then
    # send a GET request to localhost:1000/api/getDomains with X-API-KEY header
    # and get the response body and print it
    result=$(curl -s -X GET -H "X-API-KEY: $HOSTCONTROLLER_API_KEY" http://localhost:1000/api/getDomains)
    
    # response is like ["domain1", "domain2"]
    # write each domain to a new line
    echo "$result" | jq -r '.[]'
    
else 
    echo "Usage: "
    echo "    ./domain.sh add <domain>"
    echo "    ./domain.sh remove <domain>"
    echo "    ./domain.sh list"
fi


