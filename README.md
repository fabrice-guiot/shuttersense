# photo-admin

[![Tests](https://github.com/fabrice-guiot/photo-admin/actions/workflows/test.yml/badge.svg)](https://github.com/fabrice-guiot/photo-admin/actions/workflows/test.yml)

Photo Administration toolbox - A comprehensive solution for analyzing, managing, and validating photo collections across local and remote storage.

## Overview

photo-admin provides two main components:

1. **CLI Tools** - Python utilities for photo collection analysis
2. **Web Application** - Modern React/FastAPI application for remote collection management

### CLI Tools

- **PhotoStats** - Analyze photo collections for statistics, file pairing, and metadata extraction
- **Photo Pairing** - Group related files by filename patterns, track camera usage, generate analytics
- **Pipeline Validation** - Validate photo collections against user-defined processing workflows

### Web Application

A full-stack application for managing remote photo collections:
- **Backend** (FastAPI) - RESTful API with PostgreSQL storage, encrypted credentials, job queuing
- **Frontend** (React/TypeScript) - Modern, accessible UI with real-time progress updates

## Quick Start

### CLI Tools

```bash
# Clone the repository
git clone https://github.com/fabrice-guiot/photo-admin.git
cd photo-admin

# Install dependencies
pip install -r requirements.txt

# Run PhotoStats
python photo_stats.py /path/to/your/photos

# Run Photo Pairing
python photo_pairing.py /path/to/photos

# Run Pipeline Validation
python pipeline_validation.py /path/to/photos
```

### Web Application

```bash
# Backend
cd backend
pip install -r requirements.txt
export PHOTO_ADMIN_MASTER_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
export PHOTO_ADMIN_DB_URL="postgresql://user:pass@localhost:5432/photo_admin"
alembic upgrade head
uvicorn src.main:app --reload

# Frontend (in a new terminal)
cd frontend
npm install
npm run dev
```

See [backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md) for detailed setup instructions.

## Documentation

### User Guides

- [Installation Guide](docs/installation.md) - Detailed installation instructions
- [Configuration Guide](docs/configuration.md) - How to configure file types and settings
- [PhotoStats Tool](docs/photostats.md) - Complete guide to using PhotoStats
- [Photo Pairing Tool](docs/photo-pairing.md) - Complete guide to Photo Pairing
- [Pipeline Validation Tool](docs/pipeline-validation.md) - Complete guide to Pipeline Validation

### Product Requirements

Product requirement documents are stored in [docs/prd/](docs/prd/) for feature planning and design decisions.

### Component Documentation

- **[Backend README](backend/README.md)** - API setup, database migrations, testing, and development guide
- **[Frontend README](frontend/README.md)** - React app setup, component structure, and build configuration

## Project Structure

```
photo-admin/
├── photo_stats.py              # PhotoStats CLI tool
├── photo_pairing.py            # Photo Pairing CLI tool
├── pipeline_validation.py      # Pipeline Validation CLI tool
├── utils/                      # Shared Python utilities
├── templates/                  # Jinja2 HTML report templates
├── config/                     # Configuration files
├── backend/                    # FastAPI backend application
├── frontend/                   # React frontend application
├── docs/                       # Documentation
│   ├── prd/                    # Product requirement documents
│   └── ...                     # Tool documentation
├── tests/                      # CLI tool tests
├── requirements.txt            # Python dependencies
└── CLAUDE.md                   # Development guidelines
```

For detailed project structure:
- CLI tools and utilities: See this README
- Backend structure: See [backend/README.md](backend/README.md)
- Frontend structure: See [frontend/README.md](frontend/README.md)

## Development

### Running Tests

```bash
# CLI tool tests
python -m pytest tests/ -v

# Backend tests
cd backend && python -m pytest tests/ -v

# Frontend tests
cd frontend && npm test
```

### Test Coverage

The project has comprehensive test coverage:
- **CLI Tools**: 160+ tests (PhotoStats, Photo Pairing, Pipeline Validation)
- **Backend**: 300+ tests (unit + integration)
- **Frontend**: Component and hook tests

See [CLAUDE.md](CLAUDE.md) for development guidelines and coding standards.

## Features

### Remote Storage Support

- **AWS S3** - Native S3 bucket access
- **Google Cloud Storage** - GCS bucket integration
- **SMB/CIFS** - Network share access

### Calendar Events (Issue #39)

Plan and track photo-related events with comprehensive management:
- **Events** - Create standalone events or event series with multiple dates
- **Categories** - Organize events with color-coded, icon-enabled categories
- **Locations** - Track venues with address, coordinates, and timezone support
- **Organizers** - Manage event organizers with contact information
- **Performers** - Track performers with social media links and status
- **Logistics** - Track tickets, time-off, and travel requirements per event
- **Configurable Statuses** - Define custom event status workflows

### Security

- Fernet encryption for stored credentials
- Rate limiting on sensitive endpoints
- Security headers (CSP, X-Frame-Options, etc.)
- SQL injection prevention via SQLAlchemy ORM

### Performance

- PostgreSQL with connection pooling
- GIN indexes for JSONB queries
- File listing cache with state-based TTL
- Real-time progress via WebSocket

## License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).

See the [LICENSE](LICENSE) file for details.

### What this means:

- You can use, modify, and distribute this software freely
- If you run a modified version on a server, you must make the source code available to users
- Any derivative works must also be licensed under AGPL v3
- This ensures the software remains free and open for the community

For more information, visit: https://www.gnu.org/licenses/agpl-3.0.html
