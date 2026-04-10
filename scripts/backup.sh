#!/bin/bash
# Metron PostgreSQL backup script.
# Dumps the database, copies it locally with a timestamp, uploads to
# DigitalOcean Spaces, and prunes local copies older than 30 days.
#
# Expected environment variables (sourced from metron.env by the systemd service):
#   POSTGRES_USER, POSTGRES_DB       — database credentials
#   DO_ACCESS_KEY_ID                 — Spaces access key
#   DO_SECRET_ACCESS_KEY             — Spaces secret key
#   DO_S3_ENDPOINT_URL               — e.g. https://nyc3.digitaloceanspaces.com
#   DO_BACKUP_BUCKET_NAME            — dedicated backup bucket name
set -euo pipefail

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
DUMP_FILE="metron-${TIMESTAMP}.dump"
BACKUP_DIR="${HOME}/backups"

# Map DO credentials to the env vars awscli expects.
# AWS_DEFAULT_REGION is required by awscli but ignored by DO Spaces.
export AWS_ACCESS_KEY_ID="${DO_ACCESS_KEY_ID}"
export AWS_SECRET_ACCESS_KEY="${DO_SECRET_ACCESS_KEY}"
export AWS_DEFAULT_REGION="us-east-1"

echo "Starting backup: ${DUMP_FILE}"

# Step 1: dump inside the postgres container
podman exec metron-postgres pg_dump \
  -U "${POSTGRES_USER}" -Fc "${POSTGRES_DB}" \
  -f /tmp/metron-backup.dump

# Step 2: copy from container to host with timestamped filename
mkdir -p "${BACKUP_DIR}"
podman cp "metron-postgres:/tmp/metron-backup.dump" "${BACKUP_DIR}/${DUMP_FILE}"

# Step 3: upload to Spaces
aws s3 cp "${BACKUP_DIR}/${DUMP_FILE}" \
  "s3://${DO_BACKUP_BUCKET_NAME}/db/${DUMP_FILE}" \
  --endpoint-url "${DO_S3_ENDPOINT_URL}"

# Step 4: prune local backups older than 30 days
find "${BACKUP_DIR}" -name 'metron-*.dump' -mtime +30 -delete

echo "Backup complete: ${DUMP_FILE}"
