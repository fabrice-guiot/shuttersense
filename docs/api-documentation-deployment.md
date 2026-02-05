# ShutterSense API & Documentation Deployment

This guide covers the deployment of separate hostnames for API access and documentation, providing a clean separation for API consumers using API tokens.

## Overview

### Hostname Architecture

| Hostname | Purpose | Content |
|----------|---------|---------|
| `app.shuttersense.ai` | Web Application | SPA (React), session-based auth |
| `api.shuttersense.ai` | Public API | REST API for token-based access, no `/api/` prefix |
| `docs.shuttersense.ai` | Documentation | API docs (Swagger/ReDoc), future user guides |

### Route Structure

**api.shuttersense.ai** (no `/api/` prefix):
```
GET  /collections
POST /collections
GET  /collections/{guid}
GET  /events
...
```

**docs.shuttersense.ai**:
```
/api/docs      - Swagger UI (interactive API documentation)
/api/redoc     - ReDoc (alternative API documentation)
/api/openapi.json - OpenAPI 3.0 schema
/              - Future: User documentation website
```

### What's Excluded from Public API Docs

The public API documentation excludes routes that cannot be used with API tokens:

- `/api/agent/v1/*` - Agent-only endpoints (require agent authentication)
- `/api/admin/*` - Super admin endpoints (require session + super admin)
- `/api/auth/*` - OAuth endpoints (session-based only)
- `/api/tokens/*` - Token management (session-based only)

---

## Prerequisites

Before starting, ensure:
1. DNS records for all hostnames point to the server IP
2. The main deployment ([deployment-hostinger-kvm2.md](deployment-hostinger-kvm2.md)) is complete
3. SSL certificate covers all hostnames (see Section 1)

---

## 1. DNS Configuration (GoDaddy)

Add these DNS records:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| **A** | `api` | `<KVM2_IP_ADDRESS>` | 600 |
| **A** | `docs` | `<KVM2_IP_ADDRESS>` | 600 |

Verify propagation:
```bash
dig api.shuttersense.ai +short
dig docs.shuttersense.ai +short
```

---

## 2. SSL Certificate Update

### Option A: Multi-Domain Certificate (Recommended)

This is the simplest approach for a small number of hostnames. Uses HTTP-01 challenge which auto-renews without manual intervention.

```bash
# Stop nginx temporarily (certbot needs port 80)
sudo systemctl stop nginx

# Expand certificate to include new hostnames
sudo certbot certonly --standalone \
  -d app.shuttersense.ai \
  -d api.shuttersense.ai \
  -d docs.shuttersense.ai \
  --non-interactive \
  --agree-tos \
  --email admin@shuttersense.ai \
  --no-eff-email \
  --expand

# Verify certificate includes all domains
sudo certbot certificates

# Start nginx
sudo systemctl start nginx
```

**Why this is recommended:**
- Simple one-time setup
- Auto-renews every 90 days without intervention
- No DNS provider API integration needed
- Sufficient for most deployments (up to 100 hostnames per certificate)

### Option B: Wildcard Certificate (Advanced)

Covers all subdomains (`*.shuttersense.ai`) but requires DNS-01 challenge, which means proving domain ownership by creating DNS TXT records.

**How DNS-01 challenge works:**

1. Run certbot with `--manual` flag
2. Certbot displays a TXT record to add:
   ```
   Please deploy a DNS TXT record under the name:
   _acme-challenge.shuttersense.ai
   with the following value:
   abc123xyz789...
   ```
3. You manually add this TXT record in GoDaddy DNS management
4. Wait for DNS propagation (1-5 minutes)
5. Press Enter in certbot to continue verification
6. Certificate is issued
7. You can delete the TXT record

```bash
sudo certbot certonly --manual \
  -d "*.shuttersense.ai" \
  -d shuttersense.ai \
  --preferred-challenges dns-01 \
  --agree-tos \
  --email admin@shuttersense.ai
```

**Important limitations:**
- **Manual renewal required** - You must repeat the DNS TXT record process every 90 days
- **No auto-renewal** - Unless you set up DNS provider API integration (complex)
- **Only consider if** you expect many more subdomains in the future

**For automated wildcard renewal**, you would need to:
1. Use a DNS provider with API support (GoDaddy has limited API)
2. Install a certbot DNS plugin (e.g., `certbot-dns-cloudflare`)
3. Configure API credentials

This is significantly more complex than Option A and not recommended unless you have a specific need for wildcards.

---

## 3. Nginx Configuration

### 3.1 Create API Hostname Configuration

Create `/etc/nginx/sites-available/shuttersense-api`:

