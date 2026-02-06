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
1. DNS records for all hostnames point to the server IP (Section 1)
2. The main deployment ([deployment-hostinger-kvm2.md](deployment-hostinger-kvm2.md)) is complete
3. `python3-certbot-nginx` is installed (included in main deployment)

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

## 2. Nginx Configuration

### 2.1 Create API Hostname Configuration

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

### 2.2 Create Documentation Hostname Configuration

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

    # Swagger UI fetches the spec from this path (internal redirect from /api/docs)
    location = /public/api/openapi.json {
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
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ShutterSense Documentation</title>
    <meta name="description" content="ShutterSense.ai API and user documentation portal">
    <link rel="icon" type="image/svg+xml" href="https://app.shuttersense.ai/favicon.svg">
    <link rel="icon" type="image/x-icon" href="https://app.shuttersense.ai/favicon.ico">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #09090b;
            color: #fafafa;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 2rem;
        }
        .container { max-width: 600px; text-align: center; }
        .logo { width: 80px; height: 80px; margin-bottom: 1.5rem; }
        h1 { font-size: 2rem; font-weight: 600; margin-bottom: 0.5rem; }
        .tagline { color: #a1a1aa; margin-bottom: 2rem; }
        .links { display: flex; flex-direction: column; gap: 1rem; }
        .link {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 1rem 1.5rem;
            background: #18181b;
            border: 1px solid #27272a;
            border-radius: 0.5rem;
            color: #fafafa;
            text-decoration: none;
            transition: border-color 0.2s, background 0.2s;
        }
        .link:hover { background: #27272a; border-color: #3f3f46; }
        .link-icon { width: 24px; height: 24px; flex-shrink: 0; }
        .link-text { text-align: left; }
        .link-title { font-weight: 500; }
        .link-desc { font-size: 0.875rem; color: #a1a1aa; }
        footer { margin-top: 3rem; color: #52525b; font-size: 0.875rem; }
        footer a { color: #74c6ef; text-decoration: none; }
        footer a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <img src="https://app.shuttersense.ai/logo.svg" alt="ShutterSense" class="logo">
        <h1>ShutterSense Documentation</h1>
        <p class="tagline">Capture. Process. Analyze.</p>
        <div class="links">
            <a href="/api/docs" class="link">
                <svg class="link-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                    <line x1="16" y1="13" x2="8" y2="13"/>
                    <line x1="16" y1="17" x2="8" y2="17"/>
                    <polyline points="10 9 9 9 8 9"/>
                </svg>
                <div class="link-text">
                    <div class="link-title">Swagger UI</div>
                    <div class="link-desc">Interactive API documentation with try-it-out</div>
                </div>
            </a>
            <a href="/api/redoc" class="link">
                <svg class="link-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
                    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
                </svg>
                <div class="link-text">
                    <div class="link-title">ReDoc</div>
                    <div class="link-desc">Clean three-panel API reference</div>
                </div>
            </a>
        </div>
        <footer>
            <a href="https://app.shuttersense.ai">Back to ShutterSense.ai</a>
        </footer>
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

### 2.3 Enable Sites

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

## 3. SSL Certificate Update

The SSL certificate must be updated **after** the nginx sites are enabled (Section 2.3) because certbot's nginx plugin needs to find the server blocks for the new hostnames.

### 3.1 Expand Certificate with Nginx Plugin

Use the nginx plugin to expand the certificate. This works with nginx running and ensures auto-renewal works correctly.

```bash
# Expand certificate to include new hostnames (nginx must be running)
sudo certbot --nginx \
  -d app.shuttersense.ai \
  -d api.shuttersense.ai \
  -d docs.shuttersense.ai \
  --force-renewal

# Verify certificate includes all domains
sudo certbot certificates
```

**Why `--force-renewal`:** When expanding an existing certificate, certbot may not update the renewal configuration to use the nginx authenticator. The `--force-renewal` flag ensures the renewal config is regenerated with `authenticator = nginx`.

### 3.2 Verify Auto-Renewal

Confirm that the renewal configuration uses the nginx authenticator:

```bash
# Check authenticator in renewal config
cat /etc/letsencrypt/renewal/app.shuttersense.ai.conf | grep authenticator
# Should show: authenticator = nginx

# Test renewal (should succeed with nginx running)
sudo certbot renew --dry-run
```

### 3.3 Alternative: Wildcard Certificate (Advanced)

If you need a wildcard certificate (`*.shuttersense.ai`), you must use DNS-01 challenge:

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
- **No auto-renewal** - Unless you set up DNS provider API integration
- **Only consider if** you expect many more subdomains in the future

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
SHUSAI_PUBLIC_API_BASE_URL=https://api.shuttersense.ai

# Documentation site URL (for CORS)
SHUSAI_DOCS_SITE_URL=https://docs.shuttersense.ai
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
