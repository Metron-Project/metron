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

## 1. Create admin users and add SSH keys

These steps are performed as root (or the default admin user provided by
DigitalOcean) before any other setup. For each server admin, create a user
account, grant sudo access, set a temporary password, and install their SSH
public key:

```bash
# Create the admin account
useradd -m -G wheel <admin-username>

# Set a temporary password — share it with the admin out-of-band and force
# them to change it on first login
passwd <admin-username>
chage -d 0 <admin-username>

# Add their SSH public key
mkdir -p /home/<admin-username>/.ssh
chmod 700 /home/<admin-username>/.ssh
echo "<paste-public-key>" > /home/<admin-username>/.ssh/authorized_keys
chmod 600 /home/<admin-username>/.ssh/authorized_keys
chown -R <admin-username>:<admin-username> /home/<admin-username>/.ssh
```

On CentOS, members of the `wheel` group have full sudo access by default.

Repeat for each admin, then verify SSH key login works for each account before
disabling password authentication:

```bash
# Once all admins can log in with their keys, disable password auth
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart sshd
```

---

## 2. Provision the droplet

Install Podman and firewalld, then use firewalld to forward the standard
HTTP/HTTPS ports to unprivileged ports that the rootless nginx container binds
instead. This is more targeted than lowering the kernel's unprivileged port
start system-wide.

```bash
dnf install -y podman firewalld git
systemctl enable --now firewalld

# Forward external ports 80/443 to the ports the rootless nginx container
# binds (8080/8443). Masquerade is required for local port forwarding.
firewall-cmd --permanent --add-forward-port=port=80:proto=tcp:toport=8080
firewall-cmd --permanent --add-forward-port=port=443:proto=tcp:toport=8443
firewall-cmd --permanent --add-masquerade
firewall-cmd --reload
```

---

## 3. Create the deploy user

Create a dedicated `metron` service account and enable systemd linger so its
user services survive logout:

```bash
sudo useradd -m metron
sudo loginctl enable-linger metron
```

To allow other server admins to manage this user's services:

```bash
sudo usermod -aG metron <admin-username>
```

Admins can then switch to the service user with:

```bash
sudo -u metron -s
export XDG_RUNTIME_DIR=/run/user/$(id -u)
```

The `XDG_RUNTIME_DIR` export is required every time you switch to the metron
user via `sudo` — without it, `systemctl --user` commands will fail. You may
want to add it to the metron user's `~/.bashrc` so it is set automatically:

```bash
echo 'export XDG_RUNTIME_DIR=/run/user/$(id -u)' | sudo -u metron tee -a /home/metron/.bashrc
```

---

## 4. Clone the repo

```bash
sudo -u metron -s
export XDG_RUNTIME_DIR=/run/user/$(id -u)
cd ~
git clone https://github.com/Metron-Project/metron.git metron
```

---

## 5. Configure the environment file

```bash
mkdir -p ~/.config/containers
cp ~/metron/metron.env.example ~/.config/containers/metron.env
chmod 600 ~/.config/containers/metron.env
vi ~/.config/containers/metron.env   # fill in all values
```

---

## 6. Install Quadlet unit files

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

## 7. Obtain TLS certificates

### Install certbot

Certbot is not included with CentOS. Install it from EPEL:

```bash
sudo dnf install -y epel-release
sudo dnf install -y certbot
```

### Migrating from an existing droplet — copy existing certificates

While DNS still points at the old droplet, issuing a new certificate will fail
because Let's Encrypt cannot reach this droplet to complete the ACME challenge.
Copy the existing valid certificates from the old droplet instead:

```bash
mkdir -p ~/.local/share/metron/{letsencrypt,certbot-webroot}

# On the OLD droplet — archive the letsencrypt directory
sudo tar -czf /tmp/letsencrypt.tar.gz -C /etc letsencrypt

# Transfer to the new droplet
scp /tmp/letsencrypt.tar.gz metron@<new-droplet-ip>:/tmp/

# On the NEW droplet — extract into the user cert directory
tar -xzf /tmp/letsencrypt.tar.gz -C ~/.local/share/metron/letsencrypt \
  --strip-components=1
rm /tmp/letsencrypt.tar.gz
```

