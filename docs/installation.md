# Installation

This guide covers installing the ShutterSense web application and agent for local development.

> **Important:** The backend and agent have separate dependencies and MUST use separate virtual environments. Installing agent dependencies into the backend venv (or vice versa) will cause issues — the agent is distributed as a standalone binary and must only depend on its own declared packages.

## Requirements

### Web Application
- Python 3.12 or higher (backend)
- Node.js 18+ and npm (frontend)
- PostgreSQL 12+ (database)
- Git (for cloning the repository)

### Agent
- Pre-built binary for your platform (macOS, Linux, Windows) — no Python required
- Or: Python 3.12+ for building from source or development

## Web Application Setup

### 1. Clone the Repository

```bash
git clone https://github.com/fabrice-guiot/shuttersense.git
cd shuttersense
```

### 2. Backend Setup

```bash
# Create backend virtual environment (at repo root)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install backend dependencies
pip install -r backend/requirements.txt

# Set required environment variables
export SHUSAI_MASTER_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
export SHUSAI_DB_URL="postgresql://user:password@localhost:5432/shuttersense"

# Create database and run migrations
createdb shuttersense  # Or use your PostgreSQL admin tool
cd backend && alembic upgrade head && cd ..

# Start the backend server
python3 web_server.py --reload
```

> **Note:** Always activate the backend virtual environment (`source venv/bin/activate`)
> before running `web_server.py`. The script must use the Python interpreter
> that has the backend dependencies installed.

The API will be available at:
- API: http://localhost:8000/api
- OpenAPI docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### 3. Frontend Setup

In a new terminal:

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at http://localhost:3000

## Agent Setup

The agent executes photo analysis jobs on your machine. Without an agent, jobs cannot be processed.

### Option A: Pre-built Binary (Recommended)

