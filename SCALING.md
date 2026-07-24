# Horizontal Scaling Plan for Metron

## Context

Metron currently runs on a single DigitalOcean droplet with all services co-located: Gunicorn (web), PostgreSQL, Redis, Anubis (bot-protection), and nginx — all managed by Podman Quadlet / systemd. When traffic spikes, the only option today is vertical scaling (adding CPUs to the droplet). This plan outlines what it would take to scale horizontally, giving us multiple app servers behind a load balancer.

The good news is, static and media files are already on DigitalOcean Spaces (S3), which is the hardest part of stateless web tiers. The blockers are the stateful services (Postgres, Redis) and session storage, all of which are currently bound to `127.0.0.1` on one machine.

---

## Target Architecture

```
internet (80/443) → DO Load Balancer (TLS termination)
                              ↓ private network (:80)
                      metron-anubis (single instance)
                              ↓
              ┌───────────────┴───────────────┐
              ↓                               ↓
       droplet-1                       droplet-2  (repeat as needed)
  nginx (host network)             nginx (host network)
              ↓                               ↓
  metron-web (gunicorn, :8000)    metron-web (gunicorn, :8000)
              └───────────────┬───────────────┘
                              ↓
              ┌───────────────┴───────────────┐
              ↓                               ↓
   DO Managed PostgreSQL            DO Managed Redis
```

The DO Load Balancer terminates TLS and distributes traffic across web nodes;
individual droplets no longer need certbot or per-node Let's Encrypt certs. A
single Anubis instance sits between the load balancer and the web tier (Option B
from §2c), so bot-challenge state is consistent regardless of which node handles
a request. Each droplet runs only nginx and metron-web — Postgres and Redis
containers are gone, replaced by DO Managed services reachable over the private
network. Static and media files continue to be served from DigitalOcean Spaces
(S3-compatible); the web nodes remain stateless and interchangeable. nginx uses
the `real_ip` module to extract the true client IP from `X-Forwarded-For` so
that fail2ban's existing jails continue to work correctly.

---

## Recommended Approach: Two Phases

A Kubernetes migration is an option but is a bit of an overkill for a community project at this scale. That's why we'll go with using a load-balancing method first. **Phase 1** (decouple stateful services) + **Phase 2** (add load balancer and a second web node). Kubernetes can be revisited as **Phase 3** if traffic genuinely demands it.

---

## Phase 1 — Decouple Stateful Services (prerequisite for everything)

This phase makes the app tier truly stateless. It can be done without any downtime risk to the current single-droplet setup, and is valuable even if we never add a second web server.

### 1a. Migrate PostgreSQL to DigitalOcean Managed Database

**Why:** The app can't be cloned across droplets while Postgres lives on one of them.

Steps:
1. Provision a DO Managed PostgreSQL cluster (start with the smallest plan, e.g. 1 vCPU / 1 GB).
2. `pg_dump` the existing database and restore into the managed cluster.
3. Update `metron.env`:
   ```
   DB_HOST=<managed-db-hostname>
   POSTGRES_USER=metron
   POSTGRES_PASSWORD=<new-password>
   POSTGRES_DB=metron
   ```
4. Remove the `metron-postgres.container` Quadlet file and `metron-postgres.volume` — the managed DB replaces them.
5. Update `metron-web.container` to remove the `Wants=metron-postgres.service` dependency line, since the DB is now external.

Config file to change: `.quadlet/metron-web.container`, `metron.env`.

**Connection pooling note:** The existing psycopg pool config in `metron/settings.py` (`min_size=2, max_size=4`) is already appropriate for a managed DB. No settings change needed there.

### 1b. Migrate Redis to DigitalOcean Managed Redis

**Why:** Cache and thumbnail KV store must be shared across all web instances, not local.

Steps:
1. Provision a DO Managed Redis cluster.
2. Update `metron.env`:
   ```
   REDIS_URL=rediss://<managed-redis-hostname>:25061/0
   THUMBNAIL_REDIS_HOST=<managed-redis-hostname>
   THUMBNAIL_REDIS_PORT=25061
   ```
   Note: DO Managed Redis uses TLS (`rediss://`). The existing `django.core.cache.backends.redis.RedisCache` backend supports this natively.
3. Remove the `metron-redis.container` Quadlet file and `metron-redis.volume`.
4. Remove the `Wants=metron-redis.service` line from `metron-web.container`.

