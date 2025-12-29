# PRD: Remote Photo Collections and Analysis Persistence

**Issue**: #24
**Status**: Draft
**Created**: 2025-12-29
**Last Updated**: 2025-12-29

## Executive Summary

Extend photo-admin from local-only CLI tools to support remote photo collections and persistent storage of analysis results through a database-backed web interface. This evolution enables users to manage multiple collections (local and remote), execute analysis tools, and access historical results through a React-based frontend while maintaining the existing CLI tool capabilities.

## Background

### Current State
- **CLI-Only Tools**: PhotoStats, Photo Pairing, and Pipeline Validation operate as standalone Python scripts
- **Local Filesystem**: Analysis limited to locally accessible directories
- **YAML Configuration**: Settings stored in config/config.yaml, including complex pipeline definitions
- **One-Time Reports**: HTML reports generated per execution, no historical tracking
- **Jinja2 Templates**: Centralized template system for consistent HTML output
- **Pipeline Validation**: Validates photo collections against user-defined processing workflows (directed graphs)

### Problem Statement
1. **No Remote Access**: Cannot analyze photo collections on cloud storage (S3, Google Drive, etc.) or network locations
2. **No Persistence**: Analysis results are lost after report generation, preventing trend analysis
3. **Manual Tracking**: Users must manually organize and compare reports across executions
4. **Limited Scalability**: YAML configuration doesn't scale for managing multiple collections
5. **Complex Pipeline Configuration**: Editing pipeline graphs in YAML is error-prone and difficult to visualize

## Goals

### Primary Goals
1. **Remote Collection Support**: Enable analysis of photos stored on remote systems (cloud storage, network shares)
2. **Persistent Storage**: Store collection definitions, configurations, and analysis results in a database
3. **Web Interface**: Provide a React-based UI for collection management and result visualization
4. **Historical Analysis**: Enable trend tracking and comparison of analysis results over time
5. **Pipeline Configuration UI**: Enable visual pipeline configuration through web forms (future: graph editor)

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

### Tertiary: Workflow-Focused Photographer (Taylor)
- **Needs**: Track which photos have completed processing pipeline (RAW → DNG → Edit → Archive)
- **Pain Point**: Manually editing complex YAML pipeline definitions is error-prone; cannot visualize workflow
- **Goal**: Define processing pipeline through visual forms, validate collections, identify incomplete images
- **Use Case**: Run Pipeline Validation monthly to find photos stuck at intermediate processing stages

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

#### FR5: Pipeline Configuration Management
- **FR5.1**: Store pipeline definitions in database (nodes, edges, processing methods)
- **FR5.2**: Provide form-based pipeline editor for creating/editing pipeline configurations
- **FR5.3**: Validate pipeline structure (no orphaned nodes, valid references, cycle detection)
- **FR5.4**: Support all node types (Capture, File, Process, Pairing, Branching, Termination)
- **FR5.5**: Preview expected filenames for a given pipeline configuration
- **FR5.6**: Export/import pipelines as YAML for CLI tool compatibility
- **FR5.7**: Version pipeline configurations with change history

#### FR6: Tool Execution
- **FR6.1**: Trigger PhotoStats, Photo Pairing, and Pipeline Validation from web interface
- **FR6.2**: Display real-time progress during analysis execution
- **FR6.3**: Store analysis results in database upon completion
- **FR6.4**: Generate HTML reports from stored results (not just live execution)
- **FR6.5**: Select active pipeline configuration before running Pipeline Validation

#### FR7: Result Visualization
- **FR7.1**: Display historical analysis results in web UI
- **FR7.2**: Generate HTML reports using existing Jinja2 templates
- **FR7.3**: Compare results across multiple executions (trend charts)
- **FR7.4**: Filter and search analysis history by collection, date, tool
- **FR7.5**: Visualize pipeline validation results (CONSISTENT, PARTIAL, INCONSISTENT breakdowns)
- **FR7.6**: Display archival readiness metrics per termination type

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
┌─────────────────────────────────────────────────────┐
│           React Web Frontend                        │
│  - Collection Management                            │
│  - Configuration Editor                             │
│  - Pipeline Editor (Forms, v2: React Flow)          │
│  - Tool Execution Dashboard                         │
│  - Results & Trend Visualization                    │
└─────────────────┬───────────────────────────────────┘
                  │ REST API + WebSocket
