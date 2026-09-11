#!/bin/bash

# A disk-full event can truncate a WiredTiger journal/log segment mid-write,
# so mongod refuses to start with a corruption panic afterwards. mongod
# --repair rebuilds the on-disk tables from what is salvageable; running it
# here keeps recovery fully scripted instead of a human hand-repairing data
# after an outage.

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

MONGO_IMAGE="mongo:8.3"
if [[ $(uname -m) == *"x86"* ]] && [[ ! $(grep avx2 /proc/cpuinfo) ]]; then
    MONGO_IMAGE="mongo:4.4"
fi

CORRUPTION_PATTERN="WT_PANIC|WiredTiger error|requires repair|repair is required|metadata (table )?is corrupted|run.*mongod.*--repair"
MAX_WAIT=60

if ! docker inspect libertea-mongodb >/dev/null 2>&1; then
    exit 0
fi

logs_show_corruption() {
    docker logs libertea-mongodb 2>&1 | grep -qiE "$CORRUPTION_PATTERN"
}

mongo_is_ready() {
    docker exec libertea-mongodb mongosh --quiet --username root --password "${PANEL_MONGODB_PASSWORD:-}" --authenticationDatabase admin --eval "db.adminCommand({ ping: 1 })" >/dev/null 2>&1 \
        || docker exec libertea-mongodb mongosh --quiet --eval "db.adminCommand({ ping: 1 })" >/dev/null 2>&1
}

# A panic can take longer to surface than the caller is willing to sleep, so
# wait for a verdict: corruption logged, mongod answering, or mongod gone.
corrupted=0
waited=0
while [ "$waited" -lt "$MAX_WAIT" ]; do
    if logs_show_corruption; then
        corrupted=1
        break
    fi
    if mongo_is_ready; then
        break
    fi
    if [ "$(docker inspect -f '{{.State.Running}}' libertea-mongodb 2>/dev/null)" != "true" ]; then
        # mongod gave up (corruption, FCV upgrade problem, ...); logs are final
        logs_show_corruption && corrupted=1
        break
    fi
    sleep 1
    waited=$((waited + 1))
done

if [ "$corrupted" -ne 1 ]; then
    exit 0
fi

echo " ** MongoDB storage files look corrupted (likely a full-disk event). Running mongod --repair..."
docker rm -f libertea-mongodb >/dev/null 2>&1 || true

if ! docker run --rm \
    -v "$ROOT_DIR/data/db:/data/db" \
    "${MONGO_REGISTRY}${MONGO_IMAGE}" \
    mongod --repair --dbpath /data/db; then
    echo "ERROR: MongoDB repair failed. Data may be unrecoverable; restore from backup."
    exit 1
fi

echo " ** MongoDB repair finished successfully."
