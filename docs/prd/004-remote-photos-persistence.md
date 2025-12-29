# PRD: Remote Photo Collections and Analysis Persistence

**Issue**: #24
**Status**: Draft
**Created**: 2025-12-29
**Last Updated**: 2025-12-29

## Executive Summary

Extend photo-admin from local-only CLI tools to support remote photo collections and persistent storage of analysis results through a database-backed web interface. This evolution enables users to manage multiple collections (local and remote), execute analysis tools, and access historical results through a React-based frontend while maintaining the existing CLI tool capabilities.

## Background

### Current State
- **CLI-Only Tools**: PhotoStats and Photo Pairing operate as standalone Python scripts
- **Local Filesystem**: Analysis limited to locally accessible directories
- **YAML Configuration**: Settings stored in config/config.yaml
- **One-Time Reports**: HTML reports generated per execution, no historical tracking
- **Jinja2 Templates**: Centralized template system for consistent HTML output

### Problem Statement
1. **No Remote Access**: Cannot analyze photo collections on cloud storage (S3, Google Drive, etc.) or network locations
2. **No Persistence**: Analysis results are lost after report generation, preventing trend analysis
3. **Manual Tracking**: Users must manually organize and compare reports across executions
4. **Limited Scalability**: YAML configuration doesn't scale for managing multiple collections

## Goals

### Primary Goals
1. **Remote Collection Support**: Enable analysis of photos stored on remote systems (cloud storage, network shares)
2. **Persistent Storage**: Store collection definitions, configurations, and analysis results in a database
3. **Web Interface**: Provide a React-based UI for collection management and result visualization
4. **Historical Analysis**: Enable trend tracking and comparison of analysis results over time

### Secondary Goals
1. **Maintain CLI Tools**: Existing command-line workflows remain functional
2. **Unified Configuration**: Migrate from YAML to database-backed configuration with backward compatibility
3. **Reuse Templates**: Leverage existing Jinja2 HTML rendering for report generation

### Non-Goals (v1)
1. **User Authentication**: Local-only deployment (localhost) requires no auth system
2. **Multi-User Support**: Single-user operation sufficient for v1
3. **Real-Time Collaboration**: No concurrent editing or shared workspaces
4. **Mobile Application**: Desktop browser interface only

## User Personas

### Primary: Professional Photographer (Alex)
- **Needs**: Manage 10+ photo collections across local drives and cloud storage
- **Pain Point**: Cannot track which collections have orphaned files over time
- **Goal**: Run monthly analysis on all collections and identify degradation trends

### Secondary: Photo Archive Manager (Jamie)
- **Needs**: Validate photo archive integrity across network-attached storage
- **Pain Point**: Manual execution of CLI tools on each mounted drive
- **Goal**: Centralized dashboard showing health of all archive locations

## Requirements

### Functional Requirements

