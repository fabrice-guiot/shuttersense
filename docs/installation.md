# Installation

This guide covers installing the ShutterSense web application and agent.

## Requirements

### Web Application
- Python 3.10 or higher (backend)
- Node.js 18+ and npm (frontend)
- PostgreSQL 12+ (database)
- Git (for cloning the repository)

### Agent
- Python 3.10 or higher (for building from source)
- Or: pre-built binary for your platform (macOS, Linux, Windows)

## Web Application Setup

### 1. Clone the Repository

```bash
git clone https://github.com/fabrice-guiot/photo-admin.git
cd photo-admin
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set required environment variables
export SHUSAI_MASTER_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
export SHUSAI_DB_URL="postgresql://user:password@localhost:5432/shuttersense"

# Create database and run migrations
createdb shuttersense  # Or use your PostgreSQL admin tool
alembic upgrade head

# Start the backend server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

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

### Option A: Pre-built Binary

Download the latest agent binary for your platform from the releases page, then proceed to [Register the Agent](#register-the-agent).

### Option B: Build from Source

```bash
cd agent
pip install -e ".[build]"
./packaging/build_macos.sh  # or build_linux.sh, build_windows.sh
```

The binary will be in `./dist/<platform>/shuttersense-agent`.

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

## Environment Variables

### Required for Backend

| Variable | Description | Example |
|----------|-------------|---------|
| `SHUSAI_MASTER_KEY` | Fernet key for credential encryption | Generate with Python (see above) |
| `SHUSAI_DB_URL` | PostgreSQL connection URL | `postgresql://user:pass@localhost:5432/shuttersense` |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `SHUSAI_ENV` | Environment name | `development` |
| `SHUSAI_LOG_LEVEL` | Logging level | `INFO` |

## Verify Installation

### Web Application

1. Backend health check: `curl http://localhost:8000/health`
2. Frontend: Open http://localhost:3000 in your browser

### Agent

```bash
shuttersense-agent --version
shuttersense-agent self-test
```

## Development Installation

For contributing or running tests:

```bash
# Backend tests
cd backend
python -m pytest tests/ -v

# Frontend tests
cd frontend
npm test

# Agent tests
cd agent
pip install -e ".[dev]"
python -m pytest tests/ -v
```

## Troubleshooting

### Python Version
Ensure you have Python 3.10+:
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
- **Web Application**: See [backend/README.md](../backend/README.md) for detailed backend setup
- **Configuration**: See the [Configuration Guide](configuration.md) for file type settings
