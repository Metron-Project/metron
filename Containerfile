FROM python:3.12-slim

WORKDIR /app

# Install Python production dependencies from lockfile.
# PIPENV_VENV_IN_PROJECT and PIPENV_IGNORE_VIRTUALENVS prevent pipenv from
# creating a virtualenv inside the container. --deploy fails the build if
# Pipfile.lock is out of sync with Pipfile.
COPY Pipfile Pipfile.lock ./
RUN pip install --no-cache-dir pipenv && \
    PIPENV_VENV_IN_PROJECT=0 PIPENV_IGNORE_VIRTUALENVS=1 \
    pipenv install --system --deploy && \
    pip uninstall -y pipenv

# Copy application code
COPY . .

EXPOSE 8000

# Workers: 2 * CPU_count + 1 is the recommended starting point.
# Adjust --workers based on your droplet's CPU count.
CMD ["gunicorn", "metron.wsgi:application", \
    "--bind", "0.0.0.0:8000", \
    "--workers", "5", \
    "--timeout", "60", \
    "--max-requests", "300", \
    "--forwarded-allow-ips", "*", \
    "--error-logfile", "-"]
