FROM python:3.14-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Install production dependencies into .venv from lockfile.
# --no-install-project skips installing the app itself (not a package),
# enabling Docker layer caching: dep layer rebuilds only when lockfile changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# ---- runtime image ----
FROM python:3.14-slim

WORKDIR /app

# Copy the pre-built virtual environment (uv itself is not included)
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY . .

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# Workers: 2 * CPU_count + 1 is the recommended starting point.
# Adjust --workers based on your droplet's CPU count.
CMD ["gunicorn", "metron.wsgi:application", \
    "--bind", "0.0.0.0:8000", \
    "--workers", "9", \
    "--timeout", "60", \
    "--max-requests", "1000", \
    "--max-requests-jitter", "50", \
    "--forwarded-allow-ips", "*", \
    "--access-logfile", "-", \
    "--error-logfile", "-"]
