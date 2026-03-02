# Ejournal Backend — Deployment Guide

Step-by-step: clone, deploy, and secure with SSL (Let's Encrypt).

---

## Prerequisites

- Ubuntu server (22.04 or 24.04)
- Docker & Docker Compose installed
- Domain pointing to your server IP (e.g. `api.uzfintex.uz` → your server)

---

## Step 1: DNS Setup

In your domain panel (e.g. ahost.uz), add an **A record**:

| Type | Name | RDATA (IP) | TTL |
|------|------|------------|-----|
| A    | api  | `YOUR_SERVER_IP` | 14400 |

This makes `api.yourdomain.uz` (or `api.uzfintex.uz`) point to your server.

Wait 5–15 minutes for DNS to propagate.

---

## Step 2: Clone Code on Server

```bash
ssh root@YOUR_SERVER_IP

cd /var/www
git clone https://github.com/YOUR_USERNAME/ejournal-back.git
cd ejournal-back
```

Replace with your actual repo URL.

---

## Step 3: Create Production `.env`

```bash
cp .env.docker.example .env
nano .env
```

Set:

```env
DEBUG=False
SECRET_KEY=GENERATE_A_LONG_RANDOM_STRING
ALLOWED_HOSTS=api.uzfintex.uz,www.api.uzfintex.uz,YOUR_SERVER_IP,localhost,127.0.0.1

DATABASE_URL=postgres://ejournal:CHANGE_THIS_PASSWORD@db:5432/ejournal
CELERY_BROKER_URL=redis://redis:6379/0

DJANGO_SETTINGS_MODULE=ejournal.settings.prod
USE_S3_STORAGE=False

# Email (optional, for notifications)
EMAIL_USE_PROVIDER=False
EMAIL_HOST=smtp.yourdomain.uz
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=noreply@uzfintex.uz
```

Generate `SECRET_KEY`:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

---

## Step 4: Use Production Settings in Docker

Edit `docker-compose.yml` — change `web` and `celery` environment:

```yaml
environment:
  DJANGO_SETTINGS_MODULE: ejournal.settings.prod
```

Or use the included prod override:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

---

## Step 5: Deploy with Docker

```bash
cd /var/www/ejournal-back
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Check:

```bash
docker compose ps
docker compose logs -f web
```

API should respond: `http://YOUR_SERVER_IP:8000/api/`

---

## Step 6: Nginx (HTTP first)

```bash
sudo cp deploy/nginx-ejournal.conf /etc/nginx/sites-available/ejournal-api
sudo ln -s /etc/nginx/sites-available/ejournal-api /etc/nginx/sites-enabled/
```

Edit if domain differs:

```bash
sudo nano /etc/nginx/sites-available/ejournal-api
# Set server_name api.uzfintex.uz;
# Set alias paths to /var/www/ejournal-back/media/ and .../staticfiles/
```

Test and reload:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

Verify: `http://api.uzfintex.uz/api/`

---

## Step 7: SSL Certificate (Let's Encrypt)

```bash
sudo apt update
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d api.uzfintex.uz -d www.api.uzfintex.uz
```

Follow prompts (email, agree to terms). Certbot will:

- Obtain a certificate
- Update Nginx for HTTPS
- Set up auto-renewal

---

## Step 8: Final Checks

1. **HTTPS works**: `https://api.uzfintex.uz/api/`
2. **Admin**: `https://api.uzfintex.uz/admin/` — `admin@ejournal.local` / `admin123`
3. **Sample users** (optional):

```bash
docker compose exec web python manage.py seed_db --sample-users
```

---

## Optional: Media/Static from Docker Volumes

If media/static are in Docker volumes, Nginx must serve from the host path. Add to `docker-compose.yml`:

```yaml
web:
  volumes:
    - .:/app
    - ./media:/app/media
    - ./staticfiles:/app/staticfiles
```

Then run `collectstatic` and ensure `/var/www/ejournal-back/media` and `.../staticfiles` exist and match Nginx `alias`.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| 502 Bad Gateway | Check `docker compose ps`, `docker compose logs web` |
| 404 on /media/ | Verify `alias` path and volume mount |
| Connection refused | Ensure port 8000 is open, firewall allows 80/443 |
| SSL not working | Run `sudo certbot --nginx -d api.uzfintex.uz` again |

---

## Quick Reference

```bash
# Restart
docker compose restart

# View logs
docker compose logs -f web celery

# Run migrations
docker compose exec web python manage.py migrate
```