```nginx
# =============================================================================
# api.shuttersense.ai - Public API Access
# =============================================================================
# Serves the REST API without /api/ prefix for cleaner URLs.
# Designed for API token authentication (no session/cookie support needed).

server {
    listen 80;
    listen [::]:80;
    server_name api.shuttersense.ai;

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name api.shuttersense.ai;

    # SSL Configuration (same cert as app.shuttersense.ai)
    ssl_certificate /etc/letsencrypt/live/app.shuttersense.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.shuttersense.ai/privkey.pem;

    # SSL Security Settings
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # CORS for API access from docs.shuttersense.ai
    # Note: Actual CORS handling is done by FastAPI, but we ensure
    # preflight requests are proxied correctly

    # Logging
    access_log /var/log/nginx/api_access.log;
    error_log /var/log/nginx/api_error.log;

    # Request size limit
    client_max_body_size 10M;

    # Health check (no rewrite needed)
    location = /health {
        proxy_pass http://127.0.0.1:8000/health;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Rewrite all requests to add /api/ prefix
    # Example: /collections -> /api/collections
    location / {
        rewrite ^/(?!api/)(.*)$ /api/$1 break;
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

### 3.2 Create Documentation Hostname Configuration

Create `/etc/nginx/sites-available/shuttersense-docs`:

```nginx
# =============================================================================
# docs.shuttersense.ai - API Documentation
# =============================================================================
# Serves API documentation (Swagger UI, ReDoc) and future user guides.

