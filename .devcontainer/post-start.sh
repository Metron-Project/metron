#!/usr/bin/env bash

set -euo pipefail

# Start the Django dev server in the background if it is not already running on port 8000.
#
# setsid + disown fully detach the process from this postStartCommand exec session
# (stdin included). Plain `nohup ... &` is not enough under Podman: a backgrounded
# child can still get reaped when the exec session for postStartCommand ends.
if ! curl -s http://127.0.0.1:8000/ > /dev/null 2>&1; then
    setsid nohup /workspace/.venv/bin/python manage.py runserver 0.0.0.0:8000 < /dev/null > /tmp/django-server.log 2>&1 &
    disown
fi
