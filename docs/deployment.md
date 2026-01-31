# Deployment Guide

This guide covers deploying ShutterSense in a production environment.

## Prerequisites

- **Python 3.10+** - Backend and agent runtime
- **Node.js 18+** - Frontend build tooling
- **PostgreSQL 12+** - Primary database
- **Git** - Source code access

## Production Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `SHUSAI_MASTER_KEY` | Fernet encryption key for credential storage |
| `SHUSAI_DB_URL` | PostgreSQL connection URL |
| `SESSION_SECRET_KEY` | Session cookie signing key (min 32 chars) |
| `JWT_SECRET_KEY` | JWT token signing key (min 32 chars) |

### Recommended

| Variable | Description | Production Value |
|----------|-------------|-----------------|
| `SHUSAI_ENV` | Environment name | `production` |
| `SESSION_HTTPS_ONLY` | Require HTTPS for cookies | `true` |
| `SESSION_SAME_SITE` | Cookie SameSite attribute | `lax` |
| `CORS_ORIGINS` | Allowed origins | Your domain only |
| `SHUSAI_LOG_LEVEL` | Logging level | `WARNING` |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `SHUSAI_SPA_DIST_PATH` | Path to frontend build | `frontend/dist` |
| `SHUSAI_AUTHORIZED_LOCAL_ROOTS` | Authorized local paths for agents | - |
| `SHUSAI_LOG_DIR` | Log file directory | `logs` |
| `VAPID_PUBLIC_KEY` | Web Push public key | - |
| `VAPID_PRIVATE_KEY` | Web Push private key | - |
| `VAPID_SUBJECT` | Web Push contact URI | - |

### Generate Secrets

```bash
# Master encryption key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Session secret
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# JWT secret
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Database Setup

### Create Database

```bash
createdb shuttersense
```

### Run Migrations

```bash
cd backend
alembic upgrade head
```

### Connection URL Format

```
postgresql://user:password@host:5432/shuttersense
```

For connection pooling, configure SQLAlchemy pool settings in the application.

## Building the Frontend

```bash
cd frontend
npm ci                    # Install exact dependency versions
npm run build            # Build production bundle to dist/
```

The build output in `dist/` contains the SPA that FastAPI will serve.

## Single-Server Deployment

ShutterSense is designed for single-server deployment where FastAPI serves both the API and the SPA:

```bash
# Set the path to the built frontend
export SHUSAI_SPA_DIST_PATH="/path/to/shuttersense/frontend/dist"

# Start with multiple workers
cd backend
gunicorn src.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

This serves:
- `/api/*` - REST API endpoints
- `/assets/*` - Static frontend assets
- `/*` - SPA `index.html` (client-side routing)

## Reverse Proxy Configuration

### nginx Example

```nginx
server {
    listen 443 ssl http2;
    server_name shuttersense.example.com;

    ssl_certificate /etc/ssl/certs/shuttersense.crt;
    ssl_certificate_key /etc/ssl/private/shuttersense.key;

    # WebSocket support
    location /api/tools/ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # All other requests
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### HTTPS/TLS Notes

- Required for production OAuth redirects
- Required when `SESSION_HTTPS_ONLY=true`
- Required for Web Push notifications (VAPID)
- Use Let's Encrypt for free certificates

## Agent Deployment

Agents run alongside the server (or on remote machines) to execute analysis jobs.

### Install Agent

```bash
# Option A: From source
cd agent
pip install -e .

# Option B: Pre-built binary
# Download from releases page
```

### Register Agent

```bash
# 1. Generate a registration token in web UI (Settings > Agents)
# 2. Register
shuttersense-agent register \
  --server https://shuttersense.example.com \
  --token art_xxxxx... \
  --name "Production Agent"

# 3. Start
shuttersense-agent start
```

### Agent as a Service (systemd)

```ini
[Unit]
Description=ShutterSense Agent
After=network.target

[Service]
Type=simple
User=shuttersense
ExecStart=/usr/local/bin/shuttersense-agent start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Monitoring

### Health Check

```bash
curl https://shuttersense.example.com/health
```

Returns:
```json
{
  "status": "healthy",
  "version": "v1.2.3",
  "database": "connected"
}
```

### Agent Heartbeat

Agents send heartbeats every 30 seconds. The server marks agents as offline after missing heartbeats. Monitor via:

- Web UI: Agent pool status badge in header
- API: `GET /api/agent/v1/pool-status`

### Key Metrics to Monitor

- Database connection pool utilization
- Agent heartbeat frequency
- Job queue depth
- Failed job count
- WebSocket connection count

## Backup Considerations

### Database

- Regular PostgreSQL backups (pg_dump)
- Include all tables (entity data, configuration, analysis results)

### Encryption Keys

- `SHUSAI_MASTER_KEY` - **Critical**: losing this key means losing access to encrypted connector credentials
- `SESSION_SECRET_KEY` - Changing invalidates all active sessions
- `JWT_SECRET_KEY` - Changing invalidates all API tokens
- `VAPID_PRIVATE_KEY` - Changing invalidates all push subscriptions

Store these keys securely (e.g., secrets manager, encrypted vault).

### Agent Configuration

Agent configuration is stored locally on each agent machine:
- macOS: `~/Library/Application Support/shuttersense-agent/`
- Linux: `~/.config/shuttersense-agent/`

## Notes

- **No Docker yet** - There is no Dockerfile in the repository. Deployment is done directly on the host.
- **No clustering** - The application is designed for single-server deployment. Multiple backend instances require shared session storage (not yet implemented).
- **Database migrations** - Always run `alembic upgrade head` after updating the application code.