server {
    listen 80;
    listen [::]:80;
    server_name docs.shuttersense.ai;

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name docs.shuttersense.ai;

    # SSL Configuration (same cert as app.shuttersense.ai)
    ssl_certificate /etc/letsencrypt/live/app.shuttersense.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.shuttersense.ai/privkey.pem;

    # SSL Security Settings
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # Security headers (relaxed for docs - Swagger UI needs external resources)
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Logging
    access_log /var/log/nginx/docs_access.log;
    error_log /var/log/nginx/docs_error.log;

    # API Documentation routes
    # These proxy to the backend's public API documentation endpoints

    location = /api/docs {
        proxy_pass http://127.0.0.1:8000/public/api/docs;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location = /api/redoc {
        proxy_pass http://127.0.0.1:8000/public/api/redoc;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location = /api/openapi.json {
        proxy_pass http://127.0.0.1:8000/public/api/openapi.json;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Cache the OpenAPI spec for 1 hour
        expires 1h;
        add_header Cache-Control "public, max-age=3600";
    }

    # Root - placeholder for future user documentation
    location = / {
        default_type text/html;
        return 200 '<!DOCTYPE html>
<html>
<head>
    <title>ShutterSense Documentation</title>
    <style>
        body { font-family: system-ui, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        h1 { color: #333; }
        a { color: #0066cc; }
        .links { margin-top: 30px; }
        .links a { display: block; margin: 10px 0; font-size: 18px; }
    </style>
</head>
<body>
    <h1>ShutterSense Documentation</h1>
    <p>Welcome to the ShutterSense documentation portal.</p>
    <div class="links">
        <a href="/api/docs">API Documentation (Swagger UI)</a>
        <a href="/api/redoc">API Documentation (ReDoc)</a>
    </div>
</body>
</html>';
    }

    # Catch-all for undefined routes
    location / {
        return 404;
    }
}
```

### 3.3 Enable Sites

```bash
# Enable new sites
sudo ln -s /etc/nginx/sites-available/shuttersense-api /etc/nginx/sites-enabled/
sudo ln -s /etc/nginx/sites-available/shuttersense-docs /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

---

## 4. Backend Configuration

The backend needs new endpoints to serve the filtered public API documentation.

### 4.1 Environment Variables

Add to `/opt/shuttersense/app/.env`:

```bash
# =============================================================================
# Public API Configuration
# =============================================================================
# Base URL for the public API (used in OpenAPI spec "servers" field)
PUBLIC_API_BASE_URL=https://api.shuttersense.ai

# Documentation site URL (for CORS)
DOCS_SITE_URL=https://docs.shuttersense.ai
```

### 4.2 CORS Configuration Update

Update CORS settings to allow docs.shuttersense.ai to make API calls:

```bash
# Update CORS_ORIGINS in .env to include the docs site
CORS_ORIGINS=https://app.shuttersense.ai,https://docs.shuttersense.ai
```

### 4.3 Restart Backend

```bash
sudo systemctl restart shuttersense
```

---

## 5. Backend Code Changes Required

The following backend changes are needed to support the public API documentation:

### 5.1 New Endpoints Needed

Create new endpoints in the backend that serve filtered documentation:

| Endpoint | Purpose |
|----------|---------|
| `GET /public/api/docs` | Swagger UI for public API |
| `GET /public/api/redoc` | ReDoc for public API |
| `GET /public/api/openapi.json` | Filtered OpenAPI schema |

### 5.2 OpenAPI Schema Filtering

The filtered schema should:

1. **Exclude internal routes:**
   - `/api/agent/v1/*` - Agent authentication required
   - `/api/admin/*` - Super admin required
   - `/api/auth/*` - Session-based OAuth only
   - `/api/tokens/*` - Token management (session only)

2. **Modify servers field:**
   ```json
   {
     "servers": [
       {
         "url": "https://api.shuttersense.ai",
         "description": "Production API"
       }
     ]
   }
   ```

3. **Remove /api/ prefix from paths:**
   - `/api/collections` → `/collections`
   - `/api/events` → `/events`

4. **Update security schemes:**
   - Only show Bearer token authentication
   - Remove session/cookie authentication references

### 5.3 Implementation Reference

See the backend implementation PR for the complete code changes:
- New file: `backend/src/api/public_docs.py`
- Updated: `backend/src/main.py` (router registration)

---

## 6. Verification

### 6.1 DNS Verification

```bash
dig api.shuttersense.ai +short
dig docs.shuttersense.ai +short
```

### 6.2 SSL Verification

```bash
# Check certificate covers all domains
openssl s_client -connect api.shuttersense.ai:443 -servername api.shuttersense.ai < /dev/null 2>/dev/null | openssl x509 -noout -text | grep -A1 "Subject Alternative Name"
```

### 6.3 API Endpoint Test

```bash
# Test API without /api/ prefix
curl -I https://api.shuttersense.ai/health
# Should return 200 OK

# Test with API token
curl -H "Authorization: Bearer <your-token>" https://api.shuttersense.ai/collections
```

### 6.4 Documentation Test

```bash
# Test documentation endpoints
curl -I https://docs.shuttersense.ai/api/docs
curl -I https://docs.shuttersense.ai/api/redoc
curl -I https://docs.shuttersense.ai/api/openapi.json

# Verify OpenAPI schema is filtered
curl https://docs.shuttersense.ai/api/openapi.json | jq '.paths | keys' | grep -v agent
```

### 6.5 CORS Test

Open browser developer tools on `https://docs.shuttersense.ai/api/docs` and try the "Try it out" feature. Verify:
- API calls go to `https://api.shuttersense.ai`
- No CORS errors in console

---

## 7. Security Considerations

### 7.1 Rate Limiting

The API hostname should have appropriate rate limiting. This is handled by the existing slowapi middleware in the backend.

### 7.2 Authentication

- `api.shuttersense.ai` only accepts Bearer token authentication
- Session cookies are not sent cross-origin, so session auth won't work (by design)

### 7.3 CORS Policy

CORS is configured to only allow:
- `https://docs.shuttersense.ai` (for Swagger UI "Try it out")
- `https://app.shuttersense.ai` (for the main application)

### 7.4 No SPA on API Hostname

The API hostname does not serve the SPA. Unknown routes return 404, not the SPA's index.html.

---

## 8. Maintenance

### 8.1 Certificate Renewal

Certbot auto-renewal handles all hostnames if configured correctly. Verify:

```bash
sudo certbot renew --dry-run
```

### 8.2 Log Rotation

Add log rotation for new log files. Update `/etc/logrotate.d/shuttersense`:

```
/var/log/nginx/api_access.log
/var/log/nginx/api_error.log
/var/log/nginx/docs_access.log
/var/log/nginx/docs_error.log
{
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    sharedscripts
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 `cat /var/run/nginx.pid`
    endscript
}
```

---

## Appendix: Quick Reference

### Hostnames

| Hostname | Purpose | Auth Method |
|----------|---------|-------------|
| app.shuttersense.ai | Web Application | Session (OAuth) |
| api.shuttersense.ai | Public API | Bearer Token |
| docs.shuttersense.ai | Documentation | None (public) |

### Key Files

| File | Purpose |
|------|---------|
| `/etc/nginx/sites-available/shuttersense` | Main app nginx config |
| `/etc/nginx/sites-available/shuttersense-api` | API nginx config |
| `/etc/nginx/sites-available/shuttersense-docs` | Docs nginx config |
| `/opt/shuttersense/app/.env` | Backend configuration |

### Useful Commands

```bash
# Test all nginx configs
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx

# Check certificate domains
sudo certbot certificates

# View API logs
tail -f /var/log/nginx/api_access.log

# View docs logs
tail -f /var/log/nginx/docs_access.log
```
