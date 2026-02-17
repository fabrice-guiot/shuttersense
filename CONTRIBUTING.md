# Contributing to ShutterSense

Thank you for your interest in contributing to ShutterSense! This guide covers the development workflow, coding standards, and submission process.

## Development Setup

### Prerequisites

- **Python 3.12+** (backend and agent)
- **Node.js 18+** (frontend)
- **PostgreSQL 12+** (backend database)
- **Git**

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set required environment variables
export SHUSAI_MASTER_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
export SHUSAI_DB_URL="postgresql://user:password@localhost:5432/shuttersense"
export SESSION_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
export JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Run database migrations
alembic upgrade head

# Start the development server
uvicorn src.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm ci
npm run dev    # Start dev server on port 3000
```

### Agent

```bash
cd agent
pip install -e ".[dev]"

# Run from source
python -m cli.main --help
```

## Branch Naming Convention

Use the following format for branch names:

```text
<issue-number>-<short-description>
```

Examples:
- `42-guid-system`
- `86-oauth-authentication`
- `125-mobile-responsive-tables`

For branches without a linked issue:
- `fix/typo-in-readme`
- `docs/update-api-reference`

## Pull Request Process

1. **Create a branch** from `main` using the naming convention above
2. **Make your changes** with comprehensive tests
3. **Run tests locally** to verify nothing is broken
4. **Push your branch** and open a pull request
5. **Fill out the PR template** with a summary and test plan
6. **Address review feedback** and update as needed
7. **Squash and merge** once approved

### PR Title Format

Use a concise, descriptive title:
- `feat(#42): Add GUID system for all entities`
- `fix(#108): Correct trend aggregation metrics`
- `docs: Update deployment guide`

### PR Description

Include:
- **Summary** of changes (what and why)
- **Test plan** with steps to verify the changes
- **Screenshots** for UI changes

## Code Style

### Python (Backend & Agent)

- Follow **PEP 8** conventions
- Use **ruff** for linting and formatting
- Line length: **120 characters**
- Use **type hints** where beneficial
- All functions should have **docstrings** with Args/Returns

```bash
# Lint
ruff check .

# Format
ruff format .
```

### TypeScript (Frontend)

- Use **ESLint** with the project configuration
- Use **TypeScript strict mode**
- Follow the [Design System](frontend/docs/design-system.md) for UI components
- Import domain labels from `@/contracts/domain-labels.ts`

```bash
cd frontend
npm run lint
npm run typecheck
```

### Commit Messages

Write clear, concise commit messages:
- Use imperative mood ("Add feature" not "Added feature")
- Reference issue numbers where applicable
- Keep the first line under 72 characters

## Testing Requirements

### Coverage Targets

| Component | Target |
| ----------- | -------- |
| Backend core logic | >80% |
| Agent core logic | >80% |
| Utility functions | >85% |
| Overall | >65% |

### Running Tests

```bash
# Backend
python3 -m pytest backend/tests/ -v
python3 -m pytest backend/tests/ --cov=backend.src --cov-report=term-missing

# Agent
python3 -m pytest agent/tests/ -v
python3 -m pytest agent/tests/ --cov=src --cov=cli --cov-report=term-missing

# Frontend
cd frontend && npm test
```

### Test Guidelines

- Write tests alongside implementation
- Use **pytest** fixtures for reusable test data
- Use **monkeypatch** for mocking user input and file I/O
- Group related tests in test classes
- Include both unit tests and integration tests for API endpoints
- Backend tests use SQLite in-memory databases (no PostgreSQL required)

## Documentation Requirements

- Update relevant documentation when changing functionality
- Add docstrings to all new functions and classes
- Update `CHANGELOG.md` for user-facing changes
- Update `CLAUDE.md` if adding new architectural patterns or conventions

## Architecture Guidelines

Before contributing, review these key architectural principles:

1. **GUID-based identifiers** - All entities use prefixed GUIDs in APIs (see `docs/domain-model.md`)
2. **Multi-tenancy** - All data is scoped to teams via `TenantContext`
3. **Agent-only execution** - Analysis tools run on agents, not the server
4. **Single Title Pattern** - Page titles appear only in TopHeader
5. **TopHeader KPI Pattern** - All pages display stats in the header

See `CLAUDE.md` for the complete set of development guidelines.

## Reporting Issues

Use the [GitHub issue tracker](https://github.com/fabrice-guiot/shuttersense/issues) to report bugs or request features. Include:

- Steps to reproduce (for bugs)
- Expected vs actual behavior
- Environment details (OS, Python/Node version, browser)
- Screenshots or logs where helpful

## License

By contributing to ShutterSense, you agree that your contributions will be licensed under the [GNU Affero General Public License v3.0 (AGPL-3.0)](LICENSE).
