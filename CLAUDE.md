# ShutterSense.ai Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-21

## Project Overview

ShutterSense.ai - Capture. Process. Analyze. A comprehensive solution for analyzing, managing, and validating photo collections across local and remote storage.

### Agent CLI

Analysis tools are executed through the ShutterSense agent binary (`shuttersense-agent`):

- `shuttersense-agent test` - Test local path accessibility
- `shuttersense-agent collection create` - Register a collection on the server
- `shuttersense-agent run` - Run analysis tools (online or offline)
- `shuttersense-agent sync` - Upload offline results to the server
- `shuttersense-agent self-test` - Verify agent configuration

### Web Application

- **Backend** (FastAPI) - RESTful API with PostgreSQL storage, encrypted credentials, job queuing
- **Frontend** (React/TypeScript) - Modern, accessible UI with real-time progress updates

## Active Technologies
- Python 3.11+ (agent and backend), TypeScript 5.9.3 (frontend - minimal changes) + Click 8.1+ (agent CLI), FastAPI (backend API), httpx (agent HTTP client), Pydantic v2 (data validation), platformdirs (config paths) (108-remove-cli-direct-usage)
- PostgreSQL 12+ (server), JSON files (agent local cache), SQLAlchemy 2.0+ (ORM) (108-remove-cli-direct-usage)
- TypeScript 5.9.3, React 18.3.1 + shadcn/ui (Table, Tabs, Select, Badge), Tailwind CSS 4.x, Radix UI primitives, class-variance-authority, Lucide React icons (123-mobile-responsive-tables-tabs)
- N/A (frontend-only, no backend changes) (123-mobile-responsive-tables-tabs)
- Python 3.11+ (backend), TypeScript 5.9.3 (frontend) + FastAPI, SQLAlchemy 2.0+, Pydantic v2, Alembic (backend); React 18.3.1, shadcn/ui, Radix UI Popover, Tailwind CSS 4.x (frontend) (120-audit-trail-visibility)
- PostgreSQL 12+ (production), SQLite (tests) — Alembic migrations with dialect-aware code (120-audit-trail-visibility)

### Backend
- **Python 3.11+** - Required for ExceptionGroup, tomllib, and modern type hinting
- **FastAPI** - Web framework with OpenAPI docs
- **SQLAlchemy 2.0+** - ORM with async support
- **Pydantic v2** - Data validation and serialization
- **PostgreSQL 12+** - Primary database with JSONB columns (SQLite for tests)

### Agent
- **Python 3.11+** - Lightweight distributed agent binary
- **httpx** - Async HTTP client for REST API communication
- **websockets** - Real-time progress streaming
- **Pydantic v2** - Data validation and settings management
- **Click** - CLI framework
- **cryptography** - Local credential storage encryption
- **pyarrow** - Parquet format support for inventory import
- **PyInstaller** - Single-file binary distribution

### Frontend
- **TypeScript 5.9.3** - Type safety
- **React 18.3.1** - UI framework
- **Vite 6.0.5** - Build tooling
- **Tailwind CSS 4.x** - Utility-first styling
- **shadcn/ui** - Component library (Radix UI primitives)
- **Lucide React** - Icon library
- **Recharts** - Data visualization
- **class-variance-authority (cva)** - Component variants
- **Axios** - HTTP client

### Cloud Storage (Issue #107)
- **boto3** - AWS S3 and S3 Inventory
- **google-cloud-storage** - GCS and Storage Insights

### Security Features (Phase 7 & 10)
- **Authlib** - OAuth 2.0 authentication (Google, Microsoft)
- **PyJWT** - API token generation and validation
- **slowapi** - Rate limiting middleware
- **Fernet encryption** - Encrypted credential storage
- Security headers (CSP, X-Frame-Options, etc.)
- SQL injection prevention via SQLAlchemy ORM
- Credential access audit logging
- Multi-tenant data isolation (team_id scoping)
- Session-based auth (cookies) and API token auth (Bearer)

## Project Structure

