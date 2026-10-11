#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")"

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        printf 'Missing required tool: %s\n' "$1" >&2
        exit 1
    fi
}

require_command python3
require_command node
require_command npm

if [ ! -d .venv ]; then
    printf 'Creating Python virtual environment...\n'
    if ! python3 -m venv .venv; then
        printf 'Could not create .venv. Install Python 3 with the venv module.\n' >&2
        exit 1
    fi
fi

printf 'Installing Python dependencies...\n'
if ! .venv/bin/python -m pip install -r requirements.txt; then
    printf 'Could not install Python dependencies from requirements.txt.\n' >&2
    exit 1
fi

printf 'Installing JavaScript dependencies...\n'
if ! npm install; then
    printf 'Could not install JavaScript dependencies with npm.\n' >&2
    exit 1
fi

printf 'Preparing database and static assets...\n'
.venv/bin/python manage.py migrate --noinput
npm run build:css

printf 'Starting Polymarekit at http://127.0.0.1:8000/\n'
exec .venv/bin/python manage.py runserver 127.0.0.1:8000
