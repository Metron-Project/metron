# Development Setup

## Prerequisites

- Podman
- Python (see `.python-version` for required version)
- A production database dump (optional, see below)

## Container Setup

### PostgreSQL

```bash
podman run -d \
  --name metron-postgres \
  -e POSTGRES_DB=metron \
  -e POSTGRES_USER=<DB User> \
  -e POSTGRES_PASSWORD=<DB Password> \
  -p 5432:5432 \
  -v metron-pgdata:/var/lib/postgresql/data \
  postgres:16
```

The named volume (`metron-pgdata`) ensures data persists even if the container is removed.

### Redis

```bash
podman run -d \
  --name metron-redis \
  -p 6379:6379 \
  redis
```

## Environment Variables

Copy `.env.example` to `.env` and fill in the values. Add the following variables that are not in the example:

```ini
DB_HOST=localhost

REDIS_URL=redis://localhost:6379/0
THUMBNAIL_REDIS_HOST=localhost
```

## Database Setup

### Option A: Restore from a production dump

First, set up the required PostgreSQL extensions and the immutable `unaccent` wrapper (needed for trigram indexes):

```bash
podman exec -it metron-postgres psql -U <DB User> -d metron -c "
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE OR REPLACE FUNCTION public.unaccent(text)
  RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT AS
  \$\$ SELECT public.unaccent('public.unaccent', \$1) \$\$;
"
```

Then copy the dump into the container and restore it:

```bash
podman cp /path/to/dump.pgdump metron-postgres:/tmp/dump.pgdump
podman exec -it metron-postgres pg_restore -U <DB User> -d metron --no-owner /tmp/dump.pgdump
```

Finally, apply any migrations not yet on production:

```bash
python manage.py migrate
```

### Option B: Fresh database

```bash
python manage.py migrate
```

## Starting and Stopping Containers

```bash
# Start
podman start metron-postgres metron-redis

# Stop
podman stop metron-postgres metron-redis
```
