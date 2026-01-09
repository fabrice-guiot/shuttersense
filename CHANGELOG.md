# Changelog

All notable changes to photo-admin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-01-09

### Added

#### Web Application
- **Full-stack web application** for remote photo collection management
  - FastAPI backend with OpenAPI documentation
  - React 18 + TypeScript frontend with Tailwind CSS
  - PostgreSQL database with SQLAlchemy ORM

#### Remote Collection Support (US1)
- **AWS S3 connector** - Manage photo collections in S3 buckets
- **Google Cloud Storage connector** - Manage photo collections in GCS buckets
- **SMB/CIFS connector** - Manage photo collections on network shares
- **Credential encryption** - Fernet encryption for stored credentials
- **Connection testing** - Verify connector connectivity before use

#### Tool Execution (US1)
- **Job queue system** - Background execution of analysis tools
- **Real-time progress** - WebSocket-based progress monitoring
- **Run all tools** - Execute all analysis tools on a collection
- **Results storage** - Persistent storage of analysis results in PostgreSQL

#### Pipeline Management (US2)
- **Visual pipeline editor** - Create and edit processing pipelines
- **Pipeline validation** - Validate pipelines with the pipeline_validation tool
- **Display graph mode** - Visualize filename flow through pipeline stages
- **Pipeline versioning** - Track pipeline changes over time
- **Default pipeline** - Configurable default pipeline per collection

#### Trend Analysis (US3)
- **Historical metrics** - Track metrics over time across analysis runs
- **Trend visualization** - Charts showing metric trends with Recharts
- **Metric extraction** - Extract key metrics from stored results
- **Collection comparison** - Compare metrics across collections

#### Configuration Migration (US4)
- **YAML import** - Import configuration from YAML files
- **Conflict detection** - Detect and resolve configuration conflicts
- **Database-first** - CLI tools read configuration from database
- **YAML fallback** - Fall back to YAML when database unavailable
- **Export support** - Export configuration to YAML format

#### Security (US5)
- **Rate limiting** - slowapi middleware (10 req/min for tool execution)
- **Request size limits** - 10MB max upload size
- **Security headers** - CSP, X-Frame-Options, X-XSS-Protection, etc.
- **SQL injection prevention** - SQLAlchemy ORM with parameterized queries
- **Credential audit logging** - Log all credential access events
- **CORS configuration** - Configurable allowed origins

#### Performance (US5)
- **Connection pooling** - SQLAlchemy connection pool configuration
- **GIN indexes** - JSONB query optimization for results_json
- **File listing cache** - State-based TTL for collection file listings
- **Pagination** - Paginated results for large datasets

#### Documentation
- **Updated installation guide** - Web application setup instructions
- **Backend README** - API setup, migrations, environment variables
- **Frontend README** - Component structure, development guide
- **CLAUDE.md** - Development guidelines and coding standards

### Changed

- **Python 3.10+ required** - For match/case syntax and modern type hints
- **Centralized version management** - Git tag-based versioning across all components

### CLI Tools

These standalone CLI tools were available prior to v1.0.0:

- **PhotoStats** - Analyze photo collections for statistics and orphaned files
- **Photo Pairing** - Group files by filename patterns, track camera usage
- **Pipeline Validation** - Validate collections against processing pipelines

## Migration from CLI-only Usage

If you were using photo-admin as CLI tools only:

1. **No changes required** - CLI tools continue to work as before
2. **Optional database** - CLI tools can now read config from PostgreSQL
3. **YAML fallback** - If database unavailable, CLI uses YAML config as before

To enable database configuration for CLI tools:

```bash
export PHOTO_ADMIN_DB_URL="postgresql://user:pass@localhost:5432/photo_admin"
```

---

[Unreleased]: https://github.com/fabrice-guiot/photo-admin/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/fabrice-guiot/photo-admin/releases/tag/v1.0.0
