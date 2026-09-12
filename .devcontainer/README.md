# Dev Container

This devcontainer setup provides a unified development environment for Metron across all host operating systems using VS Code and Docker Compose.

## Requirements

- [VS Code](https://code.visualstudio.com/)
- [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) for VS Code
- [Docker Desktop](https://www.docker.com/products/docker-desktop/), Podman, or OrbStack

## What's Included

The devcontainer setup automatically provisions a multi-container environment via `docker-compose`:

- **App container**: Python 3.14 environment managed by `uv`
- **Database container**: PostgreSQL 16 (database: `metron`, user: `metron`, password: `metron`)
- **Cache container**: Redis 7

## Automatic Setup

When the devcontainer opens, `.devcontainer/post-create.sh` runs automatically to:

1. Install project dependencies (`uv sync`)
2. Run database migrations (`python manage.py migrate`)
3. Provision a default superuser account:
   - **Username**: `dev`
   - **Password**: `dev`
   - **Email**: `none@local.dev`

Whenever the container starts, `.devcontainer/post-start.sh` automatically launches the Django development server on `0.0.0.0:8000`.

## Accessing the Application

- **Web Application**: [http://localhost:8000/](http://localhost:8000/)
- **Django Admin**: [http://localhost:8000/admin/](http://localhost:8000/admin/) (Login: `dev` / `dev`)

## Useful Development Commands

### Web Server

Check if the server is running or start it manually:

```bash
bash .devcontainer/post-start.sh
```

Or run interactively in a terminal:

```bash
python manage.py runserver 0.0.0.0:8000
```

### Superuser Management

Create an additional superuser interactively:

```bash
python manage.py createsuperuser
```

### Database & Testing

- **Run migrations**:
  ```bash
  python manage.py migrate
  ```
- **Open Django shell**:
  ```bash
  python manage.py shell
  ```
- **Open Database CLI**:
  ```bash
  python manage.py dbshell
  ```
- **Run test suite**:
  ```bash
  pytest
  ```

### Completely emptying the database

PostgreSQL data is stored in the named volume `postgres-data` which is independent of the container images. Rebuilding the devcontainer does **not** delete this volume; this is helpful for making sure previously applied migrations and data persist across rebuilds.

To wipe the database completely: remove the volume before (re)building. Run this from the host, outside VS Code after first stopping the devcontainer:

```bash
# Docker
docker compose -f .devcontainer/docker-compose.yml down -v

# Podman
podman-compose -f .devcontainer/docker-compose.yml down -v
```

The `-v` flag removes the named volumes including `postgres-data`. The next time the devcontainer starts, `db` will reinitialize from `init.sql` and `post-create.sh` will apply all migrations against a fresh database.
