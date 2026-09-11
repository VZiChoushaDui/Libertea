#!/bin/bash

# stats_cache and connected_ips_log grow by one document per user per day,
# forever, with no native TTL (their _id is a string, not the ObjectId/Date
# a TTL index needs). Fixed 365-day retention, no disk-pressure shrinking:
# unlike the flat-file eviction in log-parser/evict.py, this data is small
# enough that a fixed window is simpler and predictable.
RETENTION_DAYS="${LIBERTEA_RETENTION_DAYS:-365}"

ROOT_DIR="$( cd "$(dirname "$0")/.." >/dev/null 2>&1 ; pwd -P )"
cd "$ROOT_DIR"

if [ -z "${PANEL_MONGODB_PASSWORD:-}" ] && [ -f "$ROOT_DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    . "$ROOT_DIR/.env"
    set +a
fi

if ! docker inspect libertea-mongodb >/dev/null 2>&1; then
    exit 0
fi

cutoff=$(date -u -d "-$RETENTION_DAYS days" +%Y-%m-%dT00:00:00Z)

# Ids are collected first and deleted in chunks: a single \$in with every id of
# a long-lived install can outgrow the 16MB BSON command limit.
eval_js="
var cutoff = new Date('$cutoff');

function evictOld(collName, pattern, toDate) {
    var coll = db.getCollection(collName);
    var toDelete = [];
    coll.find({}, {_id: 1}).forEach(function(doc) {
        var m = ('' + doc._id).match(pattern);
        if (!m) return;
        if (toDate(m) >= cutoff) return;
        toDelete.push(doc._id);
    });

    var removed = 0;
    for (var i = 0; i < toDelete.length; i += 1000) {
        removed += coll.deleteMany({_id: {\$in: toDelete.slice(i, i + 1000)}}).deletedCount;
    }
    if (removed > 0) {
        print(' ** Evicted ' + removed + ' old ' + collName + ' doc(s)');
    }
}

evictOld('stats_cache', /^(\d{4})-(\d{2})(-(\d{2}))?-/, function(m) {
    return new Date(Date.UTC(parseInt(m[1]), parseInt(m[2]) - 1, m[4] ? parseInt(m[4]) : 1));
});

evictOld('connected_ips_log', /--(\d{4})-(\d{1,2})-(\d{1,2})\$/, function(m) {
    return new Date(Date.UTC(parseInt(m[1]), parseInt(m[2]) - 1, parseInt(m[3])));
});
"

docker exec libertea-mongodb mongosh --quiet --username root --password "$PANEL_MONGODB_PASSWORD" --authenticationDatabase admin panel --eval "$eval_js" \
    || docker exec libertea-mongodb mongosh --quiet panel --eval "$eval_js"