Download the latest agent binary for your platform from the releases page, then proceed to [Register the Agent](#register-the-agent). No Python installation required.

### Option B: Run from Source (Development)

> **Important:** Do NOT install the agent into the backend's `venv/`. The agent has its own `pyproject.toml` and must use a separate virtual environment.

```bash
cd agent

# Create a dedicated agent virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install agent and dev dependencies
pip install -e ".[dev]"
```

The agent CLI is now available as `shuttersense-agent` while the agent venv is activated.

### Option C: Build a Binary from Source

See the [Agent Build Guide](agent-build.md) for instructions on creating standalone binaries with PyInstaller.

### Register the Agent

```bash
# 1. Get a registration token from the web UI
# Navigate to Settings > Agents > Generate Token

# 2. Register the agent
shuttersense-agent register \
  --server http://localhost:8000 \
  --token art_xxxxx... \
  --name "My Agent"

# 3. Verify registration
shuttersense-agent self-test
```

### Start the Agent

```bash
# Start the agent (polls server for jobs)
shuttersense-agent start

# Or run analysis directly
shuttersense-agent test /path/to/photos --tool photostats
shuttersense-agent run <collection-guid> --tool photostats
```

See [Agent Installation Guide](agent-installation.md) for detailed agent setup instructions.

## Virtual Environment Layout

After setup, the repository should have two separate venvs:

```
shuttersense/
├── venv/              # Backend venv (backend/requirements.txt)
├── agent/
│   └── .venv/         # Agent venv (agent/pyproject.toml)
└── frontend/          # Node.js (npm)
```

Do not mix these environments. Each has its own `activate` script.

## Environment Variables

### Required for Backend

| Variable | Description | Example |
| ---------- | ------------- | --------- |
| `SHUSAI_MASTER_KEY` | Fernet key for credential encryption | Generate with Python (see above) |
| `SHUSAI_DB_URL` | PostgreSQL connection URL | `postgresql://user:pass@localhost:5432/shuttersense` |

### Optional

| Variable | Description | Default |
| ---------- | ------------- | --------- |
| `SHUSAI_ENV` | Environment name | `development` |
| `SHUSAI_LOG_LEVEL` | Logging level | `INFO` |

### OAuth Provider Setup (Required for Authentication)

| Variable | Description | Example |
| ---------- | ------------- | --------- |
| `SESSION_SECRET_KEY` | Secret for signing session cookies (min 32 chars) | Generate with `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `SESSION_MAX_AGE` | Session duration in seconds | `86400` (24 hours, default) |
| `SESSION_HTTPS_ONLY` | Require HTTPS for cookies | `true` (production), `false` (development) |

#### Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Navigate to **APIs & Services > Credentials**
4. Create an **OAuth 2.0 Client ID** (Web application)
5. Add authorized redirect URI: `http://localhost:8000/api/auth/google/callback`
6. Set environment variables:
   ```bash
   export GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
   export GOOGLE_CLIENT_SECRET="your-client-secret"
   ```

#### Microsoft OAuth

1. Go to [Azure Portal](https://portal.azure.com/) > **App registrations**
2. Register a new application
3. Add redirect URI: `http://localhost:8000/api/auth/microsoft/callback`
4. Create a client secret under **Certificates & secrets**
5. Set environment variables:
   ```bash
   export MICROSOFT_CLIENT_ID="your-application-id"
   export MICROSOFT_CLIENT_SECRET="your-client-secret"
   ```

### Push Notifications (Optional)

To enable Web Push notifications, generate VAPID keys:

```bash
# Install the web-push library
pip install py-vapid

# Generate VAPID keys
python3 -c "
from py_vapid import Vapid
v = Vapid()
v.generate_keys()
print('VAPID_PUBLIC_KEY=' + v.public_key)
print('VAPID_PRIVATE_KEY=' + v.private_key)
"
```

Set the environment variables:

| Variable | Description |
| ---------- | ------------- |
| `VAPID_PUBLIC_KEY` | Base64url-encoded public key |
| `VAPID_PRIVATE_KEY` | Base64url-encoded private key |
| `VAPID_SUBJECT` | Contact URI (e.g., `mailto:admin@example.com`) |

### Rate Limiting Storage (Optional)

By default, rate limiting uses in-memory storage, which works for single-worker deployments. For multi-worker or multi-instance deployments, use a shared backend so rate limits are enforced globally:

```bash
# Install Redis client library
pip install redis

# Set the storage backend
export RATE_LIMIT_STORAGE_URI="redis://localhost:6379"
```

Supported backends:

| URI | Backend | Notes |
| --- | ------- | ----- |
| `memory://` | In-process | Default. Single-worker only. |
| `redis://host:6379` | Redis | Recommended for multi-worker. Requires `pip install redis`. |
| `memcached://host:11211` | Memcached | Alternative to Redis. Requires `pip install pymemcache`. |
| `redis+sentinel://host:26379` | Redis Sentinel | High-availability Redis. |

### GeoIP Geofencing (Optional)

GeoIP geofencing restricts API access to requests originating from a configurable list of countries, using a local MaxMind GeoLite2-Country database.

#### 1. Obtain the GeoLite2 Database

1. Create a free account at [MaxMind GeoLite2](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data)
2. Download the **GeoLite2-Country** database in `.mmdb` format
3. Place the file on the server (e.g., `/opt/geoip/GeoLite2-Country.mmdb`)

#### 2. Configure Environment Variables

```bash
# Path to the .mmdb database file
export SHUSAI_GEOIP_DB_PATH="/opt/geoip/GeoLite2-Country.mmdb"

# Comma-separated ISO 3166-1 alpha-2 country codes to allow
export SHUSAI_GEOIP_ALLOWED_COUNTRIES="US,CA"

# Block requests from unknown IPs (default: false)
# Set to true to allow requests when GeoIP lookup returns no country
export SHUSAI_GEOIP_FAIL_OPEN="false"
```

**Important notes:**

- Private/loopback IPs (127.x, 10.x, 192.168.x, ::1) always bypass geofencing
- The `/health` endpoint is always exempt
- An empty `SHUSAI_GEOIP_ALLOWED_COUNTRIES` with a configured database path will **block all non-private requests**
- The server must be restarted to pick up database file updates
- Use [geoipupdate](https://github.com/maxmind/geoipupdate) for automated weekly database refreshes

### Complete Environment Variables Reference

| Variable | Required | Description | Default |
| ---------- | ---------- | ------------- | --------- |
| `SHUSAI_MASTER_KEY` | Yes | Fernet encryption key | - |
| `SHUSAI_DB_URL` | Yes | PostgreSQL connection URL | - |
| `SESSION_SECRET_KEY` | Yes (for OAuth) | Session cookie signing key | - |
| `JWT_SECRET_KEY` | Yes (for API tokens) | JWT signing key | - |
| `SHUSAI_ENV` | No | Environment name | `development` |
| `SHUSAI_LOG_LEVEL` | No | Logging level | `INFO` |
| `SHUSAI_SPA_DIST_PATH` | No | Path to frontend dist | `frontend/dist` |
| `SHUSAI_AUTHORIZED_LOCAL_ROOTS` | No | Comma-separated authorized local paths | - |
| `CORS_ORIGINS` | No | Comma-separated allowed origins | `http://localhost:3000,...` |
| `VAPID_PUBLIC_KEY` | No | Web Push public key | - |
| `VAPID_PRIVATE_KEY` | No | Web Push private key | - |
| `VAPID_SUBJECT` | No | Web Push contact URI | - |
| `RATE_LIMIT_STORAGE_URI` | No | Rate limiting storage backend URI | `memory://` |
| `SHUSAI_GEOIP_DB_PATH` | No | Path to GeoLite2-Country .mmdb file | - (disabled) |
| `SHUSAI_GEOIP_ALLOWED_COUNTRIES` | No | Comma-separated allowed country codes | - |
| `SHUSAI_GEOIP_FAIL_OPEN` | No | Allow unknown IPs when `true` | `false` |

> **Note:** In production, the FastAPI server serves both the API and the React SPA frontend from the same origin. Set `SHUSAI_SPA_DIST_PATH` to point to the built frontend `dist/` directory.

## Verify Installation

### Web Application

1. Backend health check: `curl http://localhost:8000/health`
2. Frontend: Open http://localhost:3000 in your browser

### Agent

```bash
shuttersense-agent --version
shuttersense-agent self-test
```

## Development Testing

Backend and agent tests use separate virtual environments:

```bash
# Backend tests (activate backend venv first)
source venv/bin/activate
PYTHONPATH=. python -m pytest backend/tests/ -v

# Frontend tests
cd frontend
npm test

# Agent tests (activate agent venv first)
source agent/.venv/bin/activate
python -m pytest tests/ -v
```

## Troubleshooting

### Python Version
Ensure you have Python 3.12+:
```bash
python --version
```

### Database Connection
If you see database connection errors:
1. Verify PostgreSQL is running: `pg_isready`
2. Check connection URL: `psql $SHUSAI_DB_URL`
3. Run migrations: `cd backend && alembic upgrade head`

### Master Key Issues
The master key must be a valid Fernet key (44 characters, base64). Generate one with:
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Next Steps

- **Agent Users**: See the [Agent Installation Guide](agent-installation.md) for detailed agent setup
- **Agent Developers**: See the [Agent Build Guide](agent-build.md) for building binaries
- **Web Application**: See [backend/README.md](../backend/README.md) for detailed backend setup
- **Configuration**: See the [Configuration Guide](configuration.md) for file type settings
