FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for psycopg and Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies from lockfile
COPY Pipfile Pipfile.lock ./
RUN pip install --no-cache-dir pipenv && \
    pipenv sync --system && \
    pip uninstall -y pipenv

# Copy application code
COPY . .

EXPOSE 8000

# Workers: 2 * CPU_count + 1 is the recommended starting point.
# Adjust --workers based on your droplet's CPU count.
CMD ["gunicorn", "metron.wsgi:application", \
    "--bind", "0.0.0.0:8000", \
    "--workers", "4", \
    "--timeout", "60", \
    "--forwarded-allow-ips", "*", \
    "--access-logfile", "-", \
    "--error-logfile", "-"]
