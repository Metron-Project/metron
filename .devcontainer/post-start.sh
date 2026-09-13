#!/usr/bin/env bash

set -euo pipefail

# Start the Django dev server in the background if it is not already running on port 8000.
if ! curl -s http://127.0.0.1:8000/ > /dev/null 2>&1; then
    nohup /workspace/.venv/bin/python manage.py runserver 0.0.0.0:8000 > /tmp/django-server.log 2>&1 &
fi
