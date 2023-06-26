#!/bin/bash

date

DIR="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
cd "$DIR"

BRANCH=`git rev-parse --abbrev-ref HEAD`

# only work on 'master' and 'beta' branches
if [[ $BRANCH != "master" ]] && [[ $BRANCH != "beta" ]]; then
    echo "Not on master or beta branch, aborting."
    exit
fi

CUR_VERSION=`cat version.txt`
LATEST_VERSION=`curl -s https://raw.githubusercontent.com/VZiChoushaDui/Libertea/master/version.txt`

if [[ $LATEST_VERSION > $CUR_VERSION ]]; then
    echo "New version detected: $LATEST_VERSION"
    echo "Updating..."
    git pull
    ./init.sh update
else
    echo "No new version detected."
fi