#### FR1: Collection Management
- **FR1.1**: Create collection definitions with name, type (local/remote), and location
- **FR1.2**: Support local filesystem paths and remote URI schemes (s3://, gs://, smb://)
- **FR1.3**: Edit and delete existing collections
- **FR1.4**: List all collections with status indicators (accessible/inaccessible)

#### FR2: Remote Collection Access
- **FR2.1**: Integrate with cloud storage APIs (AWS S3, Google Cloud Storage)
- **FR2.2**: Support authentication credentials per collection (API keys, OAuth tokens)
- **FR2.3**: Cache remote file listings for performance
- **FR2.4**: Handle network failures gracefully with retry logic

#### FR3: Database Persistence
- **FR3.1**: Store collection definitions, configurations, and analysis results
- **FR3.2**: Support complex nested objects from analysis tools (camera groups, file pairings)
- **FR3.3**: Maintain analysis execution history (timestamp, tool, collection, results)
- **FR3.4**: Enable querying historical results for trend analysis

#### FR4: Configuration Migration
- **FR4.1**: Import existing YAML config into database on first run
- **FR4.2**: Manage photo extensions, metadata extensions, camera mappings in database
- **FR4.3**: Provide UI for editing configuration parameters
- **FR4.4**: Export configuration to YAML for CLI tool compatibility

#### FR5: Tool Execution
- **FR5.1**: Trigger PhotoStats and Photo Pairing from web interface
- **FR5.2**: Display real-time progress during analysis execution
- **FR5.3**: Store analysis results in database upon completion
- **FR5.4**: Generate HTML reports from stored results (not just live execution)

#### FR6: Result Visualization
- **FR6.1**: Display historical analysis results in web UI
- **FR6.2**: Generate HTML reports using existing Jinja2 templates
- **FR6.3**: Compare results across multiple executions (trend charts)
- **FR6.4**: Filter and search analysis history by collection, date, tool

### Non-Functional Requirements

#### NFR1: Performance
- **NFR1.1**: Collection listing loads within 2 seconds
- **NFR1.2**: Historical result queries return within 1 second for 1000+ entries
- **NFR1.3**: Remote collection caching reduces redundant API calls by 80%

#### NFR2: Reliability
- **NFR2.1**: Database transactions ensure data consistency
- **NFR2.2**: Failed analysis runs don't corrupt database state
- **NFR2.3**: Remote access failures don't crash the application

#### NFR3: Usability
- **NFR3.1**: Web UI accessible on localhost:PORT with clear navigation
- **NFR3.2**: Error messages provide actionable guidance
- **NFR3.3**: Configuration changes take effect immediately (no restart required)

#### NFR4: Maintainability
- **NFR4.1**: Database schema migrations automated with versioning
- **NFR4.2**: API endpoints documented with OpenAPI/Swagger
- **NFR4.3**: Frontend and backend can be developed independently

#### NFR5: Compatibility
- **NFR5.1**: Existing CLI tools work with database configuration
- **NFR5.2**: Python 3.10+ compatibility maintained
- **NFR5.3**: Cross-platform support (Linux, macOS, Windows)

## Technical Approach

### Architecture Overview

```
┌─────────────────────────────────────────────┐
│           React Web Frontend                │
│  (Collection Mgmt, Config, Results View)    │
└─────────────────┬───────────────────────────┘
                  │ REST API
┌─────────────────▼───────────────────────────┐
│        Python Backend (FastAPI)             │
│  - Collection Service                       │
│  - Tool Execution Service                   │
│  - Config Service                           │
│  - Report Generation (Jinja2)               │
└─────────────────┬───────────────────────────┘
                  │ ORM (SQLAlchemy)
┌─────────────────▼───────────────────────────┐
│            Database Layer                   │
│  PostgreSQL or Document DB (TBD)            │
│  - Collections                              │
│  - Configurations                           │
│  - Analysis Results                         │
└─────────────────────────────────────────────┘
```

### Technology Stack Investigation

#### Database Selection Criteria

**PostgreSQL (Relational)**
- **Pros**:
  - JSON/JSONB columns support complex nested objects
  - ACID compliance ensures data integrity
  - Mature ecosystem with SQLAlchemy ORM
  - Full-text search capabilities
- **Cons**:
  - Schema migrations may be complex for evolving result structures
  - Less flexible for highly variable analysis output formats

**Document Databases (MongoDB/Couchbase)**
- **Pros**:
  - Schema-less design accommodates varying analysis results
  - Natural fit for nested camera groups, file pairings
  - Easier to evolve data models
- **Cons**:
  - Additional infrastructure complexity
  - Weaker consistency guarantees (depending on configuration)
  - Less mature Python tooling compared to PostgreSQL

**Recommendation**: **PostgreSQL with JSONB columns**
- Balances structure (collections, config) with flexibility (analysis results)
- SQLAlchemy ORM provides migration tooling (Alembic)
- JSONB indexing enables efficient querying of nested result data

#### Backend Framework

**FastAPI**
- Async support for non-blocking I/O (remote collection access)
- Automatic OpenAPI documentation
- Pydantic data validation
- WebSocket support for real-time progress updates

#### Frontend Framework

**React**
- Component-based architecture for modular UI
- Rich ecosystem for data visualization (Recharts, Victory)
- Integration with existing Jinja2 templates via iframe or server-side render

#### Remote Storage Libraries

**Cloud Storage Integration**
- **AWS S3**: `boto3` library (official SDK)
- **Google Cloud Storage**: `google-cloud-storage` library
- **SMB/CIFS**: `smbprotocol` or `pysmb` for network shares
- **Abstraction Layer**: Consider `fsspec` for unified filesystem interface

### Data Models (Preliminary)

#### Collections Table
```sql
CREATE TABLE collections (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    type VARCHAR(50) NOT NULL,  -- 'local', 's3', 'gcs', 'smb'
    location TEXT NOT NULL,
    credentials JSONB,  -- encrypted credentials for remote access
    metadata JSONB,  -- custom user-defined fields
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### Configuration Table
```sql
CREATE TABLE configurations (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) NOT NULL UNIQUE,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### Analysis Results Table
```sql
CREATE TABLE analysis_results (
    id SERIAL PRIMARY KEY,
    collection_id INTEGER REFERENCES collections(id),
    tool VARCHAR(50) NOT NULL,  -- 'photostats', 'photo_pairing'
    executed_at TIMESTAMP DEFAULT NOW(),
    results JSONB NOT NULL,  -- full analysis output
    report_html TEXT,  -- generated HTML report
    status VARCHAR(50) NOT NULL,  -- 'completed', 'failed', 'running'
    error_message TEXT
);
```

### API Endpoints (Preliminary)

```
Collections:
  POST   /api/collections          - Create collection
  GET    /api/collections          - List all collections
  GET    /api/collections/{id}     - Get collection details
  PUT    /api/collections/{id}     - Update collection
  DELETE /api/collections/{id}     - Delete collection
  POST   /api/collections/{id}/test - Test collection accessibility

Configuration:
  GET    /api/config               - Get all configuration
  PUT    /api/config/{key}         - Update configuration value
  POST   /api/config/import        - Import from YAML
  GET    /api/config/export        - Export to YAML

Tools:
  POST   /api/tools/photostats     - Run PhotoStats on collection
  POST   /api/tools/photo_pairing  - Run Photo Pairing on collection
  GET    /api/tools/status/{job_id} - Get execution status
  WS     /api/tools/progress/{job_id} - WebSocket for progress updates

Results:
  GET    /api/results              - List analysis results (filterable)
  GET    /api/results/{id}         - Get specific result
  GET    /api/results/{id}/report  - Get HTML report
  DELETE /api/results/{id}         - Delete result
```

### Migration Strategy

#### Phase 1: Database Layer (Weeks 1-2)
1. Set up PostgreSQL database
2. Implement SQLAlchemy models
3. Create Alembic migrations
4. Implement configuration import from YAML
5. Write database integration tests

#### Phase 2: Backend API (Weeks 3-4)
1. Set up FastAPI application
2. Implement collection management endpoints
3. Implement configuration endpoints
4. Integrate existing tools with database storage
5. Add WebSocket support for progress updates

#### Phase 3: Remote Storage (Weeks 5-6)
1. Implement S3 storage adapter
2. Implement Google Cloud Storage adapter
3. Implement SMB/CIFS adapter
4. Add credential encryption/decryption
5. Implement file listing cache

#### Phase 4: Frontend (Weeks 7-9)
1. Set up React application
2. Implement collection management UI
3. Implement configuration management UI
4. Implement tool execution UI with progress
5. Implement results history and visualization

#### Phase 5: CLI Integration (Week 10)
1. Update CLI tools to read from database
2. Add fallback to YAML if database unavailable
3. Add CLI command to start web server
4. Update documentation

#### Phase 6: Testing & Documentation (Week 11-12)
1. End-to-end testing
2. Performance testing with large collections
3. User documentation
4. Deployment guide

## Success Metrics

### Adoption Metrics
- **M1**: 80% of existing users try web interface within 1 month
- **M2**: 50% of collections managed are remote (vs local) within 3 months

### Performance Metrics
- **M3**: Analysis execution time within 10% of CLI tool performance
- **M4**: 95% of collection access operations complete within 5 seconds

### Quality Metrics
- **M5**: Zero data loss incidents in production usage
- **M6**: Test coverage >80% for new backend code

## Risks and Mitigation

### Risk 1: Database Selection Regret
- **Impact**: High - Difficult to migrate after implementation
- **Probability**: Medium
- **Mitigation**: Build abstraction layer for data access; prototype both PostgreSQL and MongoDB with real analysis data

### Risk 2: Remote API Rate Limiting
- **Impact**: Medium - Degrades user experience
- **Probability**: High (especially for cloud storage APIs)
- **Mitigation**: Implement aggressive caching; add rate limit handling with backoff; document API quota requirements

### Risk 3: CLI Tool Compatibility Breaking
- **Impact**: High - Alienates existing users
- **Probability**: Low
- **Mitigation**: Maintain YAML fallback; extensive integration testing; phased rollout with opt-in web features

### Risk 4: Complex Schema Evolution
- **Impact**: Medium - Slows future development
- **Probability**: Medium
- **Mitigation**: Use JSONB for variable data (results); version analysis result schemas; implement schema migration testing

### Risk 5: Frontend-Backend Coupling
- **Impact**: Low - Reduces development velocity
- **Probability**: Medium
- **Mitigation**: Define API contract first; use OpenAPI for documentation; implement mock API for frontend development

## Open Questions

1. **Database Selection**: PostgreSQL vs MongoDB - Which better handles evolving analysis result structures?
2. **Credential Storage**: How to securely encrypt/decrypt remote storage credentials? Use system keyring?
3. **Caching Strategy**: How long to cache remote file listings? Invalidation strategy?
4. **Background Jobs**: Use Celery/RQ for async tool execution, or FastAPI BackgroundTasks?
5. **Report Generation**: Generate HTML on-demand from stored results, or store pre-generated HTML?
6. **Version Compatibility**: How to handle results from different tool versions?
7. **Export Functionality**: Should users be able to export results to CSV, JSON, or other formats?

## Dependencies

### External Services
- Cloud storage accounts (AWS, GCP) for testing remote collections
- Database server (PostgreSQL or MongoDB instance)

### New Python Libraries
- FastAPI (web framework)
- SQLAlchemy (ORM)
- Alembic (database migrations)
- boto3 (AWS S3)
- google-cloud-storage (GCS)
- smbprotocol (SMB/CIFS)
- pydantic (data validation)
- cryptography (credential encryption)

### Frontend Dependencies
- React
- React Router
- Axios (HTTP client)
- Recharts or Victory (data visualization)
- Material-UI or Ant Design (component library)

## Appendix

### Related Issues
- Issue #24: Support for remote Photo collections and longer term persistence

### References
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL JSONB Documentation](https://www.postgresql.org/docs/current/datatype-json.html)
- [boto3 S3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html)
- [React Documentation](https://react.dev/)

### Revision History
- **2025-12-29**: Initial draft based on Issue #24 requirements