```text
shuttersense/
├── agent/                         # ShutterSense Agent
│   ├── cli/                      # CLI commands (Click)
│   │   ├── main.py              # Entry point
│   │   ├── run.py               # Run analysis tools
│   │   ├── sync_results.py      # Sync offline results
│   │   └── ...
│   ├── src/
│   │   ├── analysis/            # Shared analysis modules
│   │   │   ├── photostats_analyzer.py
│   │   │   ├── photo_pairing_analyzer.py
│   │   │   └── pipeline_analyzer.py
│   │   ├── cache/               # Local caching (collections, results)
│   │   ├── api_client.py        # Server HTTP client
│   │   ├── chunked_upload.py    # Large payload upload
│   │   └── config.py            # Agent configuration
│   └── tests/                   # Agent test suites
├── backend/                       # FastAPI backend
├── frontend/                      # React frontend
├── utils/                         # Shared utilities
│   ├── config_manager.py         # PhotoAdminConfig class
│   └── filename_parser.py        # FilenameParser class
├── docs/                          # Documentation
├── specs/                         # Design specifications
└── requirements.txt               # Python dependencies
```

## Version Management

Photo-admin uses a centralized version management system that automatically synchronizes version numbers across all components with GitHub release tags.

### Version Module (`version.py`)

The `version.py` module provides a single source of truth for version information:

- **Tagged releases**: Returns clean tag (e.g., `v1.2.3`)
- **Development builds**: Returns tag with suffix (e.g., `v1.2.3-dev.5+a1b2c3d`)
- **No tags**: Returns development version (e.g., `v0.0.0-dev+a1b2c3d`)
- **No Git**: Falls back to `SHUSAI_VERSION` environment variable or `v0.0.0-dev+unknown`

### Version Display Locations

All components use the same version from `version.py`:

1. **Agent** (`--version` flag):
   - `shuttersense-agent --version`

2. **Backend API**:
   - FastAPI app version (shown in `/docs`)
   - `/api/version` endpoint
   - `/health` endpoint

3. **Frontend**:
   - Sidebar footer (fetched from `/api/version`)
   - Displayed dynamically via `useVersion()` hook

4. **HTML Reports**:
   - Report footer (e.g., "Generated by PhotoStats v1.2.3")

### Usage in Code

```python
# Python agent and backend
from version import __version__

print(f"Version: {__version__}")
```

```typescript
// TypeScript frontend
import { useVersion } from '@/hooks/useVersion'

const { version, loading, error } = useVersion()
```

### Development Version Format

During development (commits after a tag), the version includes:
- **Base version**: Latest Git tag
- **Commits since**: Number of commits since tag
- **Commit hash**: Short hash for traceability

Example: `v1.2.3-dev.5+a1b2c3d` means:
- Latest tag: `v1.2.3`
- 5 commits ahead of tag
- Current commit: `a1b2c3d`

### CI/CD Integration

For CI/CD environments without Git:
- Set `SHUSAI_VERSION` environment variable
- Example: `export SHUSAI_VERSION=v1.5.0-build.42`

### Creating Releases

To create a new release:
1. Tag the commit: `git tag v1.3.0`
2. Push tag: `git push origin v1.3.0`
3. All components automatically use `v1.3.0`

## Commands

### Running Agent Commands

```bash
# Test a local path
shuttersense-agent test /path/to/photos

# Register a collection
shuttersense-agent collection create /path/to/photos --name "My Photos"

# Run analysis (online - uploads results to server)
shuttersense-agent run col_GUID --tool photostats

# Run analysis (offline - stores locally for later sync)
shuttersense-agent run col_GUID --tool photostats --offline

# Sync offline results to server
shuttersense-agent sync

# Verify agent configuration
shuttersense-agent self-test
```

### Testing

```bash
# Run agent tests
python3 -m pytest agent/tests/ -v

# Run backend web tests
python3 -m pytest backend/tests/unit/ -v

# Run with coverage
python3 -m pytest agent/tests/ --cov=src --cov=cli --cov-report=term-missing
```

### Code Quality

```bash
# Run linter (if ruff is installed)
ruff check .

# Format code (if black is installed)
black .
```

## Code Style

- **Python 3.11+**: Follow PEP 8 conventions
- **Docstrings**: All functions should have clear docstrings with Args/Returns
- **Type hints**: Use where beneficial for clarity
- **Testing**: Write tests alongside implementation (flexible TDD)

## Frontend Architecture

### Design System (Required Reading)

All frontend development MUST follow the Design System documentation at `frontend/docs/design-system.md`. Key requirements:

- **Colors**: Use design tokens, never hardcoded colors
- **Buttons**: Primary=default, Cancel=outline, Delete=destructive, Icons=ghost
- **Status Colors**: success=positive, destructive=negative, muted=inactive, info=archived
- **Domain Labels**: Import from centralized `@/contracts/domain-labels.ts`
- **Error Handling**: Page errors at top, form errors above buttons, field errors via FormMessage
- **Icons**: Use consistent domain icons (Collection=FolderOpen, Connector=Plug, etc.)

See [Design System](frontend/docs/design-system.md) for complete guidelines.

### Single Title Pattern (Issue #67)

All pages MUST follow the Single Title Pattern:

1. **Page titles appear ONLY in TopHeader** - Never add `<h1>` elements in page content
2. **TopHeader is the single source of truth** for page titles, icons, and help text
3. **Page descriptions use `pageHelp` prop** - Not inline text in page content
4. **Tab content has NO titles** - The tab label is sufficient context

**Route Configuration** (`App.tsx`):
```typescript
{
  path: '/settings',
  element: <SettingsPage />,
  pageTitle: 'Settings',
  pageIcon: Settings,
  pageHelp: 'Configure tools, event categories, and storage connectors'  // Optional tooltip
}
```

**Action Button Patterns**:
- Non-tabbed pages: Right-aligned action row (`flex justify-end`)
- Tabbed pages with actions: Tabs + buttons on same row (responsive stacking)
- Tab content: Search + action on same row (responsive stacking)

**Responsive Pattern**:
```tsx
<div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
  {/* Stacks on mobile, horizontal on sm+ */}
</div>
```

### TopHeader KPI Pattern (Required for all pages)

All frontend pages MUST display relevant KPIs in the TopHeader stats area (next to the bell icon). This is a mandatory UX pattern established in Issue #37.

**Key Files**:
- `frontend/src/contexts/HeaderStatsContext.tsx` - Context for dynamic stats
- `frontend/src/components/layout/TopHeader.tsx` - Displays stats in header
- `frontend/src/components/layout/MainLayout.tsx` - Wraps pages in HeaderStatsProvider

**Implementation Pattern**:
```typescript
// 1. Create a stats hook in hooks/use<Domain>.ts
export const use<Domain>Stats = () => {
  const [stats, setStats] = useState<StatsResponse | null>(null)
  // Fetch from /api/<domain>/stats endpoint
  return { stats, loading, error, refetch }
}

// 2. In page component, set header stats
import { useHeaderStats } from '@/contexts/HeaderStatsContext'

const { stats } = use<Domain>Stats()
const { setStats } = useHeaderStats()

useEffect(() => {
  if (stats) {
    setStats([
      { label: 'Total Items', value: stats.total_count },
      { label: 'Active Items', value: stats.active_count },
    ])
  }
  return () => setStats([])  // Clear on unmount
}, [stats, setStats])
```

**Backend Requirements**:
- Each domain SHOULD have a `GET /api/<domain>/stats` endpoint
- Stats endpoints return aggregated KPIs independent of any filters
- Response schema: `<Domain>StatsResponse` in `backend/src/schemas/`

**Examples**:
- Collections: Total Collections, Storage Used, Total Files, Total Images
- Connectors: Active Connectors, Total Connectors

## Architecture Principles (Constitution)

### 0. Global Unique Identifiers (GUIDs) - Issue #42

All entities in the presentation layer (APIs, URLs, UI) are identified exclusively by GUIDs. Numeric IDs are internal-only.

**GUID Format:** `{prefix}_{26-char Crockford Base32}`

Example: `col_01hgw2bbg0000000000000001`

**Entity Prefixes (Implemented):**

| Entity | Prefix | Example |
|--------|--------|---------|
| Collection | `col_` | `col_01hgw2bbg...` |
| Connector | `con_` | `con_01hgw2bbg...` |
| Pipeline | `pip_` | `pip_01hgw2bbg...` |
| Result | `res_` | `res_01hgw2bbg...` |
| Job | `job_` | `job_01hgw2bbg...` |
| ImportSession | `imp_` | `imp_01hgw2bbg...` |
| Event | `evt_` | `evt_01hgw2bbg...` |
| EventSeries | `ser_` | `ser_01hgw2bbg...` |
| Category | `cat_` | `cat_01hgw2bbg...` |
| Location | `loc_` | `loc_01hgw2bbg...` |
| Organizer | `org_` | `org_01hgw2bbg...` |
| Performer | `prf_` | `prf_01hgw2bbg...` |
| Team | `tea_` | `tea_01hgw2bbg...` |
| User | `usr_` | `usr_01hgw2bbg...` |
| ApiToken | `tok_` | `tok_01hgw2bbg...` |
| Agent | `agt_` | `agt_01hgw2bbg...` |
| AgentRegistrationToken | `art_` | `art_01hgw2bbg...` |
| ReleaseManifest | `rel_` | `rel_01hgw2bbg...` |