Config files to change: `.quadlet/metron-web.container`, `metron.env`, `metron/settings.py` (thumbnail host/port settings).

### 1c. Switch Sessions to Redis-Backed

**Why:** Sessions are currently stored in PostgreSQL (`django.contrib.sessions`). Multiple web nodes hitting a shared managed Postgres would work, but Redis-backed sessions are faster and reduce DB load.

Change in `metron/settings.py`:
```python
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
```

This requires the managed Redis from 1b to be in place first. No new packages needed — Django ships this backend.

### 1d. Run `migrate` to clean up the session table

After switching to cache-backed sessions, the `django_session` table in Postgres is no longer used. Run:
```bash
python manage.py clearsessions
```
The table can be left in place (it just won't be written to anymore).

---

## Phase 2 — Load Balancer + Second Web Node

With stateful services external, the app tier is now fully stateless. Adding capacity is straightforward.

### 2a. Provision a DigitalOcean Load Balancer

1. Create a DO Load Balancer in the same region as the droplets.
2. Configure it to forward port 443 to port 8443 on backend droplets (or use the Load Balancer for TLS termination — see note below).
3. Set health check to `GET /health/` (we may need to add a simple health endpoint — see 2d).
4. Point DNS (`metron.cloud`, `www.metron.cloud`) to the Load Balancer IP instead of the droplet IP.

**TLS termination option:** The DO Load Balancer can terminate TLS directly (using DO-managed Let's Encrypt certs), which simplifies nginx config on each droplet — no more certbot needed per node.

### 2b. Clone the Web Droplet

1. Create a snapshot of the current droplet.
2. Spin up a second droplet from that snapshot.
3. On both droplets: update `metron.env` to remove `DB_HOST=127.0.0.1` and `REDIS_URL=redis://127.0.0.1:...` (already done in Phase 1).
4. Both droplets run the same Quadlet units: `metron-web`, `metron-nginx`, `metron-anubis`. Postgres and Redis containers are gone.

### 2c. Handle Anubis Bot-Protection State

**Problem:** Anubis uses a BBolt (local file) state store at `/data/anubis.bdb`. If a browser's challenge response hits a different node than where the challenge was issued, it will fail.

**Solution options (in order of simplicity):**

- **Option A — Sticky sessions on the Load Balancer:** Configure the DO Load Balancer to use IP-based or cookie-based session affinity. Anubis state stays per-node, but each client always hits the same node. Simplest with no code change; acceptable trade-off for bot-protection.
- **Option B — Move Anubis upstream of the LB:** Run a single Anubis instance on a dedicated small droplet or on the LB itself, in front of both web nodes. Anubis handles all bot challenges; only verified traffic reaches the web tier.
- ~~**Option C — Shared NFS volume for BBolt:** Mount a shared volume (DigitalOcean Volumes) for `/data` on all nodes. Only works if BBolt supports concurrent access from multiple processes (it does not — BBolt is single-writer). Not recommended.~~

**Recommended:** Option B (single Anubis in front of LB) for correctness, or Option A (sticky sessions) for simplicity. Option A is cheaper, but it's probably best to just run a droplet with Anubis.

### 2d. Add a Health Check Endpoint

The DO Load Balancer needs an HTTP endpoint to verify node health. Add a minimal view:

File: `comicsdb/views/__init__.py` or a new `comicsdb/views/health.py`:
```python
from django.http import HttpResponse


def health(request):
    return HttpResponse("ok")
```

URL: `metron/urls.py` — add `path("health/", health)`.

This endpoint should NOT be behind Anubis (add `/health/` to Anubis's allow-list in `anubis/policy.yaml`).

### 2e. Update `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`

When requests come through the Load Balancer, Django must trust the LB's forwarded headers. Update `metron/settings.py`:
```python
ALLOWED_HOSTS = ["metron.cloud", "www.metron.cloud"]
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```
The gunicorn flag `--forwarded-allow-ips "*"` is already set in the `Containerfile`, so this is safe.

### 2f. Reconfigure nginx for Real Client IPs (required for fail2ban)

**Problem:** With a load balancer in front, nginx sees every request as originating from the LB's IP, not the real client. fail2ban reads nginx logs to ban offending IPs — if it trips a jail against the LB's IP, it bans *all* traffic to that node instantly.

**Fix:** Enable nginx's `real_ip` module to extract the true client IP from the `X-Forwarded-For` header that the DO Load Balancer injects. Add to the `http` block in `nginx/nginx.conf`:

```nginx
# Extract real client IP from the DO Load Balancer's X-Forwarded-For header.
# Without this, fail2ban sees only the LB IP and will ban all traffic if a jail fires.
set_real_ip_from 10.0.0.0/8;   # DO VPC private network range
real_ip_header X-Forwarded-For;
real_ip_recursive on;
```

Once nginx logs the real client IP, fail2ban's existing jail configs (metron-nginx-429, 403, 404, no-ua, etc.) continue working without any changes.

**Important:** The `set_real_ip_from` directive must only trust the LB's private IP range — never `0.0.0.0/0` — or external clients could spoof their IP by injecting a fake `X-Forwarded-For` header and evade banning.

---

## Phase 3 — Kubernetes (future, if needed)

If traffic grows to the point where manually cloning droplets and managing systemd units becomes painful, DigitalOcean Kubernetes Service (DOKS) is the next step. The app is already containerized, so the main work would be:

1. Push the `metron:latest` image to a container registry (GitHub Container Registry or DO Container Registry).
2. Write a Kubernetes `Deployment` (replacing the Quadlet units) and `Service`/`Ingress` manifests.
3. Use the DO Kubernetes Load Balancer instead of a manual one.
4. Configure Horizontal Pod Autoscaler (HPA) based on CPU or request rate.
5. Use Kubernetes Secrets (or Sealed Secrets / External Secrets Operator) for `metron.env` values.
6. Backups: move from systemd timers to Kubernetes CronJobs.

This is a significant operational step up, and frankly best left to someone with good knowledge of Kubernetes (i.e. not me), and is only warranted if Phase 2 is insufficient.

---

## Summary of Files to Change

| File | Change |
|------|--------|
| `metron/settings.py` | `SESSION_ENGINE`, `SESSION_CACHE_ALIAS`, `USE_X_FORWARDED_HOST`, `SECURE_PROXY_SSL_HEADER` |
| `metron.env` | `DB_HOST`, `REDIS_URL`, `THUMBNAIL_REDIS_HOST`/`PORT` updated to managed services |
| `.quadlet/metron-web.container` | Remove `Wants` for postgres/redis containers |
| `.quadlet/metron-postgres.container` | Delete (replaced by managed DB) |
| `.quadlet/metron-redis.container` | Delete (replaced by managed Redis) |
| `anubis/policy.yaml` | Add `/health/` to allow-list |
| `metron/urls.py` | Add `/health/` route |
| New: `comicsdb/views/health.py` | Simple health check view |

---

## Cost Estimate (Phase 2)

Currently we absorb traffic spikes by vertical scaling (adding CPUs to the droplet). At some point horizontal scaling becomes more cost-effective and resilient, but it does require paying for separate managed services rather than co-locating everything on one machine.

| Service | Monthly cost |
|---------|-------------|
| DO Managed PostgreSQL (1 vCPU / 1 GB) | ~$15 |
| DO Managed Redis (1 GB) | ~$15 |
| DO Load Balancer | ~$12 |
| 2× web droplets (current RAM config) | ~$64 |
| **Total** | **~$106/month** |

> **Potential saving:** If we can reduce the RAM on each web droplet from 4 GB to 2 GB (feasible once the database and cache are offloaded), the two droplets drop to ~$48, bringing the total to **~$90/month**.

The main cost drivers are the managed databases — these are the price of making the app tier stateless enough to run on multiple nodes. Static and media files are already on DO Spaces, so no additional storage cost there.

---

## Verification

1. **Phase 1 validation (single node):**
   - After switching to managed DB: `python manage.py check --database default` passes; app loads normally.
   - After switching to managed Redis: cache operations work (test Select2 dropdowns in admin); thumbnail generation works.
   - After switching session backend: log in, verify session persists across requests; log out cleanly.

2. **Phase 2 validation (two nodes):**
   - Hit the health endpoint on both nodes directly: `curl https://<droplet-ip>:8443/health/`.
   - Send traffic through the DO Load Balancer; verify requests are distributed (check access logs on both nodes).
   - Log in through the LB; navigate several pages; verify session is consistent (works regardless of which node serves the request).
   - Trigger a rate-limit response; verify Anubis bot-protection still works correctly.
   - Run the full test suite against staging: `pytest`.
