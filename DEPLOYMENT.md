# Deployment Guide (Podman / CentOS)

This guide covers deploying Metron on a fresh CentOS droplet using rootless Podman
with Quadlet (systemd-managed containers).

## Architecture

```
internet (80/443) → firewalld → nginx (host 8080/8443 → container 80/443)
                                      ↓
                              metron-web (gunicorn :8000)
                                      ↓
                          metron-postgres  metron-redis
```

All containers share the `metron` bridge network. Static and media files are
served from DigitalOcean Spaces (S3-compatible); the containers have no local
file storage responsibility beyond database and cache data volumes.

---

## 1. Provision the droplet

Install Podman, then use firewalld (enabled by default on CentOS) to forward
the standard HTTP/HTTPS ports to unprivileged ports that the rootless nginx
container binds instead. This is more targeted than lowering the kernel's
unprivileged port start system-wide.

```bash
sudo dnf install -y podman

# Forward external ports 80/443 to the ports the rootless nginx container
# binds (8080/8443). Masquerade is required for local port forwarding.
sudo firewall-cmd --permanent --add-forward-port=port=80:proto=tcp:toport=8080
sudo firewall-cmd --permanent --add-forward-port=port=443:proto=tcp:toport=8443
sudo firewall-cmd --permanent --add-masquerade
sudo firewall-cmd --reload
```

---

## 2. Create the deploy user

Create a dedicated `metron` service account and enable systemd linger so its
user services survive logout:

```bash
sudo useradd -m metron
sudo loginctl enable-linger metron
```

To allow other server admins to manage this user's services:

```bash
sudo usermod -aG metron <admin-username>
# Admins can then run commands as the service user with:
#   sudo -u metron -s
```

---

## 3. Clone the repo

```bash
sudo -u metron -s
cd ~
git clone https://github.com/Metron-Project/metron.git metron
```

---

## 4. Configure the environment file

```bash
mkdir -p ~/.config/containers
cp ~/metron/metron.env.example ~/.config/containers/metron.env
chmod 600 ~/.config/containers/metron.env
nano ~/.config/containers/metron.env   # fill in all values
```

---

## 5. Install Quadlet unit files

Quadlet reads `.container`, `.network`, and `.volume` files from
`~/.config/containers/systemd/` and generates systemd user units automatically.

```bash
mkdir -p ~/.config/containers/systemd
cp ~/metron/.quadlet/* ~/.config/containers/systemd/
systemctl --user daemon-reload
```

Verify the units were generated without errors:

```bash
systemctl --user list-unit-files 'metron-*'
```

---

## 6. Obtain TLS certificates

### Install certbot

Certbot is not included with CentOS. Install it from EPEL:

```bash
sudo dnf install -y epel-release
sudo dnf install -y certbot
```

### Get the initial certificate

Use the standalone method (nginx is not yet running). Because firewalld
forwards external port 80 to 8080, certbot must bind on 8080 so the ACME
challenge traffic reaches it:

```bash
mkdir -p ~/.local/share/metron/{letsencrypt,certbot-webroot}

sudo certbot certonly --standalone \
  --http-01-port 8080 \
  -d metron.cloud -d www.metron.cloud \
  --config-dir /home/metron/.local/share/metron/letsencrypt \
  --work-dir /tmp/certbot \
  --logs-dir /tmp/certbot-logs

sudo chown -R metron:metron ~/.local/share/metron/letsencrypt
```

### Certificate renewal

Once nginx is running, renewals use the webroot method. Set up a systemd user
timer so renewal runs automatically as the `metron` user.

Create the service unit at `~/.config/systemd/user/certbot-renew.service`:

```ini
[Unit]
Description=Certbot renewal for metron.cloud

[Service]
Type=oneshot
ExecStart=certbot renew \
  --webroot -w %h/.local/share/metron/certbot-webroot \
  --config-dir %h/.local/share/metron/letsencrypt \
  --work-dir /tmp/certbot \
  --logs-dir /tmp/certbot-logs
ExecStartPost=systemctl --user reload metron-nginx
```

Create the timer unit at `~/.config/systemd/user/certbot-renew.timer`:

```ini
[Unit]
Description=Twice-daily certbot renewal check

[Timer]
OnCalendar=*-*-* 03,15:00:00
RandomizedDelaySec=1h
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start the timer:

```bash
systemctl --user daemon-reload
systemctl --user enable --now certbot-renew.timer

# Verify the timer is scheduled
systemctl --user list-timers certbot-renew.timer
```

---

## 7. Build the app image

```bash
cd ~/metron
podman build -t localhost/metron:latest .
```

---

## 8. Migrate data from the existing droplet

Follow these steps when rebuilding from an existing droplet to preserve all database data.

### 8a. Dump the database on the old droplet

SSH into the old Ubuntu droplet and create a dump. Stop the web service first to avoid writes during the dump:

```bash
# Stop the web service on the old droplet
sudo systemctl stop gunicorn
# Dump the database in custom format (compressed, supports parallel restore)
sudo -u postgres pg_dump -Fc metron -f /tmp/metron.dump

# Verify the dump is non-empty
ls -lh /tmp/metron.dump
```

### 8b. Transfer the dump to the new droplet

From your local machine, or directly between droplets:

```bash
# From your local machine
scp old-droplet:/tmp/metron.dump /tmp/metron.dump
scp /tmp/metron.dump new-droplet:/tmp/metron.dump

# Or directly between droplets (run on the old droplet)
scp /tmp/metron.dump metron@<new-droplet-ip>:/tmp/metron.dump
```

### 8c. Restore the database on the new droplet

Start only Postgres first (the web service must not run until data is restored):

```bash
systemctl --user start metron-postgres

# Wait for Postgres to be ready
sleep 5

# Restore the dump into the running container
podman exec -i metron-postgres pg_restore \
  --username {db_username} \
  --dbname metron \
  --no-owner \
  --role {db_username} \
  --verbose \
  < /tmp/metron.dump

# Remove the dump file once confirmed
rm /tmp/metron.dump
```

If the restore prints errors about existing objects or ownership, those are
typically harmless. Verify the data looks correct before continuing:

```bash
podman exec -it metron-postgres psql -U metron -d metron \
  -c "SELECT COUNT(*) FROM comicsdb_issue;"
```

---

## 9. Start services

Start Redis and the app, then nginx:

```bash
systemctl --user start metron-redis
systemctl --user start metron-web

# Now start nginx
systemctl --user start metron-nginx
```

> **Fresh install only:** if you are not restoring from a dump, run these
> before starting nginx:
> ```bash
> podman exec metron-web python manage.py migrate
> podman exec metron-web python manage.py collectstatic --no-input
> ```
>
> When restoring from an existing droplet the schema and static files are
> already in place — `migrate` is a no-op and static files live on
> DigitalOcean Spaces, so `collectstatic` is not needed either.

Enable all services to start automatically on boot:

```bash
systemctl --user enable metron-postgres metron-redis metron-web metron-nginx
```

---

## Updating the application

```bash
sudo -u metron -s
cd ~/metron
git pull
podman build -t localhost/metron:latest .
systemctl --user restart metron-web
podman exec metron-web python manage.py migrate
# Re-run collectstatic only if static assets changed:
# podman exec metron-web python manage.py collectstatic --no-input
```

---

## Useful commands

```bash
# Check service status
systemctl --user status metron-web

# Follow logs for a service
journalctl --user -u metron-web -f

# Follow logs for all metron services
journalctl --user -u 'metron-*' -f

# Open a shell in the web container
podman exec -it metron-web bash

# Open a psql shell
podman exec -it metron-postgres psql -U metron -d metron

# Reload nginx config without downtime
systemctl --user reload metron-nginx

# Restart all services
systemctl --user restart metron-postgres metron-redis metron-web metron-nginx
```

---

## File locations on the droplet

| Path | Purpose |
|---|---|
| `~/metron/` | Cloned repository |
| `~/.config/containers/metron.env` | Secrets / environment variables (mode 0600) |
| `~/.config/containers/systemd/` | Quadlet unit files |
| `~/.local/share/metron/letsencrypt/` | Let's Encrypt certificates |
| `~/.local/share/metron/certbot-webroot/` | ACME challenge webroot |
| Podman named volumes | Postgres and Redis data (managed by Podman) |
