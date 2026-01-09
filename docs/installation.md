# Installation

This guide covers installing the photo-admin toolbox, including CLI tools and the web application.

## Requirements

### CLI Tools
- Python 3.10 or higher
- pip package manager
- Git (for cloning the repository)

### Web Application (Optional)
- Node.js 18+ and npm (for frontend)
- PostgreSQL 12+ (for backend database)

## Quick Start - CLI Tools Only

If you only need the CLI tools (PhotoStats, Photo Pairing, Pipeline Validation):

```bash
# Clone the repository
git clone https://github.com/fabrice-guiot/photo-admin.git
cd photo-admin

# Install dependencies
pip install -r requirements.txt

# Verify installation
python photo_stats.py --help
python photo_pairing.py --help
python pipeline_validation.py --help
```

## Full Installation - Web Application

For the complete web application with remote collection management:

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
export PHOTO_ADMIN_MASTER_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
export PHOTO_ADMIN_DB_URL="postgresql://user:password@localhost:5432/photo_admin"

# Create database and run migrations
createdb photo_admin  # Or use your PostgreSQL admin tool
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

## Environment Variables

### Required for Backend

| Variable | Description | Example |
|----------|-------------|---------|
| `PHOTO_ADMIN_MASTER_KEY` | Fernet key for credential encryption | Generate with Python (see above) |
| `PHOTO_ADMIN_DB_URL` | PostgreSQL connection URL | `postgresql://user:pass@localhost:5432/photo_admin` |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `PHOTO_ADMIN_ENV` | Environment name | `development` |
| `PHOTO_ADMIN_LOG_LEVEL` | Logging level | `INFO` |

## Verify Installation

### CLI Tools

```bash
python photo_stats.py --version
python photo_pairing.py --version
python pipeline_validation.py --version
```

### Web Application

1. Backend health check: `curl http://localhost:8000/health`
2. Frontend: Open http://localhost:3000 in your browser

## Development Installation

For contributing or running tests:

```bash
# CLI tool tests
python -m pytest tests/ -v

# Backend tests
cd backend
python -m pytest tests/ -v

# Frontend tests
cd frontend
npm test
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
2. Check connection URL: `psql $PHOTO_ADMIN_DB_URL`
3. Run migrations: `cd backend && alembic upgrade head`

### Master Key Issues
The master key must be a valid Fernet key (44 characters, base64). Generate one with:
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Next Steps

- **CLI Users**: See the [Configuration Guide](configuration.md) for setting up your config file
- **Web Application**: See [backend/README.md](../backend/README.md) for detailed backend setup
- **Tool Documentation**: [PhotoStats](photostats.md), [Photo Pairing](photo-pairing.md), [Pipeline Validation](pipeline-validation.md)