### Fresh deployment — issue a new certificate

For a **fresh deployment** with DNS already pointing at this droplet, use the
standalone method (nginx is not yet running). Because firewalld forwards
external port 80 to 8080, certbot must bind on 8080 so the ACME challenge
traffic reaches it:

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

## 8. Build the app image

```bash
cd ~/metron
podman build -t localhost/metron:latest .
```

---

## 9. Migrate data from the existing droplet

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

## 10. Start services

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

## Pre-cutover testing

You can test the new droplet fully before switching any traffic. Public DNS
keeps pointing at the old droplet throughout; only your local machine sees the
new one.

### Copy the existing TLS certificates from the old droplet

Rather than issuing new certs before the DNS cutover (which requires Let's
Encrypt to reach the new droplet via public DNS), copy the existing valid certs
from the old droplet:

```bash
# Run on the old droplet — archive the letsencrypt directory
sudo tar -czf /tmp/letsencrypt.tar.gz -C /etc letsencrypt

# Transfer to the new droplet
scp /tmp/letsencrypt-backup.tar.gz metron@<new-droplet-ip>:/tmp/

# Run on the new droplet — extract into the user cert directory
tar -xzf /tmp/letsencrypt.tar.gz -C ~/.local/share/metron/letsencrypt \
  --strip-components=1
rm /tmp/letsencrypt.tar.gz
```

### Override DNS on your local machine

Add a temporary entry to your local `/etc/hosts` so your browser resolves the
domain to the new droplet while everyone else still hits the old one:

```bash
# On your local machine
echo '<new-droplet-ip>  metron.cloud www.metron.cloud' | sudo tee -a /etc/hosts
```

Browse to `https://metron.cloud` and verify the site works end-to-end — login,
API, image loading from Spaces, etc. The TLS cert is valid because the domain
still matches.

When testing is complete, remove the hosts override:

```bash
# Remove the line added above
sudo sed -i '/<new-droplet-ip>/d' /etc/hosts
```

Then proceed with the cutover steps below.

---

## Cutover: switching traffic from the old droplet to the new one

The recommended approach is a **DigitalOcean Reserved IP**. Reassigning a
reserved IP between droplets takes effect in seconds with no DNS propagation
delay.

### Option A — Reserved IP (recommended, ~zero downtime)

**Before the maintenance window** (do this days in advance):

1. In the DigitalOcean control panel, go to **Networking → Reserved IPs**.
2. If the old droplet does not already have a reserved IP assigned, create one
   and assign it. This gives you a stable IP that is separate from the
   droplet's own IP.
