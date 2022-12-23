#!/bin/bash

set -e

# if not elevated, elevate
if [ "$EUID" -ne 0 ]; then
    sudo "$0" "$@"
    exit
fi

# This file is downloaded via curl and executed by user in a single command
# It's intended to be used as a bootstrap script for the whole Libertea project.

REPO_URL="https://github.com/VZiChoushaDui/Libertea.git"
PROJECT_NAME="libertea"
COMMAND="$1"

if [ "$COMMAND" != "install" ] && [ "$COMMAND" != "update" ] && [ "$COMMAND" != "install-proxy" ]; then
    echo "Usage: $0 [install|update|install-proxy]"
    exit 1
fi

# Make sure apt-get exists
if ! command -v apt-get &> /dev/null; then
    echo "apt-get not found. This script is intended for Debian-based systems only."
    exit 1
fi

# Make sure git is installed
if ! command -v git &> /dev/null; then
    echo " ** Installing git..."
    apt-get update >/dev/null
    apt-get install -y git >/dev/null
fi

# Clone the repository to /root if not exists, otherwise update it
if [ -d "/root/$PROJECT_NAME" ]; then
    echo " ** Updating repository..."
    cd "/root/$PROJECT_NAME"
    git reset --hard >/dev/null
    git checkout master >/dev/null
    git reset --hard >/dev/null
    git clean -fd >/dev/null
    
    git pull --rebase >/dev/null
else
    echo " ** Cloning repository..."
    git clone "$REPO_URL" "/root/$PROJECT_NAME" >/dev/null
    cd "/root/$PROJECT_NAME"
fi


if [ "$COMMAND" = "install" ]; then
    # Install the project
    echo " ** Installing $PROJECT_NAME..."
    ./init.sh
elif [ "$COMMAND" = "update" ]; then
    # Update the project
    echo "Updating $PROJECT_NAME..."
    ./init.sh update
elif [ "$COMMAND" = "install-proxy" ]; then
    # Install the proxy
    echo "Installing $PROJECT_NAME-proxy..."
    ./init-proxy.sh "$2" "$3" "$4"
fi
