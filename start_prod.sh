#!/bin/bash
set -e

echo "[INFO] Activating production settings..."
export DJANGO_SETTINGS_MODULE=sesclubs.settings.production

echo "[INFO] Running migrations..."
pipenv run python manage.py migrate

echo "[INFO] Collecting static files..."
pipenv run python manage.py collectstatic --noinput

echo "[INFO] Starting Gunicorn..."
pipenv run gunicorn sesclubs.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log