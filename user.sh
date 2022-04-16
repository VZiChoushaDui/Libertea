#!/bin/bash

COMMAND="$1"

# load .env file
set -o allexport
source .env
set +o allexport


if [[ "$COMMAND" == "add" ]]; then
    NOTE="$2"
    if [[ -z "$NOTE" ]]; then
        echo "Please provide a name for the new user"
        exit 1
    fi

    echo "Creating new user with name: $NOTE"

    # send a POST request to localhost:1000/api/createUser with X-API-KEY header
    # and the note as the form body
    result=$(curl -s -X POST -H "X-API-KEY: $HOSTCONTROLLER_API_KEY" -F "note=$NOTE" http://localhost:1000/api/createUser)

    is_duplicate=$(echo "$result" | jq -r '.duplicate')
    if [[ "$is_duplicate" == "true" ]]; then
        echo "User '$NOTE' already exists"
        exit 1
    fi

    # parse result json and extract panelId
    panelId=$(echo "$result" | jq -r '.panelId')

    if [[ -z "$panelId" ]]; then
        echo "Failed to create new user"
        exit 1
    fi

    echo "Created new user with panelId: $panelId"

elif [[ "$COMMAND" == "remove" ]]; then
    NOTE="$2"
    if [[ -z "$NOTE" ]]; then
        echo "Please provide a name for the user to remove"
        exit 1
    fi

    echo "Deleting user with name: $NOTE"

    # send a POST request to localhost:1000/api/removeUser with X-API-KEY header
    # and the note as the form body, and get the response code
    # if response code is 200, then the user was deleted successfully
    # if response code is 404, then the user was not found

    response_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "X-API-KEY: $HOSTCONTROLLER_API_KEY" -F "note=$NOTE" http://localhost:1000/api/removeUser)

    if [[ "$response_code" == "200" ]]; then
        echo "Deleted user with name: $NOTE"
    elif [[ "$response_code" == "404" ]]; then
        echo "User with name: $NOTE not found"
    else
        echo "Failed to delete user with name: $NOTE"
    fi
elif [[ "$COMMAND" == "list" ]]; then
    # send a GET request to localhost:1000/api/getUsers with X-API-KEY header
    # and get the response body and print it
    result=$(curl -s -X GET -H "X-API-KEY: $HOSTCONTROLLER_API_KEY" http://localhost:1000/api/getUsers)

    # convert json to table
    echo "$result" | jq -r '.[] | [.note, .panel_id] | @tsv' | column -t -s $'\t'
else 
    echo "Usage: "
    echo "    ./user.sh add <name>"
    echo "    ./user.sh remove <name>"
    echo "    ./user.sh list"
fi


