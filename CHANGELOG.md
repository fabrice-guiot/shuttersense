# Changelog

All notable changes to ShutterSense.ai will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Dashboard

- **Dashboard landing page with KPIs** - Aggregated statistics and quick-access widgets on the home page ([#127])

### Calendar & Events

- **Filter inactive categories from EventForm** - Inactive categories no longer appear in event creation dropdowns ([#77])

### Identity & Security

- **Multi-tenant user authentication** - OAuth 2.0 login (Google, Microsoft), session-based auth, API tokens, and team-scoped data isolation ([#86])

### UI/UX Polish

- **ShutterSense.ai rebrand** - Project renamed from photo-admin to ShutterSense.ai across all components ([#88])
- **Serve SPA and APIs from same server** - Frontend and backend served from a single FastAPI process ([#84])

### Agent Architecture

- **Distributed Agent Architecture** - Lightweight agents claim and execute jobs from the server queue; server acts as coordinator only ([#96])
- **Remove CLI direct usage** - Standalone CLI tools removed; all tool execution consolidated through the ShutterSense agent binary ([#121])

### Storage & Analytics

- **Storage Optimization for Analysis Results** - Efficient JSONB storage, GIN indexes, and pagination for large result sets ([#104])
- **Fix trend aggregation** - Corrected metric extraction and time-series aggregation for trend charts ([#108])
- **Normalize OpenAPI specification structure** - Consistent API schema naming and organization ([#116])

### Cloud Integration

- **Cloud Storage Bucket Inventory Import MVP** - S3 Inventory and GCS Storage Insights integration for bulk file discovery ([#112])
- **Bucket inventory import phases 6-9** - Incremental import, conflict resolution, progress tracking, and scheduling ([#117])

### Mobile & PWA

- **Mobile responsive tables and tabs** - Adaptive table layouts and tab navigation for small screens ([#125])
- **PWA with push notifications** - Installable Progressive Web App with push notification support for job completion alerts ([#129])

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

## [1.1.0] - 2026-01-14

### Added

- **Calendar Events feature** - Full event lifecycle with CRUD, multi-day events, locations, organizers, performers, and configurable statuses ([#70])
- **Event deadline in Calendar view** - Workflow deadlines displayed on the calendar ([#82])
- **Instagram handle for Locations/Organizers** - Social media integration for event entities ([#81])
- **Compact calendar view for mobile** - Responsive calendar layout for small screens ([#80])
- **Single Title Pattern** - Consistent page layout with titles only in TopHeader ([#79])
- **Global Unique Identifiers (GUIDs)** - Prefixed GUID system for all entities ([#64])
- **Dark theme compliance** - Complete dark mode support across the application ([#65])
- **User timezone display** - Localized date and time rendering ([#66])

### Fixed

- **Filter inactive categories from EventForm** - Inactive categories excluded from dropdowns ([#77])

## [0.4] - 2026-01-09

### Added

- **Complete Epic 007** - Remote Photos Completion with production-ready application ([#63])
  - Trend analysis with historical metrics and visualization
  - Configuration migration from YAML to database
  - Display graph enhancements with termination type analysis
  - WebSocket job completion callbacks
  - Analytics page consolidating Results and Tools
  - Production security hardening (Phase 7 & 8)

## [0.3] - 2026-01-03

### Added

- **UI Migration to Modern Design System** - Migrated from MUI to shadcn/ui with TypeScript, Tailwind CSS, and Radix UI primitives ([#44])
- **UX Polish: KPI Metrics, Search, Sidebar Collapse** - TopHeader KPI stats, collection search, and collapsible sidebar ([#47])
- **Centralized version management** - Git tag-based version synchronization across agent, backend, and frontend ([#48])

## [0.2] - 2026-01-01

### Added

- **Remote photos persistence** - Backend web application foundation with FastAPI, PostgreSQL, SQLAlchemy ORM, and React frontend ([#32])

## [0.1] - 2025-12-29

### Added

- **CI/CD status badge** - GitHub Actions build status in README ([#1])
- **AGPL v3 license** - GNU Affero General Public License ([#2])
- **Improved report content** - Reports focused on image analysis rather than raw file stats ([#6])
- **Config management refactoring** - Reusable PhotoAdminConfig class with interactive prompts ([#8])
- **Photo Pairing Tool** - Group files by filename patterns, track camera usage and processing methods ([#15])
- **HTML Report Consistency & Tool Improvements** - Shared Jinja2 base template, --help flags, graceful CTRL+C, atomic writes, timestamped filenames ([#17])
- **Pipeline Validation Tool** - Validate photo collections against processing pipelines with display graph mode ([#23])

---

[Unreleased]: https://github.com/fabrice-guiot/shuttersense/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/fabrice-guiot/shuttersense/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/fabrice-guiot/shuttersense/releases/tag/v1.0.0
[0.4]: https://github.com/fabrice-guiot/shuttersense/compare/v0.3...v0.4
[0.3]: https://github.com/fabrice-guiot/shuttersense/compare/v0.2...v0.3
[0.2]: https://github.com/fabrice-guiot/shuttersense/compare/v0.1...v0.2
[0.1]: https://github.com/fabrice-guiot/shuttersense/releases/tag/v0.1

[#1]: https://github.com/fabrice-guiot/shuttersense/pull/1
[#2]: https://github.com/fabrice-guiot/shuttersense/pull/2
[#6]: https://github.com/fabrice-guiot/shuttersense/pull/6
[#8]: https://github.com/fabrice-guiot/shuttersense/pull/8
[#15]: https://github.com/fabrice-guiot/shuttersense/pull/15
[#17]: https://github.com/fabrice-guiot/shuttersense/pull/17
[#23]: https://github.com/fabrice-guiot/shuttersense/pull/23
[#32]: https://github.com/fabrice-guiot/shuttersense/pull/32
[#44]: https://github.com/fabrice-guiot/shuttersense/pull/44
[#47]: https://github.com/fabrice-guiot/shuttersense/pull/47
[#48]: https://github.com/fabrice-guiot/shuttersense/pull/48
[#63]: https://github.com/fabrice-guiot/shuttersense/pull/63
[#64]: https://github.com/fabrice-guiot/shuttersense/pull/64
[#65]: https://github.com/fabrice-guiot/shuttersense/pull/65
[#66]: https://github.com/fabrice-guiot/shuttersense/pull/66
[#70]: https://github.com/fabrice-guiot/shuttersense/pull/70
[#77]: https://github.com/fabrice-guiot/shuttersense/pull/77
[#79]: https://github.com/fabrice-guiot/shuttersense/pull/79
[#80]: https://github.com/fabrice-guiot/shuttersense/pull/80
[#81]: https://github.com/fabrice-guiot/shuttersense/pull/81
[#82]: https://github.com/fabrice-guiot/shuttersense/pull/82
[#84]: https://github.com/fabrice-guiot/shuttersense/pull/84
[#86]: https://github.com/fabrice-guiot/shuttersense/pull/86
[#88]: https://github.com/fabrice-guiot/shuttersense/pull/88
[#96]: https://github.com/fabrice-guiot/shuttersense/pull/96
[#104]: https://github.com/fabrice-guiot/shuttersense/pull/104
[#108]: https://github.com/fabrice-guiot/shuttersense/pull/108
[#112]: https://github.com/fabrice-guiot/shuttersense/pull/112
[#116]: https://github.com/fabrice-guiot/shuttersense/pull/116
[#117]: https://github.com/fabrice-guiot/shuttersense/pull/117
[#121]: https://github.com/fabrice-guiot/shuttersense/pull/121
[#125]: https://github.com/fabrice-guiot/shuttersense/pull/125
[#127]: https://github.com/fabrice-guiot/shuttersense/pull/127
[#129]: https://github.com/fabrice-guiot/shuttersense/pull/129