**Key Files:**
- `backend/src/services/guid.py` - GuidService for generation/validation
- `backend/src/models/mixins/external_id.py` - ExternalIdMixin for DB entities
- `frontend/src/utils/guid.ts` - Frontend utilities

**Rules:**
- API responses use `.guid` property (never expose internal `.id`)
- Path parameters use `{guid}` for entity endpoints
- Foreign key references in responses use `_guid` suffix (e.g., `collection_guid`)
- All new entities MUST implement this pattern

See `docs/domain-model.md` for the complete prefix table including planned entities.

### 1. Agent-Only Tool Execution (Issue #108)
- All analysis tools are executed through authenticated ShutterSense agents
- Standalone CLI scripts have been removed from the repository
- Analysis logic resides in shared modules under `agent/src/analysis/`
- Tools are invoked via agent CLI commands: `test`, `run`, `sync`, `self-test`
- Offline mode supported for LOCAL collections with later sync

### 2. Testing & Quality
- Comprehensive test coverage (target >80% for core logic)
- pytest framework with fixtures in conftest.py
- Both unit tests and integration tests
- Tests can be written alongside implementation (flexible approach)

### 3. User-Centric Design
- Interactive HTML reports with visualizations
- Clear, actionable error messages
- Progress indicators for long operations
- Simple, focused implementations (YAGNI principle)

### 4. Shared Infrastructure
- **PhotoAdminConfig**: Shared configuration management
- **Utils**: Reusable utility classes (FilenameParser, etc.)
- Standard config schema with extensible design
- Consistent file naming conventions

### 5. Simplicity
- Direct implementations without over-engineering
- No premature abstractions
- Minimal dependencies (PyYAML, Jinja2 for templates)
- Straightforward data structures
- Industry-standard tools (Jinja2 for templating)

### 6. Multi-Tenancy and Authentication (Web Application) - Issue #73

All Web Application features MUST enforce authentication and tenant isolation. This applies to backend APIs and frontend UI only; CLI tools remain independent.

**Authentication Requirements:**
- All API endpoints MUST require authentication EXCEPT: `/health`, `/api/version`, `/api/auth/*`
- Authentication via session cookies (OAuth) or API tokens (Bearer header)
- API tokens CANNOT access super admin endpoints (`/api/admin/*`)
- Unauthenticated requests return 401 Unauthorized

**Tenant Isolation Requirements:**
- All data MUST be scoped to user's team (`team_id`)
- Services MUST accept `TenantContext` and filter by `team_id`
- Cross-team access returns 404 (not 403) to prevent information leakage
- New entities auto-assigned to user's team

**Backend Pattern:**
```python
from backend.src.middleware.tenant import TenantContext, get_tenant_context

@router.get("/items")
async def list_items(ctx: TenantContext = Depends(get_tenant_context)):
    return service.list_items(team_id=ctx.team_id)
```

**Frontend Pattern:**
```typescript
// Wrap routes with ProtectedRoute
<ProtectedRoute><ItemsPage /></ProtectedRoute>

// Access user via useAuth hook
const { user, isAuthenticated } = useAuth()
```

**Key Files:**
- `backend/src/middleware/tenant.py` - TenantContext, get_tenant_context
- `frontend/src/contexts/AuthContext.tsx` - Authentication context
- `frontend/src/components/auth/ProtectedRoute.tsx` - Route protection

**Entity Prefixes:**
| Entity | Prefix |
|--------|--------|
| Team | `tea_` |
| User | `usr_` |
| ApiToken | `tok_` |

### 7. Agent-Only Execution (Distributed Processing) - Issue #90

All asynchronous job processing MUST be executed by agents. The server acts as a coordinator only and MUST NOT execute any jobs directly.