┌─────────────────▼───────────────────────────────────┐
│        Python Backend (FastAPI)                     │
│  - Collection Service (local/remote)                │
│  - Tool Execution Service (PhotoStats, Pairing,     │
│    Pipeline Validation)                             │
│  - Config Service (extensions, cameras, methods)    │
│  - Pipeline Service (CRUD, validation, versioning)  │
│  - Report Generation (Jinja2)                       │
│  - Remote Storage Adapters (S3, GCS, SMB)           │
└─────────────────┬───────────────────────────────────┘
                  │ ORM (SQLAlchemy)
┌─────────────────▼───────────────────────────────────┐
│            PostgreSQL Database                      │
│  - Collections (local & remote)                     │
│  - Configurations (extensions, cameras, methods)    │
│  - Pipelines (nodes, edges, versions)               │
│  - Analysis Results (PhotoStats, Pairing, Pipeline) │
│  - Pipeline History (versioning, change tracking)   │
└─────────────────────────────────────────────────────┘
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
    tool VARCHAR(50) NOT NULL,  -- 'photostats', 'photo_pairing', 'pipeline_validation'
    pipeline_id INTEGER REFERENCES pipelines(id),  -- NULL for non-pipeline tools
    executed_at TIMESTAMP DEFAULT NOW(),
    results JSONB NOT NULL,  -- full analysis output
    report_html TEXT,  -- generated HTML report
    status VARCHAR(50) NOT NULL,  -- 'completed', 'failed', 'running'
    error_message TEXT
);
```

#### Pipelines Table
```sql
CREATE TABLE pipelines (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    config JSONB NOT NULL,  -- pipeline nodes and edges definition
    is_active BOOLEAN DEFAULT FALSE,  -- active pipeline for validation
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### Pipeline History Table
```sql
CREATE TABLE pipeline_history (
    id SERIAL PRIMARY KEY,
    pipeline_id INTEGER REFERENCES pipelines(id),
    version INTEGER NOT NULL,
    config JSONB NOT NULL,  -- historical pipeline configuration
    changed_by VARCHAR(255),
    changed_at TIMESTAMP DEFAULT NOW(),
    change_notes TEXT
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

Pipelines:
  GET    /api/pipelines            - List all pipelines
  POST   /api/pipelines            - Create pipeline
  GET    /api/pipelines/{id}       - Get pipeline details
  PUT    /api/pipelines/{id}       - Update pipeline
  DELETE /api/pipelines/{id}       - Delete pipeline
  POST   /api/pipelines/{id}/validate - Validate pipeline structure
  POST   /api/pipelines/{id}/activate - Set as active pipeline
  GET    /api/pipelines/{id}/preview - Preview expected filenames
  GET    /api/pipelines/{id}/history - Get version history
  POST   /api/pipelines/import     - Import from YAML
  GET    /api/pipelines/{id}/export - Export to YAML

Tools:
  POST   /api/tools/photostats     - Run PhotoStats on collection
  POST   /api/tools/photo_pairing  - Run Photo Pairing on collection
  POST   /api/tools/pipeline_validation - Run Pipeline Validation on collection
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
2. Implement SQLAlchemy models (collections, configurations, pipelines, results)
3. Create Alembic migrations
4. Implement configuration import from YAML
5. Implement pipeline import from YAML
6. Write database integration tests

#### Phase 2: Backend API (Weeks 3-4)
1. Set up FastAPI application
2. Implement collection management endpoints
3. Implement configuration endpoints
4. Implement pipeline management endpoints (CRUD, validation, activation)
5. Integrate existing tools with database storage
6. Add WebSocket support for progress updates

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
4. Implement form-based pipeline editor (node creation, editing, validation)
5. Implement tool execution UI with progress (including Pipeline Validation)
6. Implement results history and visualization
7. Add pipeline validation result visualization (CONSISTENT/PARTIAL/INCONSISTENT)

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
- **M3**: 60% of Pipeline Validation users switch from YAML editing to form-based editor within 2 months

### Performance Metrics
- **M4**: Analysis execution time within 10% of CLI tool performance
- **M5**: 95% of collection access operations complete within 5 seconds
- **M6**: Pipeline validation completes within 2 seconds for cached results (same as CLI)

### Quality Metrics
- **M7**: Zero data loss incidents in production usage
- **M8**: Test coverage >80% for new backend code
- **M9**: Pipeline configuration errors reduced by 70% compared to manual YAML editing

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

### Risk 6: Pipeline Configuration Complexity
- **Impact**: Medium - Form-based editor may be cumbersome for complex pipelines
- **Probability**: High (for pipelines with >15 nodes)
- **Mitigation**: Start with form-based editor for v1; plan React Flow graph editor for v2; provide YAML import/export for power users

## Future Enhancements (Post-v1)

### Visual Pipeline Editor with React Flow

**Rationale**: While v1 will provide a form-based pipeline editor, complex pipelines with branching, pairing nodes, and multiple terminations become difficult to visualize and edit through forms alone.

**Technology**: [React Flow](https://reactflow.dev/) - A highly customizable React library for building node-based editors and interactive diagrams.

**Features for v2**:
1. **Drag-and-Drop Nodes**: Visually create pipeline nodes by dragging from a palette
2. **Visual Edge Connections**: Connect nodes by dragging edges between output/input ports
3. **Node Validation**: Real-time visual feedback on invalid connections (e.g., orphaned nodes)
4. **Auto-Layout**: Automatic graph layout algorithms for complex pipelines
5. **Zoom & Pan**: Navigate large pipeline graphs with smooth interactions
6. **Minimap**: Overview map for large pipelines
7. **Export to YAML**: Convert visual graph to YAML configuration
8. **Import from YAML**: Automatically layout existing YAML pipelines

**Benefits**:
- Reduces cognitive load for understanding complex workflows
- Prevents configuration errors through visual validation
- Enables rapid prototyping of pipeline architectures
- Improves onboarding for new users

**Acceptance Criteria for v2**:
- User can create a 20-node pipeline with branching and pairing visually
- Graph automatically detects cycles and orphaned nodes
- Changes save to database in real-time
- Export matches existing YAML schema exactly

## Open Questions

1. **Database Selection**: PostgreSQL vs MongoDB - Which better handles evolving analysis result structures?
2. **Credential Storage**: How to securely encrypt/decrypt remote storage credentials? Use system keyring?
3. **Caching Strategy**: How long to cache remote file listings? Invalidation strategy?
4. **Background Jobs**: Use Celery/RQ for async tool execution, or FastAPI BackgroundTasks?
5. **Report Generation**: Generate HTML on-demand from stored results, or store pre-generated HTML?
6. **Version Compatibility**: How to handle results from different tool versions?
7. **Export Functionality**: Should users be able to export results to CSV, JSON, or other formats?
8. **Pipeline Versioning**: Should pipeline changes create new versions automatically, or require manual versioning?
9. **Multiple Active Pipelines**: Allow multiple active pipelines, or enforce single active pipeline?
10. **Pipeline Node Library**: Should we provide pre-built node templates for common workflows?

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
- React Flow (v2 - visual pipeline editor)

## Appendix

### Related Issues
- Issue #24: Support for remote Photo collections and longer term persistence

### References
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL JSONB Documentation](https://www.postgresql.org/docs/current/datatype-json.html)
- [boto3 S3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html)
- [React Documentation](https://react.dev/)
- [React Flow Documentation](https://reactflow.dev/) - Visual pipeline editor (v2 enhancement)

### Revision History
- **2025-12-29 (v2)**: Added Pipeline Validation tool integration, pipeline configuration management, React Flow future enhancement
- **2025-12-29 (v1)**: Initial draft based on Issue #24 requirements
