#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="polymarekit"
APP_DIR="/var/www/${APP_NAME}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ "$(id -u)" -ne 0 ]; then
    printf 'Run this script with sudo: sudo bash deploy/setup-ec2.sh\n' >&2
    exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y nginx python3 python3-venv python3-pip nodejs npm rsync

mkdir -p "$APP_DIR"
chown -R ubuntu:ubuntu "$APP_DIR"

install -m 0644 "$SCRIPT_DIR/${APP_NAME}.service" "/etc/systemd/system/${APP_NAME}.service"
install -m 0644 "$SCRIPT_DIR/nginx-${APP_NAME}.conf" "/etc/nginx/sites-available/${APP_NAME}"
ln -sfn "/etc/nginx/sites-available/${APP_NAME}" "/etc/nginx/sites-enabled/${APP_NAME}"
rm -f /etc/nginx/sites-enabled/default

systemctl daemon-reload
systemctl enable "${APP_NAME}.service"
nginx -t
systemctl enable nginx
systemctl restart nginx

printf 'EC2 setup complete. Deploy the application with:\n'
printf '  ./deploy/deploy.sh -h <PUBLIC-IP> -i ~/keys/mykey.pem\n'