**Architecture:**
- Server creates jobs, assigns them to agents, and stores results
- Agents (lightweight binaries) claim and execute jobs on user machines
- Jobs without available agents remain queued indefinitely
- Collections can be bound to specific agents (local filesystem MUST be bound)

**Job Processing Flow:**
1. User creates job via web UI
2. Server queues job for execution
3. Agent polls `/api/jobs/claim` and claims job
4. Agent executes tool locally against collection
5. Agent reports results via `/api/jobs/{guid}/complete`
6. Server stores results and updates job status

**UI Requirements:**
- Application MUST indicate when no agents are available
- Job creation MUST warn users if no agents can process their request
- Agent status visible in application header (Agent Pool Status indicator)

**Key Files:**
- `backend/src/services/agent_service.py` - Agent registration and management
- `backend/src/services/job_service.py` - Job creation and assignment
- `backend/src/api/agent/` - Agent-facing API endpoints
- `agent/` - Agent binary source code

**Entity Prefixes:**
| Entity | Prefix |
|--------|--------|
| Agent | `agt_` |
| AgentRegistrationToken | `art_` |
| ReleaseManifest | `rel_` |

### 8. Audit Trail & User Attribution - Issue #120

All tenant-scoped entities MUST record who created and last modified each record. Audit trail is a cross-cutting requirement for all features.

**Database Requirements:**
- All tenant-scoped entities MUST include `created_by_user_id` and `updated_by_user_id` columns
- New entities MUST use `AuditMixin` from `backend/src/models/mixins/audit.py`
- `created_by_user_id` is immutable after creation (enforced by service layer + PostgreSQL trigger)
- FK ON DELETE SET NULL preserves audit trail when users are deleted

**Backend Requirements:**
- All response schemas MUST include `audit: Optional[AuditInfo] = None`
- Service create methods MUST set both `created_by_user_id` and `updated_by_user_id` from `TenantContext.user_id`
- Service update methods MUST set `updated_by_user_id` from `TenantContext.user_id`

**Backend Pattern:**
```python
from backend.src.models.mixins.audit import AuditMixin

class MyEntity(Base, GuidMixin, AuditMixin):
    __tablename__ = "my_entities"
    # AuditMixin adds: created_by_user_id, updated_by_user_id, .audit property
```

**Frontend Requirements:**
- All entity API contracts MUST include `audit?: AuditInfo`
- List views MUST display a "Modified" column using `AuditTrailPopover`
- Detail views MUST display an `AuditSection` component
- Missing audit data renders an em dash (\u2014) fallback

**Frontend Pattern:**
```typescript
import { AuditTrailPopover } from '@/components/audit'
import type { AuditInfo } from '@/contracts/api/audit-api'

// List view column:
{ header: 'Modified', cell: (row) => <AuditTrailPopover audit={row.audit} /> }
```

**Key Files:**
- `backend/src/models/mixins/audit.py` - AuditMixin for models
- `backend/src/schemas/audit.py` - AuditInfo, AuditUserSummary schemas
- `frontend/src/contracts/api/audit-api.ts` - TypeScript audit types
- `frontend/src/components/audit/AuditTrailPopover.tsx` - List view popover
- `frontend/src/components/audit/AuditSection.tsx` - Detail view section

## Configuration

### Config File Locations (Priority Order)

1. `./config/config.yaml` (current directory)
2. `./config.yaml` (current directory)
3. `~/.photo_stats_config.yaml` (home directory)
4. `<script-dir>/config/config.yaml` (installation directory)

### Config Schema

```yaml
photo_extensions:
  - .dng
  - .cr3
  - .tiff

metadata_extensions:
  - .xmp

require_sidecar:
  - .cr3

camera_mappings:
  AB3D:
    - name: Canon EOS R5
      serial_number: "12345"

processing_methods:
  HDR: High Dynamic Range
  BW: Black and White
```

## Shared Utilities

### PhotoAdminConfig (utils/config_manager.py)

Manages configuration loading and interactive prompts:

```python
from utils.config_manager import PhotoAdminConfig

config = PhotoAdminConfig()
# Or with explicit path:
config = PhotoAdminConfig(config_path='/path/to/config.yaml')

# Access configuration
photo_exts = config.photo_extensions
camera_map = config.camera_mappings

# Interactive prompts (auto-saves to config)
camera_info = config.ensure_camera_mapping('AB3D')
method_desc = config.ensure_processing_method('HDR')
```

