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

if [ -z "${PANEL_MONGODB_PASSWORD:-}" ] && [ -f "$ROOT_DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    . "$ROOT_DIR/.env"
    set +a
fi

wait_for_mongo_ready() {
    local container_id=$1
    local retries=0

    echo "    Waiting for MongoDB $container_id to be ready..."
    sleep "$RETRY_INTERVAL"
    until docker exec "$container_id" mongosh --quiet --username root --password "$PANEL_MONGODB_PASSWORD" --authenticationDatabase admin --eval "db.adminCommand({ ping: 1 })" >/dev/null 2>&1 \
        || docker exec "$container_id" mongosh --quiet --eval "db.adminCommand({ ping: 1 })" >/dev/null 2>&1; do
        retries=$((retries + 1))
        if [ "$retries" -ge "$MAX_RETRIES" ]; then
            echo "Error: MongoDB container $container_id did not become ready in time!"
            docker logs "$container_id" 2>&1 | tail -n 20 | sed 's/^/        /'
            docker rm -f "$container_id" >/dev/null
            exit 1
        fi
        echo "    MongoDB not ready yet. Retrying in $RETRY_INTERVAL seconds... ($retries/$MAX_RETRIES)"
        sleep "$RETRY_INTERVAL"
    done
}

set_fcv_command() {
    local fcv=$1
    case "$fcv" in
        7.0|8.0|8.1|8.2|8.3)
            echo "db.adminCommand({ setFeatureCompatibilityVersion: \"$fcv\", confirm: true })"
            ;;
        *)
            echo "db.adminCommand({ setFeatureCompatibilityVersion: \"$fcv\" })"
            ;;
    esac
}

# Docker Hub never published a mongo:8.1 image (library/mongo jumps from 8.0
# straight to 8.2), so FCV 8.1 is set with the 8.2 binary, which still accepts
# it as its last-continuous version.
image_for_fcv() {
    case "$1" in
        8.1) echo "8.2" ;;
        *) echo "$1" ;;
    esac
}

run_mongo_command() {
    local mongo_version=$1
    local mongo_command=$2
    local image_tag
    image_tag=$(image_for_fcv "$mongo_version")

    echo "    Starting MongoDB $image_tag (featureCompatibilityVersion $mongo_version)..."
    docker rm -f libertea-mongodb >/dev/null 2>&1 || true
    container_id=$(docker run -d \
        --name libertea-mongodb \
        -h libertea-mongodb \
        -e MONGO_INITDB_ROOT_USERNAME=root \
        -e MONGO_INITDB_ROOT_PASSWORD="$PANEL_MONGODB_PASSWORD" \
        -v "$ROOT_DIR/data/db:/data/db" \
        "${MONGO_REGISTRY}mongo:$image_tag")

    if [ -z "$container_id" ]; then
        echo "Error: could not start ${MONGO_REGISTRY}mongo:$image_tag"
        exit 1
    fi

    wait_for_mongo_ready "$container_id"

    echo "    Setting featureCompatibilityVersion on $mongo_version"
    docker exec "$container_id" mongosh --quiet --username root --password "$PANEL_MONGODB_PASSWORD" --authenticationDatabase admin --eval "$mongo_command" \
        || docker exec "$container_id" mongosh --quiet --eval "$mongo_command"

    echo "    Stopping MongoDB $mongo_version..."
    docker stop "$container_id" >/dev/null
    docker rm -f "$container_id" >/dev/null
}

if [[ $(uname -m) == *"x86"* ]]; then
    if [[ ! $(grep avx2 /proc/cpuinfo) ]]; then
        # Running in compatibility mode, don't upgrade mongodb
        exit 0
    fi
fi

if ! docker inspect libertea-mongodb >/dev/null 2>&1; then
    exit 0
fi

mongo_logs=$(docker logs libertea-mongodb 2>&1 || true)
if ! echo "$mongo_logs" | grep -q "UPGRADE PROBLEM"; then
    exit 0
fi

fcv=$(echo "$mongo_logs" | grep -oE "feature compatibility version value '[0-9]+\.[0-9]+" | grep -oE "[0-9]+\.[0-9]+" | head -n 1)
if [ -z "$fcv" ]; then
    fcv=$(echo "$mongo_logs" | grep -oE 'version: "[0-9]+\.[0-9]+"' | grep -oE "[0-9]+\.[0-9]+" | head -n 1)
fi
if [ -z "$fcv" ]; then
    fcv="6.0"
fi

# Every FCV value mongod accepts on the way up, oldest first. A rung can only
# be reached from the one before it, so the path is just "everything after
# wherever the data files currently sit". 3.6 is a starting point only, never
# set. Compose keeps image: mongo:8.3, the newest FCV each of those binaries
# accepts, so every data file ends up caught up to it instead of stalling on
# some in-between version the next repair also has to handle.
FCV_LADDER="3.6 4.0 4.2 4.4 5.0 6.0 7.0 8.0 8.1 8.2 8.3"
TARGET_FCV="8.3"

steps=""
seen=0
for rung in $FCV_LADDER; do
    if [ "$seen" = "1" ]; then
        steps="${steps:+$steps }$rung"
    elif [ "$rung" = "$fcv" ]; then
        seen=1
    fi
done

if [ "$seen" != "1" ]; then
    echo "Error: unrecognized featureCompatibilityVersion '$fcv', refusing to guess an upgrade path."
    echo "       Upgrade to $TARGET_FCV by hand, or restore from backup."
    exit 1
fi

if [ -z "$steps" ]; then
    echo " ** MongoDB featureCompatibilityVersion is already $fcv"
    exit 0
fi

echo " ** Upgrading MongoDB data files (featureCompatibilityVersion $fcv -> $TARGET_FCV via $steps)..."

for step in $steps; do
    run_mongo_command "$step" "$(set_fcv_command "$step")"
done
