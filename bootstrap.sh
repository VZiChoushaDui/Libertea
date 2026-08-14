#!/bin/bash

set -e

# if not elevated, elevate
if [ "$EUID" -ne 0 ]; then
    sudo -E /bin/bash "$0" "$@"
    exit
fi

# This file is downloaded via curl and executed by user in a single command
# It's intended to be used as a bootstrap script for the whole Libertea project.

REPO_URL="https://github.com/VZiChoushaDui/Libertea.git"
PROJECT_NAME="libertea"
COMMAND="$1"

if [ "$COMMAND" != "install" ] && [ "$COMMAND" != "update" ] && [ "$COMMAND" != "install-proxy" ] && [ "$COMMAND" != "uninstall" ]; then
    echo "Usage: $0 [install|update|install-proxy|uninstall] [--iran-blackout]"
    exit 1
fi

if [ "$COMMAND" != "uninstall" ]; then
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
    if [ -d "/root/$PROJECT_NAME/.git" ]; then
        echo " ** Updating repository..."
        cd "/root/$PROJECT_NAME"
        git reset --hard >/dev/null
        git checkout master >/dev/null
        git reset --hard >/dev/null
        git clean -fd >/dev/null

        if ! git pull --rebase >/dev/null; then
            echo "    - Could not reach $REPO_URL, continuing with the files already on disk."
        fi
    elif [ -d "/root/$PROJECT_NAME" ]; then
        # Files placed by hand, e.g. an offline archive on a restricted network.
        echo " ** Using the existing files in /root/$PROJECT_NAME (not a git checkout)..."
        cd "/root/$PROJECT_NAME"
    else
        echo " ** Cloning repository..."
        if ! git clone "$REPO_URL" "/root/$PROJECT_NAME" >/dev/null; then
            echo ""
            echo "ERROR: Could not clone $REPO_URL."
            echo "       If GitHub is unreachable, copy the Libertea files to"
            echo "       /root/$PROJECT_NAME yourself and run this command again."
            exit 1
        fi
        cd "/root/$PROJECT_NAME"
    fi

    if [ -z "$LIBERTEA_BRANCH" ]; then
        if [ -f "/root/$PROJECT_NAME/.env" ]; then
            . /root/$PROJECT_NAME/.env
            export LIBERTEA_BRANCH="$LIBERTEA_BRANCH_NAME"
            echo "Will use branch $LIBERTEA_BRANCH based on existing Libertea installation."
        fi
    fi  

    if [ -n "$LIBERTEA_BRANCH" ] && [ -d "/root/$PROJECT_NAME/.git" ]; then
        echo " ** Checking out branch $LIBERTEA_BRANCH..."
        if ! git checkout "$LIBERTEA_BRANCH" >/dev/null; then
            echo "    - Branch $LIBERTEA_BRANCH is not available locally, staying on the current one."
        elif ! git pull --rebase >/dev/null; then
            echo "    - Could not reach $REPO_URL, continuing with the files already on disk."
        fi
    fi
fi

if [ "$COMMAND" = "install" ]; then
    # Install the project
    echo " ** Installing $PROJECT_NAME..."
    ./init.sh "${@:2}"
elif [ "$COMMAND" = "update" ]; then
    # Update the project
    echo "Updating $PROJECT_NAME..."
    ./init.sh update "${@:2}"
elif [ "$COMMAND" = "install-proxy" ]; then
    # Install the proxy
    echo "Installing $PROJECT_NAME-proxy..."
    ./init-proxy.sh "${@:2}"
elif [ "$COMMAND" = "uninstall" ]; then
    set +e

    echo "Are you sure you want to uninstall Libertea? This action is irreversible. [y/N]"
    read -r CONFIRM
    if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
        echo "Uninstall cancelled."
        exit 0
    fi

    cd "/root/$PROJECT_NAME"
    echo " ** Stopping docker containers..."
    for container_name in $(docker ps -a | grep "libertea-" | awk '{print $NF}'); do
        echo "   - $container_name"
        docker rm -f "$container_name" >/dev/null
    done

    echo " ** Stopping systemd service..."
    pkill -9 -f uwsgi
    systemctl kill libertea-panel.service
    pkill -9 -f uwsgi
    systemctl stop libertea-panel.service

    echo " ** Removing systemd service..."
    systemctl disable libertea-panel.service
    rm -f /etc/systemd/system/libertea-panel.service

    echo " ** Removing proxy systemd services..."
    systemctl stop libertea-proxy-ssh-tunnel-0.service >/dev/null 2>&1
    systemctl stop libertea-proxy-ssh-tunnel-1.service >/dev/null 2>&1
    systemctl stop libertea-proxy-ssh-tunnel-2.service >/dev/null 2>&1
    systemctl stop libertea-proxy-ssh-tunnel-3.service >/dev/null 2>&1
    systemctl stop libertea-proxy-ssh-tunnel-4.service >/dev/null 2>&1
    systemctl disable libertea-proxy-ssh-tunnel-0.service >/dev/null 2>&1
    systemctl disable libertea-proxy-ssh-tunnel-1.service >/dev/null 2>&1
    systemctl disable libertea-proxy-ssh-tunnel-2.service >/dev/null 2>&1
    systemctl disable libertea-proxy-ssh-tunnel-3.service >/dev/null 2>&1
    systemctl disable libertea-proxy-ssh-tunnel-4.service >/dev/null 2>&1
    systemctl stop libertea-proxy-fake-traffic.service >/dev/null 2>&1
    systemctl disable libertea-proxy-fake-traffic.service >/dev/null 2>&1
    systemctl stop libertea-proxy-register.service >/dev/null 2>&1
    systemctl disable libertea-proxy-register.service >/dev/null 2>&1
    systemctl stop haproxy >/dev/null 2>&1
    systemctl disable haproxy >/dev/null 2>&1

    echo " ** Removing restricted-network apt/DNS overrides..."
    if [ -f "/root/$PROJECT_NAME/bash-tools/restricted-network.sh" ]; then
        DIR="/root/$PROJECT_NAME"
        # shellcheck source=bash-tools/restricted-network.sh
        . "/root/$PROJECT_NAME/bash-tools/restricted-network.sh"
        libertea_restricted_uninstall
    fi

    echo " ** Deleting Libertea files..."
    cd /root
    rm -rf "/root/$PROJECT_NAME"

    echo ""
    echo "Uninstall complete."
fi
