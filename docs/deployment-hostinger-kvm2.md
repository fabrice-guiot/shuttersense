# ShutterSense Deployment Plan: Hostinger KVM2

Complete deployment guide for ShutterSense on Hostinger KVM2 VPS with HTTPS-only access at `app.shuttersense.ai`.

## Table of Contents

1. [Infrastructure Overview](#1-infrastructure-overview)
2. [OS Selection](#2-os-selection)
3. [Domain Configuration (GoDaddy)](#3-domain-configuration-godaddy)
4. [Initial Server Setup](#4-initial-server-setup)
5. [Security Hardening](#5-security-hardening)
6. [PostgreSQL Setup](#6-postgresql-setup)
7. [Application Deployment](#7-application-deployment)
8. [HTTPS Certificate (Let's Encrypt)](#8-https-certificate-lets-encrypt)
9. [Nginx Reverse Proxy](#9-nginx-reverse-proxy)
10. [Systemd Services](#10-systemd-services)
11. [Database Seeding](#11-database-seeding)
12. [OAuth Configuration](#12-oauth-configuration)
13. [Final Verification](#13-final-verification)
14. [Maintenance & Backups](#14-maintenance--backups)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. Infrastructure Overview

### Target Configuration

| Component | Specification |
|-----------|---------------|
| **Provider** | Hostinger KVM2 |
| **vCPU** | 2 cores |
| **RAM** | 8 GB |
| **Storage** | 100 GB NVMe SSD |
| **Bandwidth** | 8 TB/month |
| **Domain** | app.shuttersense.ai |
| **DNS Provider** | GoDaddy |

### Architecture

```
Internet
    │
    ▼
┌─────────────────────────────────────────────────┐
│  Hostinger KVM2 (app.shuttersense.ai)           │
│  ┌─────────────────────────────────────────┐    │
│  │  UFW Firewall                           │    │
│  │  Allow: 22 (SSH), 80 (HTTP→redirect),   │    │
│  │         443 (HTTPS)                     │    │
│  └─────────────────────────────────────────┘    │
│                     │                           │
│                     ▼                           │
│  ┌─────────────────────────────────────────┐    │
│  │  Nginx (Reverse Proxy)                  │    │
│  │  - TLS termination (Let's Encrypt)      │    │
│  │  - HTTP → HTTPS redirect                │    │
│  │  - WebSocket proxy                      │    │
│  └─────────────────────────────────────────┘    │
│                     │                           │
│                     ▼ localhost:8000            │
│  ┌─────────────────────────────────────────┐    │
│  │  Gunicorn + Uvicorn (4 workers)         │    │
│  │  - FastAPI application                  │    │
│  │  - Serves API + SPA                     │    │
│  └─────────────────────────────────────────┘    │
│                     │                           │
│                     ▼ localhost:5432            │
│  ┌─────────────────────────────────────────┐    │
│  │  PostgreSQL 16                          │    │
│  │  - Database: shuttersense               │    │
│  │  - Local connections only               │    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

---

## 2. OS Selection

### Recommendation: Ubuntu 24.04 LTS

| Criteria | Ubuntu 24.04 LTS | Notes |
|----------|------------------|-------|
| **Support** | Until April 2029 | 5-year LTS support |
| **Python** | 3.12 (default) | Exceeds 3.11+ requirement |
| **PostgreSQL** | 16 via apt | Exceeds 12+ requirement |
| **Node.js** | 20.x via NodeSource | Meets 20+ requirement |
| **Security** | Auto-updates available | `unattended-upgrades` |
| **Hostinger** | First-class support | Pre-built image available |

**Why Ubuntu over alternatives:**
- **vs Debian**: Ubuntu has newer packages and better Hostinger integration
- **vs CentOS/Rocky**: apt ecosystem is simpler for this stack; better community support
- **vs Alpine**: Not suitable for VPS; designed for containers

### Hostinger OS Selection

When creating the KVM2 instance:
1. Select **Ubuntu 24.04 LTS** from the OS dropdown
2. Choose a datacenter close to your primary users
3. Set a strong root password (will be changed to key-based auth)

---

## 3. Domain Configuration (GoDaddy)

### DNS Records to Create

Log into GoDaddy DNS Management for `shuttersense.ai` and add:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| **A** | `app` | `<KVM2_IP_ADDRESS>` | 600 (10 min initially, increase later) |

### Verification

After creating the record, verify propagation:

```bash
# From your local machine
dig app.shuttersense.ai +short
# Should return: <KVM2_IP_ADDRESS>

# Or use online tool
nslookup app.shuttersense.ai
```

**Note:** DNS propagation can take up to 48 hours, but typically completes within 15-30 minutes for new records.

### Optional: CAA Record

Add a CAA record to restrict certificate issuance to Let's Encrypt:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| **CAA** | `app` | `0 issue "letsencrypt.org"` | 3600 |

---

## 4. Initial Server Setup

### 4.1 First Login

```bash
# SSH as root (use IP until DNS propagates)
ssh root@<KVM2_IP_ADDRESS>
```

### 4.2 System Update

```bash
apt update && apt upgrade -y
apt install -y software-properties-common curl wget git
```

### 4.3 Create Application User

```bash
# Create non-root user for running the application
useradd -m -s /bin/bash shuttersense
usermod -aG sudo shuttersense

# Set password (for sudo)
passwd shuttersense

# Create application directories
mkdir -p /opt/shuttersense
mkdir -p /var/log/shuttersense
chown -R shuttersense:shuttersense /opt/shuttersense /var/log/shuttersense
```

### 4.4 Configure SSH Key Authentication

```bash
# On your LOCAL machine, generate key if needed
ssh-keygen -t ed25519 -C "shuttersense-deploy"

# Copy public key to server
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@<KVM2_IP_ADDRESS>
ssh-copy-id -i ~/.ssh/id_ed25519.pub shuttersense@<KVM2_IP_ADDRESS>

# Test key-based login before proceeding
ssh shuttersense@<KVM2_IP_ADDRESS>
```

### 4.5 Set Timezone

```bash
timedatectl set-timezone UTC
# Or your preferred timezone:
# timedatectl set-timezone America/New_York
```

### 4.6 Set Hostname

```bash
hostnamectl set-hostname app-shuttersense
echo "127.0.0.1 app-shuttersense" >> /etc/hosts
```

---

## 5. Security Hardening

### 5.1 SSH Hardening

Edit `/etc/ssh/sshd_config`:

```bash
# Backup original
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

# Edit configuration
nano /etc/ssh/sshd_config
```

Apply these settings:

```
# Disable root login
PermitRootLogin no

# Disable password authentication (key-only)
PasswordAuthentication no
PubkeyAuthentication yes

# Disable empty passwords
PermitEmptyPasswords no

# Limit authentication attempts
MaxAuthTries 3

# Disable X11 forwarding
X11Forwarding no

# Set idle timeout (5 minutes)
ClientAliveInterval 300
ClientAliveCountMax 2

# Restrict to specific user (optional)
AllowUsers shuttersense
```

Restart SSH:

```bash
systemctl restart sshd
```

**WARNING:** Test SSH access in a NEW terminal before closing your current session!

### 5.2 UFW Firewall

```bash
# Install UFW
apt install -y ufw

# Default policies
ufw default deny incoming
ufw default allow outgoing

# Allow SSH (do this FIRST!)
ufw allow 22/tcp comment 'SSH'

# Allow HTTP (for Let's Encrypt verification and redirect)
ufw allow 80/tcp comment 'HTTP'

# Allow HTTPS
ufw allow 443/tcp comment 'HTTPS'

# Enable firewall
ufw enable

# Verify rules
ufw status verbose
```

Expected output:
```
Status: active

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW IN    Anywhere       # SSH
80/tcp                     ALLOW IN    Anywhere       # HTTP
443/tcp                    ALLOW IN    Anywhere       # HTTPS
```

### 5.3 Fail2ban

```bash
# Install
apt install -y fail2ban

# Create local configuration
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 5
backend = systemd

[sshd]
enabled = true
port = ssh
filter = sshd
maxretry = 3
bantime = 24h
EOF

# Start and enable
systemctl enable fail2ban
systemctl start fail2ban

# Verify
fail2ban-client status sshd
```

### 5.4 Automatic Security Updates

```bash
apt install -y unattended-upgrades

# Enable automatic updates
dpkg-reconfigure -plow unattended-upgrades
# Select "Yes" when prompted

# Verify configuration
cat /etc/apt/apt.conf.d/20auto-upgrades
```

### 5.5 Disable Unnecessary Services

```bash
# Check running services
systemctl list-units --type=service --state=running

# Common services to disable if not needed:
systemctl disable --now snapd.service snapd.socket 2>/dev/null || true
systemctl disable --now cups.service 2>/dev/null || true
```

---

## 6. PostgreSQL Setup

### 6.1 Install PostgreSQL 16

```bash
# Add PostgreSQL apt repository
sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /etc/apt/trusted.gpg.d/postgresql.gpg

# Install
apt update
apt install -y postgresql-16 postgresql-contrib-16
```

### 6.2 Configure PostgreSQL

```bash
# Switch to postgres user
sudo -u postgres psql
```

In the PostgreSQL shell:

```sql
-- Create database
CREATE DATABASE shuttersense;

-- Create application user with strong password
CREATE USER shuttersense_app WITH ENCRYPTED PASSWORD 'GENERATE_STRONG_PASSWORD_HERE';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE shuttersense TO shuttersense_app;

-- Connect to the database and grant schema privileges
\c shuttersense
GRANT ALL ON SCHEMA public TO shuttersense_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO shuttersense_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO shuttersense_app;

-- Exit
\q
```

**Generate a strong password:**
```bash
openssl rand -base64 32
```

### 6.3 PostgreSQL Security Configuration

Edit `/etc/postgresql/16/main/postgresql.conf`:

```bash
nano /etc/postgresql/16/main/postgresql.conf
```

Set these values:

```ini
# Listen only on localhost (no external connections)
listen_addresses = 'localhost'

# Performance tuning for 8GB RAM
shared_buffers = 2GB
effective_cache_size = 6GB
maintenance_work_mem = 512MB
work_mem = 64MB
max_connections = 50

# Logging
log_destination = 'stderr'
logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d.log'
log_rotation_age = 1d
log_rotation_size = 100MB
```

Edit `/etc/postgresql/16/main/pg_hba.conf`:

```bash
nano /etc/postgresql/16/main/pg_hba.conf
```

Ensure only local connections are allowed:

```
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             postgres                                peer
local   all             all                                     peer
host    shuttersense    shuttersense_app 127.0.0.1/32          scram-sha-256
host    all             all             0.0.0.0/0               reject
```

Restart PostgreSQL:

```bash
systemctl restart postgresql
systemctl enable postgresql
```

### 6.4 Verify PostgreSQL Setup

```bash
# Test connection
psql -h localhost -U shuttersense_app -d shuttersense -c "SELECT version();"
# Enter password when prompted
```

---

## 7. Application Deployment

### 7.1 Install Python 3.12

Ubuntu 24.04 includes Python 3.12 by default:

```bash
# Verify
python3 --version
# Python 3.12.x

# Install pip and venv
apt install -y python3-pip python3-venv python3-dev

# Install build dependencies
apt install -y build-essential libpq-dev
```

### 7.2 Install Node.js 20

```bash
# Add NodeSource repository
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -

# Install Node.js
apt install -y nodejs

# Verify
node --version
# v20.x.x
npm --version
```

### 7.3 Clone Repository

```bash
# Switch to application user
su - shuttersense

# Clone repository
cd /opt/shuttersense
git clone https://github.com/fabrice-guiot/shuttersense.git app
cd app

# Checkout the appropriate branch/tag
git checkout main  # or specific release tag
```

### 7.4 Backend Setup

```bash
# Create virtual environment
cd /opt/shuttersense/app
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r backend/requirements.txt

# Install gunicorn
pip install gunicorn
```

### 7.5 Frontend Build

```bash
cd /opt/shuttersense/app/frontend

# Install dependencies
npm ci

# Build for production
npm run build

# Verify build output
ls -la dist/
```

### 7.6 Environment Configuration

Create `/opt/shuttersense/app/.env`:

```bash
nano /opt/shuttersense/app/.env
```

```bash
# =============================================================================
# Database
# =============================================================================
SHUSAI_DB_URL=postgresql://shuttersense_app:YOUR_DB_PASSWORD@localhost:5432/shuttersense

# =============================================================================
# Security Keys (GENERATE UNIQUE VALUES!)
# =============================================================================
# Generate: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
SHUSAI_MASTER_KEY=

# Generate: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
SESSION_SECRET_KEY=

# Generate: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_SECRET_KEY=

# =============================================================================
# Production Settings
# =============================================================================
SHUSAI_ENV=production
SESSION_HTTPS_ONLY=true
SESSION_SAME_SITE=lax
CORS_ORIGINS=https://app.shuttersense.ai
SHUSAI_LOG_LEVEL=WARNING
SHUSAI_LOG_DIR=/var/log/shuttersense

# =============================================================================
# Application Paths
# =============================================================================
SHUSAI_SPA_DIST_PATH=/opt/shuttersense/app/frontend/dist

# =============================================================================
# OAuth 2.0 (Configure after initial setup)
# =============================================================================
OAUTH_REDIRECT_BASE_URL=https://app.shuttersense.ai

# Google OAuth
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# Microsoft OAuth (optional)
MICROSOFT_CLIENT_ID=
MICROSOFT_CLIENT_SECRET=

# =============================================================================
# Agent Security
# =============================================================================
REQUIRE_AGENT_ATTESTATION=true

# =============================================================================
# Super Admin (optional - SHA-256 hash of admin email)
# Generate: python3 -c "import hashlib; print(hashlib.sha256('admin@example.com'.lower().encode()).hexdigest())"
# =============================================================================
# SHUSAI_SUPER_ADMIN_HASHES=

# =============================================================================
# Web Push Notifications (optional)
# Generate: npx web-push generate-vapid-keys
# =============================================================================
# VAPID_PUBLIC_KEY=
# VAPID_PRIVATE_KEY=
# VAPID_SUBJECT=mailto:admin@shuttersense.ai
```

Set proper permissions:

```bash
chmod 600 /opt/shuttersense/app/.env
chown shuttersense:shuttersense /opt/shuttersense/app/.env
```

### 7.7 Generate Security Keys

Run these commands and add the output to `.env`:

```bash
cd /opt/shuttersense/app
source venv/bin/activate

# Generate SHUSAI_MASTER_KEY
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Generate SESSION_SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate JWT_SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 8. HTTPS Certificate (Let's Encrypt)

### 8.1 Install Certbot

```bash
# Exit to root user if still as shuttersense
exit

apt install -y certbot python3-certbot-nginx
```

### 8.2 Obtain Certificate

**Prerequisites:** DNS must be propagated (verify with `dig app.shuttersense.ai`).

```bash
# Obtain certificate (standalone mode, before nginx is configured)
certbot certonly --standalone -d app.shuttersense.ai \
  --non-interactive \
  --agree-tos \
  --email admin@shuttersense.ai \
  --no-eff-email
```

### 8.3 Verify Certificate

```bash
# Check certificate
certbot certificates

# Certificate files location:
# /etc/letsencrypt/live/app.shuttersense.ai/fullchain.pem
# /etc/letsencrypt/live/app.shuttersense.ai/privkey.pem
```

### 8.4 Auto-Renewal

Certbot installs a systemd timer for auto-renewal. Verify:

```bash
systemctl status certbot.timer
systemctl list-timers | grep certbot
```

Test renewal:

```bash
certbot renew --dry-run
```

---

## 9. Nginx Reverse Proxy

### 9.1 Install Nginx

```bash
apt install -y nginx
```

### 9.2 Configure Nginx

Create `/etc/nginx/sites-available/shuttersense`:

```bash
nano /etc/nginx/sites-available/shuttersense
```

```nginx
# HTTP -> HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name app.shuttersense.ai;

    # Let's Encrypt ACME challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # Redirect all other traffic to HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name app.shuttersense.ai;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/app.shuttersense.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.shuttersense.ai/privkey.pem;

    # SSL Security Settings
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;

    # Modern TLS configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # HSTS (uncomment after confirming HTTPS works)
    # add_header Strict-Transport-Security "max-age=63072000" always;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Logging
    access_log /var/log/nginx/shuttersense_access.log;
    error_log /var/log/nginx/shuttersense_error.log;

    # Request size limit (match FastAPI)
    client_max_body_size 10M;

    # WebSocket support for job progress
    location /api/tools/ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    # WebSocket support for agent pool status
    location /api/agent/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    # All other requests
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

### 9.3 Enable Site

```bash
# Remove default site
rm -f /etc/nginx/sites-enabled/default

# Enable ShutterSense site
ln -s /etc/nginx/sites-available/shuttersense /etc/nginx/sites-enabled/

# Test configuration
nginx -t

# Reload nginx
systemctl reload nginx
systemctl enable nginx
```

---

## 10. Systemd Services

### 10.1 ShutterSense Backend Service

Create `/etc/systemd/system/shuttersense.service`:

```bash
nano /etc/systemd/system/shuttersense.service
```

```ini
[Unit]
Description=ShutterSense Backend API
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=exec
User=shuttersense
Group=shuttersense
WorkingDirectory=/opt/shuttersense/app/backend
Environment="PATH=/opt/shuttersense/app/venv/bin"
EnvironmentFile=/opt/shuttersense/app/.env
ExecStart=/opt/shuttersense/app/venv/bin/gunicorn src.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    --access-logfile /var/log/shuttersense/access.log \
    --error-logfile /var/log/shuttersense/error.log \
    --capture-output \
    --timeout 120

Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# Security hardening
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/var/log/shuttersense /opt/shuttersense/app

[Install]
WantedBy=multi-user.target
```

### 10.2 Enable and Start Services

```bash
# Reload systemd
systemctl daemon-reload

# Enable services
systemctl enable shuttersense

# Start services
systemctl start shuttersense

# Check status
systemctl status shuttersense
```

### 10.3 View Logs

```bash
# Backend logs
journalctl -u shuttersense -f

# Or file-based logs
tail -f /var/log/shuttersense/error.log
tail -f /var/log/shuttersense/access.log

# Nginx logs
tail -f /var/log/nginx/shuttersense_error.log
```

---

## 11. Database Seeding

### 11.1 Run Database Migrations

```bash
su - shuttersense
cd /opt/shuttersense/app
source venv/bin/activate

# Set environment
export $(grep -v '^#' .env | xargs)

# Run migrations
cd backend
alembic upgrade head
```

### 11.2 Seed First Team and Admin

```bash
# Still as shuttersense user with venv activated
cd /opt/shuttersense/app

python -m backend.src.scripts.seed_first_team \
    --team-name "Your Team Name" \
    --admin-email "admin@yourdomain.com"
```

Expected output:
```
==================================================
ShutterSense: First Team Seed Script
==================================================

[CREATED] Team: Your Team Name
  GUID: tea_01hgw2bbg...
  Slug: your-team-name

[SEEDED] Default data for team
  Categories: 7
  Event statuses: 4
  TTL configs: 3

[CREATED] User: admin@yourdomain.com
  GUID: usr_01hgw2bbg...
  Status: pending

==================================================
SEED COMPLETE

Team GUID:  tea_01hgw2bbg...
Admin GUID: usr_01hgw2bbg...

Next steps:
  1. Configure OAuth providers in .env
  2. Start the server
  3. Login with admin@yourdomain.com via OAuth
```

---

## 12. OAuth Configuration

### 12.1 Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new project or select existing
3. Configure OAuth consent screen:
   - User Type: External
   - App name: ShutterSense
   - User support email: your email
   - Authorized domains: `shuttersense.ai`
4. Create OAuth 2.0 Client ID:
   - Application type: Web application
   - Name: ShutterSense Production
   - Authorized redirect URIs: `https://app.shuttersense.ai/auth/callback/google`
5. Copy Client ID and Client Secret to `.env`:
   ```
   GOOGLE_CLIENT_ID=xxxxx.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=GOCSPX-xxxxx
   ```

### 12.2 Microsoft OAuth Setup (Optional)

1. Go to [Azure Portal](https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps)
2. Register new application:
   - Name: ShutterSense
   - Supported account types: Accounts in any organizational directory and personal Microsoft accounts
   - Redirect URI: `https://app.shuttersense.ai/auth/callback/microsoft`
3. Create client secret under "Certificates & secrets"
4. Copy values to `.env`:
   ```
   MICROSOFT_CLIENT_ID=xxxxx
   MICROSOFT_CLIENT_SECRET=xxxxx
   ```

### 12.3 Restart After OAuth Configuration

```bash
systemctl restart shuttersense
```

---

## 13. Final Verification

### 13.1 Service Health Checks

```bash
# Check all services are running
systemctl status postgresql
systemctl status shuttersense
systemctl status nginx

# Check listening ports (should only see localhost for 8000 and 5432)
ss -tlnp | grep -E '(8000|5432|80|443)'
```

Expected output:
```
LISTEN  0  128  127.0.0.1:8000   0.0.0.0:*    users:(("gunicorn",...))
LISTEN  0  244  127.0.0.1:5432   0.0.0.0:*    users:(("postgres",...))
LISTEN  0  511    0.0.0.0:80     0.0.0.0:*    users:(("nginx",...))
LISTEN  0  511    0.0.0.0:443    0.0.0.0:*    users:(("nginx",...))
```

### 13.2 External Access Tests

From your local machine:

```bash
# HTTP redirects to HTTPS
curl -I http://app.shuttersense.ai
# Should show: HTTP/1.1 301 Moved Permanently
# Location: https://app.shuttersense.ai/

# HTTPS health check
curl https://app.shuttersense.ai/health
# Should return: {"status":"healthy","version":"...","database":"connected"}

# API version
curl https://app.shuttersense.ai/api/version
```

### 13.3 SSL Certificate Verification

```bash
# Check certificate
openssl s_client -connect app.shuttersense.ai:443 -servername app.shuttersense.ai < /dev/null 2>/dev/null | openssl x509 -noout -dates

# Or use SSL Labs (comprehensive test)
# https://www.ssllabs.com/ssltest/analyze.html?d=app.shuttersense.ai
```

### 13.4 Login Test

1. Open `https://app.shuttersense.ai` in browser
2. Click "Sign in with Google" (or Microsoft)
3. Authenticate with the admin email used in seeding
4. Verify dashboard loads successfully

---

## 14. Maintenance & Backups

### 14.1 Database Backup Script

Create `/opt/shuttersense/scripts/backup-db.sh`:

```bash
mkdir -p /opt/shuttersense/scripts
nano /opt/shuttersense/scripts/backup-db.sh
```

```bash
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/opt/shuttersense/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/shuttersense_${TIMESTAMP}.sql.gz"
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

# Create backup
sudo -u postgres pg_dump shuttersense | gzip > "$BACKUP_FILE"

# Set permissions
chmod 600 "$BACKUP_FILE"
chown shuttersense:shuttersense "$BACKUP_FILE"

# Delete old backups
find "$BACKUP_DIR" -name "shuttersense_*.sql.gz" -mtime +${RETENTION_DAYS} -delete

echo "Backup created: $BACKUP_FILE"
```

```bash
chmod +x /opt/shuttersense/scripts/backup-db.sh
```

### 14.2 Automated Backup Cron

```bash
crontab -e
```

Add:
```
# Daily database backup at 3 AM
0 3 * * * /opt/shuttersense/scripts/backup-db.sh >> /var/log/shuttersense/backup.log 2>&1
```

### 14.3 Application Updates

```bash
# Switch to shuttersense user
su - shuttersense
cd /opt/shuttersense/app

# Pull latest changes
git fetch origin
git pull origin main

# Update backend dependencies
source venv/bin/activate
pip install -r backend/requirements.txt

# Rebuild frontend
cd frontend
npm ci
npm run build

# Run migrations
cd ../backend
alembic upgrade head

# Exit to root and restart service
exit
systemctl restart shuttersense
```

### 14.4 Log Rotation

Create `/etc/logrotate.d/shuttersense`:

```bash
nano /etc/logrotate.d/shuttersense
```

```
/var/log/shuttersense/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 shuttersense shuttersense
    sharedscripts
    postrotate
        systemctl reload shuttersense > /dev/null 2>&1 || true
    endscript
}
```

### 14.5 Critical Keys Backup

**IMPORTANT:** Store these keys securely (password manager, encrypted vault):

1. `SHUSAI_MASTER_KEY` - Losing this means encrypted credentials are unrecoverable
2. `SESSION_SECRET_KEY` - Changing invalidates all sessions
3. `JWT_SECRET_KEY` - Changing invalidates all API tokens
4. Database password

---

## 15. Troubleshooting

### 15.1 Service Won't Start

```bash
# Check detailed logs
journalctl -u shuttersense -n 100 --no-pager

# Common issues:
# - Missing .env file or permissions
# - Database connection failed
# - Port already in use
```

### 15.2 502 Bad Gateway

```bash
# Check if backend is running
systemctl status shuttersense
curl http://127.0.0.1:8000/health

# Check nginx error log
tail -f /var/log/nginx/shuttersense_error.log
```

### 15.3 Database Connection Issues

```bash
# Test PostgreSQL is running
systemctl status postgresql

# Test connection manually
psql -h localhost -U shuttersense_app -d shuttersense -c "SELECT 1;"

# Check pg_hba.conf if authentication fails
cat /etc/postgresql/16/main/pg_hba.conf
```

### 15.4 SSL Certificate Issues

```bash
# Check certificate status
certbot certificates

# Force renewal
certbot renew --force-renewal

# Check nginx config
nginx -t
```

### 15.5 OAuth Redirect Issues

- Verify `OAUTH_REDIRECT_BASE_URL` matches exactly: `https://app.shuttersense.ai`
- Check Google/Microsoft console has correct redirect URI
- Ensure no trailing slashes in URLs

### 15.6 Performance Issues

```bash
# Check resource usage
htop
free -h
df -h

# Check PostgreSQL connections
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"

# Check gunicorn workers
ps aux | grep gunicorn
```

---

## Appendix: Quick Reference Commands

```bash
# Service management
systemctl status shuttersense
systemctl restart shuttersense
systemctl stop shuttersense
journalctl -u shuttersense -f

# Database
sudo -u postgres psql -d shuttersense
/opt/shuttersense/scripts/backup-db.sh

# SSL
certbot certificates
certbot renew --dry-run

# Firewall
ufw status verbose

# Logs
tail -f /var/log/shuttersense/error.log
tail -f /var/log/nginx/shuttersense_error.log
```

---

## Security Checklist

- [ ] SSH key-only authentication enabled
- [ ] Root login disabled
- [ ] UFW firewall active (only 22, 80, 443 open)
- [ ] Fail2ban protecting SSH
- [ ] PostgreSQL listening only on localhost
- [ ] Gunicorn listening only on localhost
- [ ] HTTPS-only access enforced
- [ ] Let's Encrypt auto-renewal configured
- [ ] Strong passwords/keys generated
- [ ] Automatic security updates enabled
- [ ] Log rotation configured
- [ ] Database backups scheduled
- [ ] Critical keys backed up securely
