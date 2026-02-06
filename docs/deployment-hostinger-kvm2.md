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
13. [Geofencing (Optional)](#13-geofencing-optional)
14. [Final Verification](#14-final-verification)
15. [Maintenance & Backups](#15-maintenance--backups)
16. [Troubleshooting](#16-troubleshooting)

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
│  Hostinger Cloud Firewall (hPanel)              │
│  - Filters traffic BEFORE reaching VPS          │
│  - Allow: 22 (SSH), 80 (HTTP), 443 (HTTPS)      │
│  - Optional: Restrict SSH to specific IPs       │
└─────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────┐
│  Hostinger KVM2 (app.shuttersense.ai)           │
│  ┌─────────────────────────────────────────┐    │
│  │  UFW Firewall + Fail2ban                │    │
│  │  - OS-level filtering (defense-in-depth)│    │
│  │  - Dynamic IP blocking on abuse         │    │
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
│  │  - Rate limiting (slowapi)              │    │
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

### 5.2 Hostinger Managed Firewall (hPanel)

Hostinger provides a cloud-level firewall that filters traffic **before** it reaches your VPS. This reduces server resource usage and provides defense-in-depth alongside UFW.

#### Why Use Both Firewalls?

| Layer | Firewall | Purpose |
|-------|----------|---------|
| **Cloud** | Hostinger Managed | Blocks traffic at infrastructure level, before it hits your VPS |
| **OS** | UFW | Blocks traffic at the kernel level, defense-in-depth |
| **Application** | Fail2ban | Dynamic blocking based on application behavior |

#### 5.2.1 Create Firewall Configuration

1. Log into [Hostinger hPanel](https://hpanel.hostinger.com)
2. Select your KVM2 VPS
3. Navigate to **Security → Firewall**
4. Click **Create firewall configuration**
5. Name it: `shuttersense-production`

#### 5.2.2 Configure Inbound Rules

Add the following rules in order (Hostinger applies a default "drop all" rule at the end):

| Rule | Protocol | Port | Source | Action | Description |
|------|----------|------|--------|--------|-------------|
| 1 | TCP | 22 | Your IP / Office IP | Accept | SSH (restricted) |
| 2 | TCP | 22 | Backup IP (optional) | Accept | SSH failsafe |
| 3 | TCP | 80 | Anywhere (0.0.0.0/0) | Accept | HTTP (Let's Encrypt + redirect) |
| 4 | TCP | 443 | Anywhere (0.0.0.0/0) | Accept | HTTPS |
| 5 | ICMP | - | Anywhere | Accept | Ping (optional, for monitoring) |

**Important Notes:**
- Rule 1 restricts SSH to specific IPs for maximum security
- If you don't have a static IP, use `0.0.0.0/0` for SSH but rely on fail2ban
- The default "drop" rule blocks everything not explicitly allowed

#### 5.2.3 Recommended: Restrict SSH to Known IPs

For production servers, restrict SSH access to specific IPs:

```
Your home/office IP:     203.0.113.50/32
VPN exit IP:             198.51.100.0/24
Cloud IDE IP (if used):  192.0.2.100/32
```

To find your current IP:
```bash
curl -4 ifconfig.me
```

#### 5.2.4 Apply Configuration

1. After adding rules, click **Activate** or **Apply to server**
2. The firewall applies immediately to new connections
3. Existing SSH sessions are preserved during changes

#### 5.2.5 Verify Firewall is Active

In hPanel, the firewall status should show:
- Configuration: `shuttersense-production`
- Status: **Active**
- Rules: 4-5 inbound rules

#### 5.2.6 Emergency Access

If you lock yourself out via the Hostinger firewall:
1. Log into hPanel
2. Navigate to **Security → Firewall**
3. Either disable the firewall temporarily or add your new IP
4. Use hPanel's **Console** for emergency SSH access (browser-based)

### 5.3 UFW Firewall (OS-Level)

UFW provides OS-level filtering as a second layer of defense. Even if the Hostinger firewall is misconfigured, UFW protects your server.

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

### 5.4 Fail2ban

Fail2ban protects against brute-force attacks on both SSH and web application authentication.

#### 5.4.1 Install Fail2ban

```bash
apt install -y fail2ban
```

#### 5.4.2 Create Nginx Rate Limit Filter

Create `/etc/fail2ban/filter.d/nginx-limit-req.conf`:

```bash
cat > /etc/fail2ban/filter.d/nginx-limit-req.conf << 'EOF'
# Fail2ban filter for nginx rate limiting and bad requests
# Catches clients hitting rate limits or sending malformed requests

[Definition]

# Rate limit exceeded (429 responses)
failregex = ^<HOST> .* "(GET|POST|PUT|DELETE|PATCH) [^"]*" 429 .*$
            ^<HOST> .* "(GET|POST|PUT|DELETE|PATCH) [^"]*" 401 .*$
            limiting requests, excess:.* by zone.*client: <HOST>

# Ignore normal traffic
ignoreregex = ^<HOST> .* "(GET|POST) /health.*" 200 .*$
              ^<HOST> .* "(GET|POST) /api/version.*" 200 .*$
EOF
```

#### 5.4.3 Create ShutterSense Auth Filter

Create `/etc/fail2ban/filter.d/shuttersense-auth.conf`:

```bash
cat > /etc/fail2ban/filter.d/shuttersense-auth.conf << 'EOF'
# Fail2ban filter for ShutterSense OAuth login failures
# Matches JSON log entries with client_ip field and auth.login.failed event

[Definition]
failregex = ^.*"client_ip":\s*"<HOST>".*"event":\s*"auth\.login\.failed".*$

ignoreregex = ^.*"event":\s*"auth\.login\.success".*$
EOF
```

#### 5.4.4 Create ShutterSense Token Filter

Create `/etc/fail2ban/filter.d/shuttersense-token.conf`:

```bash
cat > /etc/fail2ban/filter.d/shuttersense-token.conf << 'EOF'
# Fail2ban filter for ShutterSense API token brute-force
# Matches SEC-13 warning messages with IP addresses

[Definition]
failregex = ^.*SEC-13: IP <HOST> has \d+ failed token validations.*$

ignoreregex =
EOF
```

#### 5.4.5 Configure Jail Rules

Create `/etc/fail2ban/jail.local`:

```bash
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
# Default ban settings
bantime = 1h
findtime = 10m
maxretry = 5
backend = auto
banaction = ufw

# =============================================================================
# SSH Protection
# =============================================================================
[sshd]
enabled = true
port = ssh
filter = sshd
maxretry = 3
bantime = 24h
findtime = 10m

# =============================================================================
# Nginx Protection (enabled after nginx is installed in section 9)
# =============================================================================
[nginx-http-auth]
enabled = false
port = http,https
filter = nginx-http-auth
logpath = /var/log/nginx/shuttersense_error.log
maxretry = 5
bantime = 1h

[nginx-limit-req]
enabled = false
port = http,https
filter = nginx-limit-req
logpath = /var/log/nginx/shuttersense_access.log
maxretry = 10
findtime = 1m
bantime = 30m

[nginx-botsearch]
enabled = false
port = http,https
filter = nginx-botsearch
logpath = /var/log/nginx/shuttersense_access.log
maxretry = 2
bantime = 1d

# =============================================================================
# ShutterSense Application Protection
# =============================================================================
[shuttersense-auth]
enabled = true
port = http,https
filter = shuttersense-auth
logpath = /var/log/shuttersense/auth.log
maxretry = 5
findtime = 5m
bantime = 1h

[shuttersense-token]
enabled = true
port = http,https
filter = shuttersense-token
logpath = /var/log/shuttersense/api.log
maxretry = 10
findtime = 5m
bantime = 2h

# =============================================================================
# Recidive (repeat offenders)
# =============================================================================
[recidive]
enabled = true
filter = recidive
logpath = /var/log/fail2ban.log
bantime = 1w
findtime = 1d
maxretry = 3
EOF
```

#### 5.4.6 Configure Nginx to Log Client IPs

For fail2ban to work correctly, nginx must log the real client IP. Update the nginx log format if using a CDN or proxy.

Edit `/etc/nginx/nginx.conf` and ensure this log format exists:

```nginx
http {
    # Log format with real client IP
    log_format main '$remote_addr - $remote_user [$time_local] '
                    '"$request" $status $body_bytes_sent '
                    '"$http_referer" "$http_user_agent"';

    # Use main format for access logs
    access_log /var/log/nginx/access.log main;
}
```

#### 5.4.7 Start and Enable Fail2ban

```bash
# Start and enable
systemctl enable fail2ban
systemctl start fail2ban

# Verify jails are running (only sshd and recidive at this point)
fail2ban-client status

# Check SSH jail status
fail2ban-client status sshd
```

> **Note:** The nginx jails are disabled at this stage because nginx is not yet installed.
> They will be enabled in section 9.4 (after nginx is configured).
> The ShutterSense application jails (`shuttersense-auth`, `shuttersense-token`) are enabled
> but will only activate once the application is deployed and logging to the configured paths.

Expected output:
```
Status
|- Number of jail:      7
`- Jail list:   nginx-botsearch, nginx-http-auth, nginx-limit-req, recidive, shuttersense-auth, shuttersense-token, sshd
```

#### 5.4.8 Fail2ban Management Commands

```bash
# View banned IPs for a jail
fail2ban-client status sshd

# Manually ban an IP
fail2ban-client set sshd banip 1.2.3.4

# Manually unban an IP
fail2ban-client set sshd unbanip 1.2.3.4

# Check if an IP is banned
fail2ban-client get sshd banned 1.2.3.4

# View fail2ban log
tail -f /var/log/fail2ban.log
```

#### 5.4.9 Protection Summary

| Jail | Protects Against | Max Retries | Ban Duration |
|------|------------------|-------------|--------------|
| `sshd` | SSH brute-force | 3 in 10m | 24 hours |
| `nginx-http-auth` | Basic auth attacks | 5 in 10m | 1 hour |
| `nginx-limit-req` | Rate limit abuse | 10 in 1m | 30 minutes |
| `nginx-botsearch` | Vulnerability scanners | 2 in 10m | 1 day |
| `shuttersense-auth` | OAuth login abuse | 5 in 5m | 1 hour |
| `shuttersense-token` | API token brute-force | 10 in 5m | 2 hours |
| `recidive` | Repeat offenders | 3 bans/day | 1 week |

### 5.5 Automatic Security Updates

```bash
apt install -y unattended-upgrades

# Enable automatic updates
dpkg-reconfigure -plow unattended-upgrades
# Select "Yes" when prompted

# Verify configuration
cat /etc/apt/apt.conf.d/20auto-upgrades
```

### 5.6 Disable Unnecessary Services

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

Ensure only local connections are allowed (replace the entire file contents):

```
# TYPE  DATABASE        USER            ADDRESS                 METHOD

# Local socket connections (administrative access)
local   all             postgres                                peer
local   all             all                                     peer

# IPv4 localhost - application connection
host    shuttersense    shuttersense_app 127.0.0.1/32          scram-sha-256

# IPv6 localhost - application connection
host    shuttersense    shuttersense_app ::1/128               scram-sha-256

# Reject all other connections (IPv4 and IPv6)
host    all             all             0.0.0.0/0               reject
host    all             all             ::/0                    reject
```

**Note:** This configuration explicitly removes the default replication rules since this is a single-server deployment. If you need streaming replication later, add appropriate rules at that time.

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

# Checkout the appropriate branch/tag (clone fetches all tags by default)
git checkout main  # or specific release tag, e.g., git checkout v1.2.3
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

### 7.6 Production Cleanup

After building, remove development artifacts that aren't needed at runtime. This reduces disk usage, improves security by removing source code, and eliminates potential information leakage.

Maintenance scripts are maintained in the repository under `scripts/`. Copy them to the server scripts directory:

```bash
# Copy all maintenance scripts to server scripts directory
mkdir -p /opt/shuttersense/scripts
cp /opt/shuttersense/app/scripts/*.sh /opt/shuttersense/scripts/
chmod +x /opt/shuttersense/scripts/*.sh

# Preview what will be removed (dry run)
/opt/shuttersense/scripts/production-cleanup.sh --dry-run

# Execute cleanup
/opt/shuttersense/scripts/production-cleanup.sh
```

#### What Gets Removed

| Category | Items Removed | Space Saved |
|----------|---------------|-------------|
| Dev tools | `.claude/`, `.specify/`, `.vscode/`, `.github/` | ~200 KB |
| Specs | `specs/` (27 directories) | ~5 MB |
| Tests | `*/tests/`, `.pytest_cache/`, coverage | ~2 MB |
| Frontend source | `frontend/src/`, `frontend/node_modules/` | ~500 MB |
| Agent source | `agent/src/`, `agent/cli/`, `agent/packaging/` | ~1 MB |
| Python cache | `__pycache__/`, `*.pyc` | Variable |
| Dev configs | `CLAUDE.md`, `CONTRIBUTING.md`, etc. | ~50 KB |

**Total typical savings: ~500+ MB**

#### What Remains After Cleanup

```
/opt/shuttersense/app/
├── backend/
│   └── src/              # Backend source (required for runtime)
├── frontend/
│   └── dist/             # Built frontend assets only
├── templates/            # Jinja2 report templates
├── utils/                # Shared utilities
├── docs/                 # Deployment documentation (optional)
├── version.py            # Version management
├── requirements.txt      # Python dependencies reference
├── venv/                 # Python virtual environment
└── .env                  # Environment configuration
```

#### Important Notes

1. **Run after every deployment** - New deployments will restore removed files
2. **Git history** - Keeping `.git/` allows `git pull` updates; removing saves ~50MB
3. **Agent binaries** - If distributing agents from this server, keep `agent/dist/`
4. **Reversible** - A fresh `git checkout` restores all files
5. **Script location** - The canonical script is in `scripts/production-cleanup.sh` in the repo

### 7.7 Environment Configuration

Create `/opt/shuttersense/app/.env`:

> **Note:** During development, `.env` is located in `backend/` where Python's `load_dotenv()`
> looks for it. In production, we place it at the application root instead. This works because
> the systemd service (section 10.1) uses `EnvironmentFile=/opt/shuttersense/app/.env` to load
> all variables into the environment before the Python process starts.

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

### 7.8 Generate Security Keys

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

**Important:** Certbot's standalone mode needs to bind to port 80. If another process (typically nginx) is already using this port, you must stop it first:

```bash
# Check if anything is using port 80
sudo lsof -i :80

# If nginx is running, stop it temporarily
sudo systemctl stop nginx
```

Obtain the certificate:

```bash
# Obtain certificate (standalone mode, before nginx is configured)
certbot certonly --standalone -d app.shuttersense.ai \
  --non-interactive \
  --agree-tos \
  --email admin@shuttersense.ai \
  --no-eff-email
```

> **Note:** If you stopped nginx above, it will be started again in section 9. Do not restart it now as it needs the certificate files that were just created.

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

    # HSTS - Enable after HTTPS is confirmed working (see section 9.6)
    # add_header Strict-Transport-Security "max-age=63072000" always;

    # Security headers (applied to dynamic content; static assets override below)
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Logging
    access_log /var/log/nginx/shuttersense_access.log;
    error_log /var/log/nginx/shuttersense_error.log;

    # Request size limit (match FastAPI)
    client_max_body_size 10M;

    # =========================================================================
    # Static Assets with Browser Caching
    # =========================================================================
    # PWA icons, images, fonts, and hashed build assets get long cache times.
    # This reduces repeated requests (especially PWA manifest icon fetches)
    # and improves performance. Vite adds hashes to JS/CSS filenames, so
    # they can be cached indefinitely (immutable).

    # PWA icons and images (30-day cache)
    location /icons/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        expires 30d;
        add_header Cache-Control "public, max-age=2592000, immutable";
        add_header X-Content-Type-Options "nosniff" always;
    }

    # Hashed build assets (JS, CSS, fonts) - 1 year cache
    # Vite includes content hashes in filenames, so these are safe to cache long-term
    location /assets/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        expires 1y;
        add_header Cache-Control "public, max-age=31536000, immutable";
        add_header X-Content-Type-Options "nosniff" always;
    }

    # Service worker - MUST NOT be cached (browsers check for updates on navigation)
    location = /sw.js {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires "0";
        add_header X-Content-Type-Options "nosniff" always;
    }

    # HTML files - short cache to ensure users get updated asset references
    location ~* ^/[^/]*\.html$ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        add_header Cache-Control "no-cache, must-revalidate";
        add_header X-Content-Type-Options "nosniff" always;
    }

    # Other static files at root (favicon, apple-touch-icon, etc.) - 7 day cache
    location ~* ^/[^/]+\.(png|ico|svg|webp|webmanifest)$ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        expires 7d;
        add_header Cache-Control "public, max-age=604800";
        add_header X-Content-Type-Options "nosniff" always;
    }

    # =========================================================================
    # WebSocket Endpoints
    # =========================================================================

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

    # =========================================================================
    # Default Handler (API and SPA)
    # =========================================================================

    # All other requests (API calls, SPA HTML)
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

> **Note:** The static asset caching configuration above significantly reduces repeated requests for PWA icons and build assets. Without these cache headers, browsers may re-request manifest icons on every page load or PWA validation check.

### 9.3 Enable Site

```bash
# Remove default site
rm -f /etc/nginx/sites-enabled/default

# Enable ShutterSense site
ln -s /etc/nginx/sites-available/shuttersense /etc/nginx/sites-enabled/

# Test configuration
nginx -t

# Start nginx (it was stopped in section 8.2 for certbot)
systemctl start nginx
systemctl enable nginx
```

### 9.4 Enable Nginx Fail2ban Jails

Now that nginx is installed and configured, enable the nginx-related fail2ban jails:

```bash
# Enable nginx jails in jail.local
sed -i '/\[nginx-http-auth\]/,/^\[/{s/enabled = false/enabled = true/}' /etc/fail2ban/jail.local
sed -i '/\[nginx-limit-req\]/,/^\[/{s/enabled = false/enabled = true/}' /etc/fail2ban/jail.local
sed -i '/\[nginx-botsearch\]/,/^\[/{s/enabled = false/enabled = true/}' /etc/fail2ban/jail.local

# Reload fail2ban to apply changes
fail2ban-client reload

# Verify nginx jails are now active
fail2ban-client status
fail2ban-client status nginx-http-auth
fail2ban-client status nginx-limit-req
fail2ban-client status nginx-botsearch
```

### 9.5 Checkpoint: Verify HTTPS is Working

At this point, nginx is serving HTTPS with a valid Let's Encrypt certificate. Verify before proceeding:

```bash
# From your local machine or browser
curl -I https://app.shuttersense.ai
```

**Expected result:**
- Browser shows a valid certificate (no security warnings)
- Response is `502 Bad Gateway`

The 502 error is expected because the backend service is not running yet. This confirms:
- ✅ DNS is resolving correctly
- ✅ Nginx is running and listening on port 443
- ✅ SSL certificate is valid and trusted
- ✅ Nginx is attempting to proxy to the backend (which doesn't exist yet)

If you see certificate errors or connection refused, review sections 8 and 9 before continuing.

### 9.6 Enable HSTS (After Production is Stable)

> **Important:** Only enable HSTS after HTTPS has been working reliably for several days. HSTS is "sticky" - once browsers receive it, they will refuse HTTP connections for the duration of `max-age`. If HTTPS breaks, users cannot access the site until they manually clear HSTS from their browser.

**Staged rollout approach:**

1. **Start with a short max-age (5 minutes)** to test:

Edit `/etc/nginx/sites-available/shuttersense` and uncomment the HSTS line, changing the value:

```nginx
add_header Strict-Transport-Security "max-age=300" always;
```

2. **Apply the nginx configuration change:**

```bash
# Test the configuration for syntax errors
nginx -t

# If test passes, reload nginx (graceful - no downtime)
sudo systemctl reload nginx
```

3. **Verify the header is present:**

```bash
curl -I https://app.shuttersense.ai 2>/dev/null | grep -i strict
# Expected: Strict-Transport-Security: max-age=300
```

4. **Gradually increase max-age** after confirming each stage works:

| Stage | max-age | Duration | Wait before next |
|-------|---------|----------|------------------|
| Test | 300 | 5 minutes | 1 hour |
| Day | 86400 | 1 day | 1 day |
| Week | 604800 | 1 week | 1 week |
| Production | 63072000 | 2 years | Final |

5. **Final production configuration:**

```nginx
add_header Strict-Transport-Security "max-age=63072000" always;
```

> **Tip:** After any nginx configuration change, always run `nginx -t` to test before reloading. Use `systemctl reload nginx` (not restart) for zero-downtime configuration updates.

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
WorkingDirectory=/opt/shuttersense/app
# Include system paths for git (needed for version detection)
Environment="PATH=/opt/shuttersense/app/venv/bin:/usr/bin:/bin"
EnvironmentFile=/opt/shuttersense/app/.env
ExecStart=/opt/shuttersense/app/venv/bin/gunicorn backend.src.main:app \
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
# Application logs (where ShutterSense logs go)
tail -f /var/log/shuttersense/error.log    # Application errors and info
tail -f /var/log/shuttersense/access.log   # HTTP request logs (gunicorn)
tail -f /var/log/shuttersense/api.log      # API-specific logs
tail -f /var/log/shuttersense/auth.log     # Authentication events

# Service status logs (systemd lifecycle only - start/stop/restart)
journalctl -u shuttersense -f

# Nginx logs
tail -f /var/log/nginx/shuttersense_error.log
```

> **Note:** Application logs (startup messages, errors, warnings) go to files in `/var/log/shuttersense/`, not to the systemd journal. The `journalctl` command only shows service lifecycle events (started, stopped, restarted).

### 10.4 Checkpoint: Backend is Running

At this point, the backend service is running and serving the application. Verify before proceeding:

```bash
# From your local machine or browser
curl -I https://app.shuttersense.ai
```

**Expected result:**
- The `502 Bad Gateway` error from section 9.5 is now resolved
- Response is `200 OK` or `302 Found` (redirect to login)
- Opening `https://app.shuttersense.ai` in a browser shows the login page
- The login page displays a message indicating no authentication providers are configured

This confirms:
- ✅ Gunicorn is running and serving the FastAPI application
- ✅ Nginx is successfully proxying requests to the backend
- ✅ The application is loading correctly

The "no authentication providers" message is expected because OAuth is configured in section 12.

---

## 11. Database Seeding

Database setup requires a specific order because migration 031 enforces team ownership on all entities, which requires a team to exist first.

### 11.1 Run Initial Migrations (up to 030)

```bash
su - shuttersense
cd /opt/shuttersense/app
source venv/bin/activate

# Set environment
export $(grep -v '^#' .env | xargs)

# Run migrations (must be from backend directory where alembic.ini is located)
cd backend

# Verify alembic.ini exists (if missing, re-clone the repository)
ls -la alembic.ini

# Run migrations up to 030 (before team_id enforcement)
alembic upgrade 030_user_type_api_tokens
```

> **Troubleshooting:** If you see "No 'script_location' key found in configuration", verify:
> 1. You are in the `/opt/shuttersense/app/backend` directory (not the app root)
> 2. The `alembic.ini` file exists in the current directory
> 3. If missing, the file may have been accidentally deleted - re-clone or restore from git

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
  GUID: ten_01hgw2bbg...
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

Team GUID:  ten_01hgw2bbg...
Admin GUID: usr_01hgw2bbg...

Next steps:
  1. Complete remaining migrations (section 11.3)
  2. Configure OAuth providers in .env
  3. Restart the server
  4. Login with admin@yourdomain.com via OAuth
```

### 11.3 Complete Remaining Migrations

Now that a team exists, run the remaining migrations to enforce team ownership:

```bash
# Still as shuttersense user with venv activated
cd /opt/shuttersense/app/backend

# Run remaining migrations
alembic upgrade head
```

### 11.4 Restart Backend Service

After database changes, restart the backend to pick up the new schema:

```bash
# Exit to root user
exit

# Restart the service
sudo systemctl restart shuttersense
sudo systemctl status shuttersense
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
   - Authorized redirect URIs: `https://app.shuttersense.ai/api/auth/callback/google`
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
   - Redirect URI: `https://app.shuttersense.ai/api/auth/callback/microsoft`
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

## 13. Geofencing (Optional)

ShutterSense supports geographic access restrictions using MaxMind's GeoLite2 database. When enabled, only requests from allowed countries can access the application.

### 13.1 When to Use Geofencing

Consider enabling geofencing if:
- Your users are located in specific countries only
- You want to block traffic from high-risk regions
- Compliance requires geographic access controls

**Note:** Geofencing is disabled by default and has zero runtime overhead when not configured.

### 13.2 Obtain MaxMind GeoLite2 Database

The GeoLite2 database is free but requires registration:

1. Create account at [MaxMind GeoLite2](https://www.maxmind.com/en/geolite2/signup)
2. Generate a license key under **Account → Manage License Keys**
3. Note your **Account ID** and **License Key**

### 13.3 Install geoipupdate

```bash
# Add MaxMind PPA
add-apt-repository ppa:maxmind/ppa
apt update

# Install geoipupdate
apt install -y geoipupdate
```

### 13.4 Configure geoipupdate

Create `/etc/GeoIP.conf`:

```bash
cat > /etc/GeoIP.conf << 'EOF'
# MaxMind account credentials
AccountID YOUR_ACCOUNT_ID
LicenseKey YOUR_LICENSE_KEY

# Download GeoLite2-Country only (smallest, sufficient for geofencing)
EditionIDs GeoLite2-Country

# Database directory
DatabaseDirectory /opt/maxmind
EOF
```

Set permissions:

```bash
chmod 600 /etc/GeoIP.conf
mkdir -p /opt/maxmind
chown shuttersense:shuttersense /opt/maxmind
```

### 13.5 Download Initial Database

```bash
# Run geoipupdate manually first time
geoipupdate -v

# Verify database exists
ls -la /opt/maxmind/GeoLite2-Country.mmdb
```

### 13.6 Configure Automatic Updates

MaxMind updates the database weekly. Create a cron job:

```bash
cat > /etc/cron.d/geoipupdate << 'EOF'
# Update GeoLite2 database weekly (Wednesdays at 2:30 AM)
# MaxMind typically releases updates on Tuesdays
# Scheduled before DB backup (3 AM) and auto-update (5 AM)
30 2 * * 3 root /usr/bin/geoipupdate && systemctl restart shuttersense
EOF

chmod 644 /etc/cron.d/geoipupdate
```

### 13.7 Configure Environment Variables

Add to `/opt/shuttersense/app/.env`:

```bash
# =============================================================================
# Geofencing (Optional)
# =============================================================================
# Path to MaxMind GeoLite2-Country database
SHUSAI_GEOIP_DB_PATH=/opt/maxmind/GeoLite2-Country.mmdb

# Allowed countries (ISO 3166-1 alpha-2 codes, comma-separated)
# Common codes: US, CA, GB, DE, FR, AU, NZ, JP, etc.
SHUSAI_GEOIP_ALLOWED_COUNTRIES=US,CA,GB,DE,FR,NL,BE,AU,NZ

# Fail-open mode: allow requests when country cannot be determined
# false (default) = block unknown, true = allow unknown
SHUSAI_GEOIP_FAIL_OPEN=false
```

### 13.8 Restart Application

```bash
systemctl restart shuttersense
```

### 13.9 Verify Geofencing is Active

Check the application logs at startup:

```bash
grep -i geoip /var/log/shuttersense/api.log
```

Expected output (with `SHUSAI_LOG_LEVEL=INFO` or lower):
```
GeoIP geofencing enabled — allowed countries: AU, BE, CA, DE, FR, GB, NL, NZ, US (fail-closed, db: /opt/maxmind/GeoLite2-Country.mmdb)
```

> **Note:** This message is logged at INFO level. If `SHUSAI_LOG_LEVEL=WARNING` (the production default), the message won't appear. You can either:
> - Temporarily set `SHUSAI_LOG_LEVEL=INFO` in `.env`, restart, verify, then revert
> - Use the functional test in section 13.10 to confirm geofencing is working

### 13.10 Test Geofencing

From an allowed country:
```bash
curl -I https://app.shuttersense.ai/health
# Should return: HTTP/2 200
```

Blocked requests receive:
```json
{
  "detail": "Access denied based on geographic restrictions"
}
```

### 13.11 Country Code Reference

Common ISO 3166-1 alpha-2 country codes:

| Region | Countries |
|--------|-----------|
| North America | `US`, `CA`, `MX` |
| Europe | `GB`, `DE`, `FR`, `NL`, `BE`, `IT`, `ES`, `PT`, `IE`, `CH`, `AT`, `SE`, `NO`, `DK`, `FI`, `PL` |
| Asia Pacific | `AU`, `NZ`, `JP`, `SG`, `HK`, `KR` |

Full list: [ISO 3166-1 alpha-2 codes](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2)

### 13.12 Important Notes

1. **Private IPs always pass** - Localhost and private network IPs (10.x, 172.16-31.x, 192.168.x) bypass geofencing
2. **Health endpoint exempt** - `/health` is never blocked (for load balancer probes)
3. **WebSockets exempt** - WebSocket connections skip geofencing checks
4. **Restart required** - Database updates require application restart to take effect
5. **Fail-closed default** - Unknown countries are blocked unless `SHUSAI_GEOIP_FAIL_OPEN=true`

---

## 14. Final Verification

### 14.1 Service Health Checks

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

### 14.2 External Access Tests

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

### 14.3 SSL Certificate Verification

```bash
# Check certificate
openssl s_client -connect app.shuttersense.ai:443 -servername app.shuttersense.ai < /dev/null 2>/dev/null | openssl x509 -noout -dates

# Or use SSL Labs (comprehensive test)
# https://www.ssllabs.com/ssltest/analyze.html?d=app.shuttersense.ai
```

### 14.4 Login Test

1. Open `https://app.shuttersense.ai` in browser
2. Click "Sign in with Google" (or Microsoft)
3. Authenticate with the admin email used in seeding
4. Verify dashboard loads successfully

---

## 15. Maintenance & Backups

### 15.1 Database Backup Script

The backup script is maintained in the repository at `scripts/backup-db.sh`. Copy it to the server scripts directory:

```bash
# Copy backup script to server scripts directory
cp /opt/shuttersense/app/scripts/backup-db.sh /opt/shuttersense/scripts/
chmod +x /opt/shuttersense/scripts/backup-db.sh
```

#### Tiered Retention Policy

The script implements a tiered retention policy to balance storage usage with recovery options:

| Tier | Backups Kept | Retention Period |
|------|--------------|------------------|
| Daily | All backups | 7 days |
| Weekly | Saturday backups | ~30 days |
| Monthly | First Saturday of each month | 1 year |

This means you can restore to:
- Any point in the last week (daily granularity)
- Any Saturday in the last month (weekly granularity)
- The first week of any month in the last year (monthly granularity)

> **Note:** The script uses `BACKUP_DIR` environment variable to customize the backup location (default: `/opt/shuttersense/backups`).

### 15.2 Scheduled Tasks (Cron)

Configure scheduled tasks for backups and automatic updates.

**Backups (as shuttersense user):**

```bash
crontab -e
```

Add:
```
# Daily database backup at 3 AM UTC
0 3 * * * /opt/shuttersense/scripts/backup-db.sh >> /var/log/shuttersense/backup.log 2>&1
```

**Auto-updates (as root):**

The auto-update requires root privileges to restart the service. Configure in root's crontab:

```bash
sudo crontab -e
```

Add:
```
# Daily auto-update check at 5 AM UTC (optional but recommended)
0 5 * * * /opt/shuttersense/scripts/auto-update-cron.sh
```

> **Note:** The auto-update scripts manage their own logging to `/var/log/shuttersense/auto-update.log`.

### 15.3 Application Updates

There are three update strategies:
- **Automatic updates**: Daily check for new version tags (recommended for most deployments)
- **Manual tag deployment**: Deploy a specific version tag
- **Latest main branch**: Deploy the most recent code from main (development only)

#### Automatic Updates (Recommended)

The auto-update system consists of two scripts that work together:

1. **`auto-update-cron.sh`** - Root wrapper that orchestrates the update process
2. **`auto-update.sh`** - Performs the actual update (runs as shuttersense user)

This separation is necessary because:
- The update process (git, npm, pip) should run as the application user for proper file ownership
- The service restart requires root privileges

**Setup:**

```bash
# Add to root's crontab (runs daily at 5 AM UTC)
sudo crontab -e
```

Add:
```
# Daily auto-update check at 5 AM UTC
0 5 * * * /opt/shuttersense/scripts/auto-update-cron.sh
```

**What automatic updates handle:**
- Fetching new version tags from the repository
- Comparing versions and updating only when a newer tag exists
- Backend dependency updates (`pip install`)
- Frontend rebuilds (`npm ci && npm run build`)
- Database migrations (`alembic upgrade head`)
- Maintenance script updates
- Production cleanup
- Service restart

**What automatic updates do NOT handle:**
- **Major version updates** (e.g., v1.x → v2.x) - skipped by default, see below
- Nginx configuration changes (check release notes)
- Breaking changes that require manual migration steps
- Rollbacks (must be done manually)

**Major Version Updates:**

By default, major version updates are skipped because they may contain breaking changes. When a major update is available, the script logs:

```
SKIPPED: Major version update detected (v1.19.0 → v2.0.0)
Major updates may contain breaking changes and require manual intervention.
```

To enable automatic major updates, set the environment variable in root's crontab:

```
0 5 * * * AUTO_UPDATE_MAJOR=true /opt/shuttersense/scripts/auto-update-cron.sh
```

Or update manually when ready:

```bash
cd /opt/shuttersense/app
git fetch --tags
git reset --hard v2.0.0
# Then follow the manual update steps below
```

**Monitoring:**

All auto-update activity is logged to `/var/log/shuttersense/auto-update.log`:

```bash
# View recent update activity
tail -100 /var/log/shuttersense/auto-update.log

# Watch updates in real-time
tail -f /var/log/shuttersense/auto-update.log
```

#### Manual Updates

For manual control or to deploy a specific version:

```bash
# SSH as shuttersense user (root login is disabled)
cd /opt/shuttersense/app

# Fetch latest changes and tags
git fetch origin --tags

# Option A: Deploy a specific release tag (recommended)
# Use git reset --hard to restore all files removed by production-cleanup.sh
git reset --hard v1.2.3

# Option B: Update to latest main branch (development only)
git pull origin main

# Update backend dependencies
source venv/bin/activate
pip install -r backend/requirements.txt

# Set environment
export $(grep -v '^#' .env | xargs)

# Rebuild frontend
cd frontend
npm ci
npm run build
cd ..

# Run migrations
cd backend
alembic upgrade head
cd ..

# Update maintenance scripts (may have changed between releases)
cp scripts/*.sh /opt/shuttersense/scripts/
chmod +x /opt/shuttersense/scripts/*.sh

# Run production cleanup (remove dev artifacts)
/opt/shuttersense/scripts/production-cleanup.sh

# Restart service
sudo systemctl restart shuttersense
```

#### Nginx Configuration Changes

Nginx configuration changes are NOT handled automatically. When release notes indicate nginx changes:

```bash
# Compare and update nginx config
sudo cp /etc/nginx/sites-available/shuttersense /etc/nginx/sites-available/shuttersense.backup
sudo nano /etc/nginx/sites-available/shuttersense  # Apply changes from docs

# Test and reload
sudo nginx -t && sudo systemctl reload nginx
```

#### Service Worker Note

Even after deployment, users may continue seeing cached content until their browser's service worker updates. The service worker checks for updates on navigation, but the new version won't activate until all tabs are closed. Users experiencing stale content should:
1. Close all tabs for the application
2. Reopen the application
3. If issues persist, clear site data in browser settings

### 15.4 Log Rotation

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

### 15.5 Critical Keys Backup

**IMPORTANT:** Store these keys securely (password manager, encrypted vault):

1. `SHUSAI_MASTER_KEY` - Losing this means encrypted credentials are unrecoverable
2. `SESSION_SECRET_KEY` - Changing invalidates all sessions
3. `JWT_SECRET_KEY` - Changing invalidates all API tokens
4. Database password

---

## 16. Troubleshooting

### 16.1 Service Won't Start

```bash
# Check service status and recent lifecycle events
systemctl status shuttersense
journalctl -u shuttersense -n 50 --no-pager

# Check application error logs (startup errors, exceptions)
tail -100 /var/log/shuttersense/error.log

# Common issues:
# - Missing .env file or permissions
# - Database connection failed
# - Port already in use
# - Python import errors (check error.log)
```

### 16.2 502 Bad Gateway

```bash
# Check if backend is running
systemctl status shuttersense
curl http://127.0.0.1:8000/health

# Check nginx error log
tail -f /var/log/nginx/shuttersense_error.log
```

### 16.3 Database Connection Issues

```bash
# Test PostgreSQL is running
systemctl status postgresql

# Test connection manually
psql -h localhost -U shuttersense_app -d shuttersense -c "SELECT 1;"

# Check pg_hba.conf if authentication fails
cat /etc/postgresql/16/main/pg_hba.conf
```

### 16.4 SSL Certificate Issues

```bash
# Check certificate status
certbot certificates

# Force renewal
certbot renew --force-renewal

# Check nginx config
nginx -t
```

### 16.5 OAuth Redirect Issues

- Verify `OAUTH_REDIRECT_BASE_URL` matches exactly: `https://app.shuttersense.ai`
- Check Google/Microsoft console has correct redirect URI
- Ensure no trailing slashes in URLs

### 16.6 Performance Issues

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
journalctl -u shuttersense -f              # Service lifecycle only (start/stop)

# Database
sudo -u postgres psql -d shuttersense
/opt/shuttersense/scripts/backup-db.sh

# SSL
certbot certificates
certbot renew --dry-run

# Firewall
ufw status verbose

# Fail2ban
fail2ban-client status                          # List all jails
fail2ban-client status sshd                     # Check SSH jail
fail2ban-client status nginx-limit-req          # Check rate limit jail
fail2ban-client set sshd unbanip <IP>           # Unban IP
tail -f /var/log/fail2ban.log                   # Watch bans

# Application logs (where ShutterSense logs go)
tail -f /var/log/shuttersense/error.log         # Gunicorn errors, startup issues
tail -f /var/log/shuttersense/api.log           # API logs (GeoIP, requests, etc.)
tail -f /var/log/shuttersense/auth.log          # Authentication events
tail -f /var/log/shuttersense/auto-update.log   # Auto-update activity
tail -f /var/log/nginx/shuttersense_error.log   # Nginx proxy errors

# Manual update trigger (run as root)
sudo /opt/shuttersense/scripts/auto-update-cron.sh
```

---

## Security Checklist

- [ ] Hostinger managed firewall configured (hPanel)
- [ ] SSH restricted to known IPs in Hostinger firewall (recommended)
- [ ] SSH key-only authentication enabled
- [ ] Root login disabled
- [ ] UFW firewall active (only 22, 80, 443 open)
- [ ] Fail2ban protecting SSH (sshd jail)
- [ ] Fail2ban protecting nginx (nginx-limit-req, nginx-botsearch jails)
- [ ] Recidive jail enabled for repeat offenders
- [ ] PostgreSQL listening only on localhost
- [ ] Gunicorn listening only on localhost
- [ ] HTTPS-only access enforced
- [ ] Let's Encrypt auto-renewal configured
- [ ] Strong passwords/keys generated
- [ ] Automatic security updates enabled
- [ ] Log rotation configured
- [ ] Database backups scheduled
- [ ] Auto-updates scheduled (optional)
- [ ] Critical keys backed up securely
