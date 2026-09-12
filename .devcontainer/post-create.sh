#!/usr/bin/env bash

set -euo pipefail

uv sync

# Apply database migrations.
python manage.py migrate

# Automatically create a superuser with username "dev" and password "dev".
python manage.py shell -c "from django.contrib.auth import get_user_model; user_model = get_user_model(); user, _ = user_model.objects.update_or_create(username='dev', defaults={'email': 'none@local.dev', 'is_staff': True, 'is_superuser': True}); user.set_password('dev'); user.save()"
