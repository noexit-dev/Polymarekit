#!/usr/bin/env bash
set -Eeuo pipefail

HOST=""
IDENTITY=""
APP_NAME="polymarekit"
REMOTE_USER="ubuntu"
REMOTE_DIR="/var/www/${APP_NAME}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

usage() {
    printf 'Usage: %s -h <PUBLIC-IP> -i <SSH-KEY>\n' "$0"
}

while getopts ":h:i:" option; do
    case "$option" in
        h) HOST="$OPTARG" ;;
        i) IDENTITY="$OPTARG" ;;
        *) usage >&2; exit 2 ;;
    esac
done

if [ -z "$HOST" ] || [ -z "$IDENTITY" ]; then
    usage >&2
    exit 2
fi

for command in rsync ssh curl; do
    if ! command -v "$command" >/dev/null 2>&1; then
        printf 'Missing required local tool: %s\n' "$command" >&2
        exit 1
    fi
done

if [ ! -f "$IDENTITY" ]; then
    printf 'SSH key not found: %s\n' "$IDENTITY" >&2
    exit 1
fi

printf 'Running Django checks...\n'
if [ -x "$REPO_DIR/.venv/bin/python" ]; then
    "$REPO_DIR/.venv/bin/python" "$REPO_DIR/manage.py" check
else
    python3 "$REPO_DIR/manage.py" check
fi

SSH=(ssh -i "$IDENTITY" -o BatchMode=yes -o ConnectTimeout=15 -o ConnectionAttempts=1 -o StrictHostKeyChecking=accept-new "${REMOTE_USER}@${HOST}")
RSYNC=(rsync -az --delete --timeout=30 --info=progress2,stats1 -e "ssh -i ${IDENTITY} -o BatchMode=yes -o ConnectTimeout=15 -o ConnectionAttempts=1 -o StrictHostKeyChecking=accept-new")

printf 'Checking SSH connection and remote deploy directory...\n'
if ! "${SSH[@]}" "command -v rsync >/dev/null && test -d '$REMOTE_DIR' && test -w '$REMOTE_DIR'"; then
    printf 'Cannot access %s or remote rsync is missing. Run deploy/setup-ec2.sh on the server first.\n' "$REMOTE_DIR" >&2
    exit 1
fi

printf 'Copying application to %s...\n' "$HOST"
"${RSYNC[@]}" \
    --exclude '.git/' \
    --exclude '.venv/' \
    --exclude 'node_modules/' \
    --exclude '__pycache__/' \
    --exclude 'db.sqlite3' \
    --exclude 'staticfiles/' \
    "$REPO_DIR/" "${REMOTE_USER}@${HOST}:${REMOTE_DIR}/"

printf 'Installing dependencies and restarting service...\n'
"${SSH[@]}" "cd '$REMOTE_DIR' && \
    python3 -m venv .venv && \
    .venv/bin/python -m pip install -r requirements.txt && \
    npm install && \
    .venv/bin/python manage.py migrate --noinput && \
    npm run build:css && \
    .venv/bin/python manage.py collectstatic --noinput && \
    sudo systemctl restart ${APP_NAME}.service && \
    sudo systemctl is-active --quiet ${APP_NAME}.service && \
    curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8000/api/health && \
    sudo ss -ltnp | grep -E ':80 |:8000 '"

printf 'Checking deployment health...\n'
if ! curl --fail --silent --show-error --max-time 15 "http://${HOST}/api/health"; then
    printf '\nDeployment health check failed.\n' >&2
    exit 1
fi
printf '\nDeployment succeeded: http://%s/\n' "$HOST"
