#!/bin/bash

MAX_RETRIES=30
RETRY_INTERVAL=2 

ROOT_DIR="$( cd "$(dirname "$0")/.." >/dev/null 2>&1 ; pwd -P )"

# Restricted-network installs cannot reach Docker Hub. init.sh exports the
# mirror; when this script is run on its own, read it from the profile instead.
MONGO_REGISTRY="${LIBERTEA_DOCKER_REGISTRY:-}"
if [ -z "$MONGO_REGISTRY" ] && [ -f "$ROOT_DIR/.libertea.iran" ]; then
    # shellcheck source=restricted-network.sh
    . "$ROOT_DIR/bash-tools/restricted-network.sh"
    MONGO_REGISTRY="$LIBERTEA_IR_DOCKER_REGISTRY"
fi

wait_for_mongo_ready() {
    local container_id=$1
    local retries=0

    echo "Waiting for MongoDB container $container_id to be ready..."
    sleep "$RETRY_INTERVAL"
    until docker exec "$container_id" mongosh --quiet --eval "db.adminCommand({ ping: 1 })" >/dev/null 2>&1; do
        retries=$((retries + 1))
        if [ "$retries" -ge "$MAX_RETRIES" ]; then
            echo "Error: MongoDB container $container_id did not become ready in time!"
            docker stop "$container_id" >/dev/null
            exit 1
        fi
        echo "MongoDB not ready yet. Retrying in $RETRY_INTERVAL seconds... ($retries/$MAX_RETRIES)"
        sleep "$RETRY_INTERVAL"
    done
    echo "MongoDB container $container_id is ready!"
}

run_mongo_command() {
    local mongo_version=$1
    local mongo_command=$2

    echo "Starting MongoDB $mongo_version container..."
    container_id=$(docker run -d -v "./data/db:/data/db" --name libertea-mongodb -h libertea-mongodb -e MONGO_INITDB_ROOT_USERNAME=root -e MONGO_INITDB_ROOT_PASSWORD=${PANEL_MONGODB_PASSWORD} -v ./data/db:/data/db "${MONGO_REGISTRY}mongo:$mongo_version")

    wait_for_mongo_ready "$container_id"

    echo "Running command on MongoDB $mongo_version: $mongo_command"
    docker exec "$container_id" mongosh --quiet --username root --password "$PANEL_MONGODB_PASSWORD" --eval "$mongo_command"

    echo "Stopping MongoDB $mongo_version container..."
    docker stop "$container_id" >/dev/null
}

if [[ $(uname -m) == *"x86"* ]]; then
    if [[ ! $(grep avx2 /proc/cpuinfo) ]]; then 
        # Running in compatibility mode, don't upgrade mongodb
        exit 0
    fi
fi

mongo_upgrade_needed=$(docker logs libertea-mongodb | grep "UPGRADE PROBLEM" | wc -l)
if [ $mongo_upgrade_needed != "0" ]; then
    echo " ** Upgrading mongodb data files..."
     
    docker rm -f libertea-mongodb
    run_mongo_command "7" 'db.adminCommand({ setFeatureCompatibilityVersion: "7.0", confirm: true })'
    docker rm -f libertea-mongodb
    run_mongo_command "8" 'db.adminCommand({ setFeatureCompatibilityVersion: "7.0", confirm: true })'
    docker rm -f libertea-mongodb
fi
