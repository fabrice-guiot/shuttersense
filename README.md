# ShutterSense.ai

<p align="center">
  <img src="frontend/public/og-image.png" alt="ShutterSense.ai - Capture. Process. Analyze." width="600">
</p>

[![Tests](https://github.com/fabrice-guiot/shuttersense/actions/workflows/test.yml/badge.svg)](https://github.com/fabrice-guiot/shuttersense/actions/workflows/test.yml)

A comprehensive solution for analyzing, managing, and validating photo collections across local and remote storage.

## Overview

ShutterSense provides:

- **Web Application** - Modern React/FastAPI application for managing and analyzing photo collections
  - **Backend** (FastAPI) - RESTful API with PostgreSQL storage, encrypted credentials, job queuing
  - **Frontend** (React/TypeScript) - Modern, accessible UI with real-time progress updates
  - **Authentication** - OAuth 2.0 (Google, Microsoft) with session-based auth and API tokens
  - **Multi-Tenancy** - Team-based data isolation with automatic scoping
  - **PWA** - Progressive Web App with push notifications and offline support
  - **Dashboard** - KPI overview with activity feed and queue status
- **Agent** (Python binary) - Distributed executor running on user machines, providing:
  - **PhotoStats** - Analyze photo collections for statistics, file pairing, and metadata
  - **Photo Pairing** - Group related files by filename patterns, track camera usage
  - **Pipeline Validation** - Validate collections against processing workflows

> **Important**: The web application requires at least one agent to process photo analysis jobs. Without an agent, jobs will remain queued but never execute. See [Agent Setup](#agent-setup) below.

## Quick Start

### Web Application

```bash
# Backend
cd backend
pip install -r requirements.txt
export SHUSAI_MASTER_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
export SHUSAI_DB_URL="postgresql://user:pass@localhost:5432/shuttersense"
alembic upgrade head
uvicorn src.main:app --reload

# Frontend (in a new terminal)
cd frontend
npm install
npm run dev
```

See [backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md) for detailed setup instructions.

### Agent Setup

The agent executes photo analysis jobs on your machine. Without an agent, jobs cannot be processed.

```bash
# 1. Download or build the agent binary
cd agent
pip install -e ".[build]"
./packaging/build_macos.sh  # or build_linux.sh, build_windows.sh

# 2. Get a registration token from the web UI
# Navigate to Settings > Agents > Generate Token

# 3. Register the agent
./dist/macos/shuttersense-agent register \
  --server http://localhost:8000 \
  --token art_xxxxx... \
  --name "My Agent"

# 4. Start the agent
./dist/macos/shuttersense-agent start
```

The agent will poll the server for jobs and execute them locally. Leave it running while you want to process jobs.

See [Agent Installation Guide](docs/agent-installation.md) for detailed setup instructions.

## Documentation

### User Guides

- [Installation Guide](docs/installation.md) - Setting up the web application and agent
- [Agent Installation](docs/agent-installation.md) - How to install and run the agent
- [Configuration Guide](docs/configuration.md) - File type and analysis configuration

### Product Requirements

Product requirement documents are stored in [docs/prd/](docs/prd/) for feature planning and design decisions.

### Component Documentation

- **[Backend README](backend/README.md)** - API setup, database migrations, testing, and development guide
- **[Frontend README](frontend/README.md)** - React app setup, component structure, and build configuration
- **[Agent README](agent/README.md)** - Agent setup, commands, and configuration
- **[Agent Build Guide](docs/agent-build.md)** - For developers building agent binaries

### Reference

- [Architecture Overview](docs/architecture.md) - System architecture and data flow
- [Authentication Guide](docs/authentication.md) - OAuth setup and token management
- [Deployment Guide](docs/deployment.md) - Production deployment instructions
- [API Reference](docs/api/README.md) - API conventions and endpoint index
- [Notifications](docs/notifications.md) - Push notification setup
- [Contributing](CONTRIBUTING.md) - Development setup and contribution guidelines

## Project Structure

```
shuttersense/
├── backend/                    # FastAPI backend application
├── frontend/                   # React frontend application
├── agent/                      # Distributed agent for job execution
│   ├── cli/                    # CLI commands (test, run, sync, collection, self-test)
│   ├── src/                    # Agent source code and analysis modules
│   │   ├── analysis/           # PhotoStats, Photo Pairing, Pipeline Validation
│   │   ├── cache/              # Local caching (collections, test results, offline results)
│   │   └── ...                 # API client, job executor, chunked upload
│   ├── packaging/              # Build scripts for standalone binaries
│   └── tests/                  # Agent tests
├── utils/                      # Shared Python utilities
├── templates/                  # Jinja2 HTML report templates
├── docs/                       # Documentation
│   ├── prd/                    # Product requirement documents
│   └── ...                     # Tool and setup documentation
└── CLAUDE.md                   # Development guidelines
```

For detailed project structure:
- Backend: See [backend/README.md](backend/README.md)
- Frontend: See [frontend/README.md](frontend/README.md)
- Agent: See [agent/README.md](agent/README.md)

## Development

### Running Tests

```bash
# Backend tests
cd backend && python -m pytest tests/ -v

# Frontend tests
cd frontend && npm test

# Agent tests
cd agent && python -m pytest tests/ -v
```

### Test Coverage

The project has comprehensive test coverage:
- **Agent**: 678 tests across 39 test files
- **Backend**: ~2,454 tests across 110 test files
- **Frontend**: 57 test files with component and hook tests

See [CLAUDE.md](CLAUDE.md) for development guidelines and coding standards.

## Features

### Remote Storage Support

- **AWS S3** - Native S3 bucket access
- **Google Cloud Storage** - GCS bucket integration
- **SMB/CIFS** - Network share access

### Calendar Events

Plan and track photo-related events with comprehensive management:
- **Events** - Create standalone events or event series with multiple dates
- **Categories** - Organize events with color-coded, icon-enabled categories
- **Locations** - Track venues with address, coordinates, and timezone support
- **Organizers** - Manage event organizers with contact information
- **Performers** - Track performers with social media links and status
- **Logistics** - Track tickets, time-off, and travel requirements per event
- **Configurable Statuses** - Define custom event status workflows

### Authentication & Multi-Tenancy
- **OAuth 2.0** - Sign in with Google or Microsoft accounts
- **API Tokens** - Scoped tokens for agent and programmatic access
- **Multi-Tenancy** - Team-based data isolation
- **Session Management** - Configurable session cookies with secure defaults

### Dashboard
- **KPI Overview** - Collections, agents, jobs, and storage metrics at a glance
- **Activity Feed** - Recent analysis results and agent activity
- **Queue Status** - Real-time job queue monitoring

### Notifications
- **Push Notifications** - Web push for job completions and deadline reminders
- **In-App Notifications** - Bell icon with notification center
- **Preferences** - Per-category notification preferences

### Cloud Inventory Import
- **S3 Inventory** - Import collections from AWS S3 Inventory reports
- **GCS Storage Insights** - Import from Google Cloud Storage Insights

### Mobile Responsive
- **Responsive Tables** - Card-based layout on mobile
- **Responsive Tabs** - Dropdown navigation on small screens

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
