#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")"

missing_packages=()
command -v python3 >/dev/null 2>&1 || missing_packages+=(python3 python3-venv)
command -v node >/dev/null 2>&1 || missing_packages+=(nodejs)
command -v npm >/dev/null 2>&1 || missing_packages+=(npm)

if [ "${#missing_packages[@]}" -gt 0 ]; then
    if ! command -v apt-get >/dev/null 2>&1; then
        printf 'Missing required tools: python3, node, or npm; apt-get is unavailable for automatic installation.\n' >&2
        exit 1
    fi

    if [ "$(id -u)" -eq 0 ]; then
        apt_command=(apt-get)
    elif command -v sudo >/dev/null 2>&1; then
        apt_command=(sudo apt-get)
    else
        printf 'Missing required tools and no sudo access is available to install them: %s\n' "${missing_packages[*]}" >&2
        exit 1
    fi

    printf 'Installing missing tools: %s\n' "${missing_packages[*]}"
    "${apt_command[@]}" update
    "${apt_command[@]}" install -y "${missing_packages[@]}"
fi

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
