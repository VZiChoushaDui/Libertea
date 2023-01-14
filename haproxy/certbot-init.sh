#!/bin/bash

sudo mkdir -p /etc/ssl/ha-certs

sudo rm /etc/cron.d/certbot-cron
sudo touch /etc/cron.d/certbot-cron

DIR="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

echo "# certbot" | sudo tee -a /etc/cron.d/certbot-cron
echo "0 0 * * *     root   chmod +x $DIR/certbot-renew.sh && $DIR/certbot-renew.sh 2>&1 >> /var/log/certbot-log" | sudo tee -a /etc/cron.d/certbot-cron
