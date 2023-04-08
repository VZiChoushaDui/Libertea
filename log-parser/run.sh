#!/bin/bash

while true; do
    cd /app
    python3 parse.py
    python3 summarize.py
    cd /data/logs

    files_to_compress=`ls -t | grep -v gz |  tail -n +2 | wc -l`

    if [ $files_to_compress -gt 0 ]; then
        echo "Compressing $files_to_compress files"
        ls -t | grep -v gz |  tail -n +2 | xargs gzip --verbose
    fi

    files_to_delete=`ls -t | grep gz |  tail -n +72 | wc -l`
    if [ $files_to_delete -gt 0 ]; then
        echo "Deleting $files_to_delete old files"
        ls -t | grep gz |  tail -n +72 | xargs rm
    fi

    sleep 300
done
