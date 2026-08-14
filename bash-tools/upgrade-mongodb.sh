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
        7.0|8.0|8.1|8.2)
            echo "db.adminCommand({ setFeatureCompatibilityVersion: \"$fcv\", confirm: true })"
            ;;
        *)
            echo "db.adminCommand({ setFeatureCompatibilityVersion: \"$fcv\" })"
            ;;
    esac
}

run_mongo_command() {
    local mongo_version=$1
    local mongo_command=$2

    echo "    Starting MongoDB $mongo_version..."
    docker rm -f libertea-mongodb >/dev/null 2>&1 || true
    container_id=$(docker run -d \
        --name libertea-mongodb \
        -h libertea-mongodb \
        -e MONGO_INITDB_ROOT_USERNAME=root \
        -e MONGO_INITDB_ROOT_PASSWORD="$PANEL_MONGODB_PASSWORD" \
        -v "$ROOT_DIR/data/db:/data/db" \
        "${MONGO_REGISTRY}mongo:$mongo_version")

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

# Intermediate images only. Compose keeps image: mongo:8 so hosts already on
# 8.1/8.2 stay there; 8.2 cannot start on FCV 6.0 or 7.0, so we raise FCV
# through 7.0 then 8.0 first.
steps=""
case "$fcv" in
    4.4) steps="5.0 6.0 7.0 8.0" ;;
    5.0) steps="6.0 7.0 8.0" ;;
    6.0) steps="7.0 8.0" ;;
    7.0) steps="8.0" ;;
    8.0|8.1|8.2)
        echo " ** MongoDB featureCompatibilityVersion is already $fcv"
        exit 0
        ;;
    *) steps="7.0 8.0" ;;
esac

echo " ** Upgrading MongoDB data files (featureCompatibilityVersion $fcv -> 8.0 via $steps)..."

for step in $steps; do
    run_mongo_command "$step" "$(set_fcv_command "$step")"
done