### FilenameParser (utils/filename_parser.py)

Validates and parses photo filenames:

```python
from utils.filename_parser import FilenameParser

# Validate filename
is_valid, error = FilenameParser.validate_filename('AB3D0001-HDR.dng')

# Parse filename
parsed = FilenameParser.parse_filename('AB3D0001-HDR.dng')
# Returns: {'camera_id': 'AB3D', 'counter': '0001',
#           'properties': ['HDR'], 'extension': '.dng'}

# Detect property type
prop_type = FilenameParser.detect_property_type('2')  # 'separate_image'
prop_type = FilenameParser.detect_property_type('HDR')  # 'processing_method'
```

## Recent Changes
- 120-audit-trail-visibility: Added Python 3.11+ (backend), TypeScript 5.9.3 (frontend) + FastAPI, SQLAlchemy 2.0+, Pydantic v2, Alembic (backend); React 18.3.1, shadcn/ui, Radix UI Popover, Tailwind CSS 4.x (frontend)
- 123-mobile-responsive-tables-tabs: Added TypeScript 5.9.3, React 18.3.1 + shadcn/ui (Table, Tabs, Select, Badge), Tailwind CSS 4.x, Radix UI primitives, class-variance-authority, Lucide React icons
- 108-remove-cli-direct-usage: Remove standalone CLI tools (photo_stats.py, photo_pairing.py, pipeline_validation.py) and consolidate all tool execution through agent commands (test, collection, run, sync, self-test). Added local caching, offline execution, and new agent API endpoints for collection management and result upload

### Issue #107: Cloud Storage Bucket Inventory Import (2026-01)

### Issue #106: Fix Trend Aggregation (2026-01)

### Issue #22: Storage Optimization (2026-01)

### Phase 7 Production-Ready Application (2026-01-09)

### HTML Report Consistency & Tool Improvements (2025-12-25)
  - Created templates/base.html.j2 with shared styling and Chart.js theme
  - Tool-specific templates extend base for PhotoStats and Photo Pairing
  - Removed 640+ lines of duplicate HTML generation code
  - Migrated PhotoStats from manual argv parsing to argparse
  - Enhanced Photo Pairing help with examples and workflow
  - Both tools support --help and -h flags
  - User-friendly "Operation interrupted by user" message
  - Exit code 130 (standard for SIGINT)
  - Atomic file writes prevent partial reports
  - Shutdown checks in scan loops and before report generation
  - PhotoStats: photo_stats_report_YYYY-MM-DD_HH-MM-SS.html
  - Photo Pairing: photo_pairing_report_YYYY-MM-DD_HH-MM-SS.html
  - Report renderer tests (12): template rendering, visual consistency
  - Help text tests (6): --help/-h flag validation
  - Signal handling tests (7): CTRL+C graceful interruption

### Photo Pairing Tool (2025-12-25)

### Code Refactoring (2025-12-24)

## Testing Guidelines

### Test Organization

- **Fixtures**: Define reusable test data in fixtures
- **Test Classes**: Group related tests by functionality
- **Integration Tests**: Test complete workflows end-to-end
- **Mocking**: Use monkeypatch for user input, file I/O, etc.

### Coverage Targets

- Core business logic: >80%
- Utility functions: >85%
- Overall: >65% (accounts for CLI code)

### Example Test Structure

```python
import pytest
from utils.filename_parser import FilenameParser

class TestFilenameValidation:
    """Tests for filename validation"""

    def test_valid_filename(self):
        is_valid, error = FilenameParser.validate_filename('AB3D0001.dng')
        assert is_valid
        assert error is None

    def test_invalid_counter(self):
        is_valid, error = FilenameParser.validate_filename('AB3D0000.dng')
        assert not is_valid
        assert 'Counter cannot be 0000' in error
```

## Documentation Standards

### Code Documentation

- Module-level docstrings explaining purpose
- Function docstrings with Args, Returns, and Raises
- Inline comments for complex logic only

### User Documentation

- Installation guide (docs/installation.md)
- Configuration guide (docs/configuration.md)
- Tool-specific guides (docs/photostats.md, docs/photo-pairing.md)
- README.md with quick start and overview

### Tool Help Output

- Include usage examples in `--help`
- Show expected workflow
- Provide sample commands

## License

GNU Affero General Public License v3.0 (AGPL-3.0)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