3. Update your DNS A records to point `metron.cloud` and `www.metron.cloud` at
   the reserved IP (if they don't already).
4. Lower the TTL on those records to 60 seconds so any remaining DNS cache
   clears quickly on cutover day.
5. Complete all setup steps on the new droplet up through section 10, but do
   **not** yet do the final data restore — that happens in the maintenance
   window.

**During the maintenance window:**

```bash
# 1. On the OLD droplet — stop the web service to prevent new writes
sudo systemctl stop gunicorn   # adjust unit name as needed

# 2. On the OLD droplet — take a final database dump
sudo -u postgres pg_dump -Fc metron -f /tmp/metron-final.dump

# 3. Transfer the dump to the new droplet
scp /tmp/metron-final.dump metron@<new-droplet-ip>:/tmp/metron.dump

# 4. On the NEW droplet — restore (postgres must already be running)
podman exec -i metron-postgres pg_restore \
  --username {db_username} \
  --dbname {db_name} \
  --no-owner \
  --role {db_username} \
  --verbose \
  < /tmp/metron.dump
rm /tmp/metron.dump

# 5. On the NEW droplet — start remaining services
systemctl --user start metron-redis metron-web metron-nginx
```

Then in the DigitalOcean control panel, reassign the reserved IP from the old
droplet to the new droplet. Traffic switches immediately.

**Verify** the site is working on the new droplet, then restore the DNS TTL
to a normal value (e.g. 3600) and power off or destroy the old droplet once
satisfied.

---

### Option B — DNS cutover (no reserved IP)

Use this if a reserved IP is not available.

**Days before cutover**, lower the TTL on your DNS A records to 60 seconds so
the cache clears quickly when you update them.

Follow the same maintenance window steps as Option A (stop old service, final
dump, restore on new droplet), then update the DNS A records to point at the
new droplet's IP. Allow up to a few minutes for the low TTL to propagate.

Once the site is confirmed working, restore the TTL to a normal value (e.g.
3600) and decommission the old droplet.

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

## History cleanup

`django-simple-history` accumulates duplicate history entries over time.
Set up a systemd user timer to clean them up every 30 minutes.

Create the service unit at `~/.config/systemd/user/metron-history-cleanup.service`:

```ini
[Unit]
Description=Clean duplicate django-simple-history entries
After=metron-web.service
Requires=metron-web.service

[Service]
Type=oneshot
ExecStart=podman exec metron-web python manage.py clean_duplicate_history -m 40 --auto
```

Create the timer unit at `~/.config/systemd/user/metron-history-cleanup.timer`:

```ini
[Unit]
Description=Periodic django-simple-history duplicate cleanup

[Timer]
OnCalendar=*-*-* *:00,30:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start the timer:

```bash
systemctl --user daemon-reload
systemctl --user enable --now metron-history-cleanup.timer

# Verify it is scheduled
systemctl --user list-timers metron-history-cleanup.timer
```

---

## Database backups

### Manual backup

```bash
# Create a timestamped dump in custom format
podman exec metron-postgres pg_dump \
  -U {db_username} \
  -Fc {db_name} \
  -f /tmp/metron-$(date +%Y%m%d-%H%M%S).dump

# Copy the dump out of the container to the host
podman cp metron-postgres:/tmp/metron-*.dump ~/backups/
```

### Automated backups with a systemd timer

Create the service unit at `~/.config/systemd/user/metron-backup.service`:

```ini
[Unit]
Description=Metron PostgreSQL backup

[Service]
Type=oneshot
ExecStart=podman exec metron-postgres pg_dump \
  -U {db_username} -Fc {db_name} \
  -f /tmp/metron-backup.dump
ExecStartPost=podman cp metron-postgres:/tmp/metron-backup.dump \
  %h/backups/metron-%(%Y%m%d-%H%M%S)T.dump
```

Create the timer unit at `~/.config/systemd/user/metron-backup.timer`:

```ini
[Unit]
Description=Daily Metron database backup

[Timer]
OnCalendar=*-*-* 02:00:00
RandomizedDelaySec=30m
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start the timer:

```bash
mkdir -p ~/backups
systemctl --user daemon-reload
systemctl --user enable --now metron-backup.timer

# Verify it is scheduled
systemctl --user list-timers metron-backup.timer
```

### Restoring from a backup

```bash
# Copy the dump into the container
podman cp ~/backups/<dump-file> metron-postgres:/tmp/metron.dump

# Stop the web service to prevent writes during restore
systemctl --user stop metron-web

# Restore
podman exec metron-postgres pg_restore \
  --username {db_username} \
  --dbname {db_name} \
  --no-owner \
  --role {db_username} \
  --verbose \
  /tmp/metron.dump

# Clean up and restart
podman exec metron-postgres rm /tmp/metron.dump
systemctl --user start metron-web
```

### Pruning old backups

To keep only the last 30 days of backups, add this to the service unit:

```ini
ExecStartPost=find %h/backups -name 'metron-*.dump' -mtime +30 -delete
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
