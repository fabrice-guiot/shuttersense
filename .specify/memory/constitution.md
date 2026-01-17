<!--
SYNC IMPACT REPORT (Constitution v1.5.0 - Multi-Tenancy and Authentication)

Version change: 1.4.0 → 1.5.0 (MINOR)
Modified sections:
  - Added new Core Principle: V. Multi-Tenancy and Authentication (Web Application)

Added requirements:
  - All API endpoints MUST require authentication except public endpoints (/health, /api/version, /api/auth/*)
  - All data MUST be scoped to authenticated user's team (tenant isolation)
  - Services MUST accept TenantContext and filter by team_id
  - Cross-team data access MUST return 404 (not 403) to prevent information leakage
  - New entities MUST be auto-assigned to user's team
  - Database entities with tenant scope MUST have team_id FK
  - API tokens MUST NOT access /api/admin/* endpoints
  - Frontend routes MUST be wrapped with ProtectedRoute (except /login)

Rationale:
  - Issue #73 / Feature 019-user-tenancy established multi-tenancy architecture
  - Ensures complete data isolation between organizations
  - Consistent TenantContext pattern prevents accidental data leakage
  - 404 response for cross-team access prevents GUID enumeration attacks

Impact:
  - All new backend endpoints MUST use get_tenant_context dependency
  - All new services MUST filter by team_id
  - All new frontend routes MUST be protected
  - Code reviews MUST verify tenant isolation compliance

Templates requiring updates:
  ✅ No template changes needed - this is an architecture standard

Previous Amendment (v1.4.0 - Single Title Pattern):
  - Added new Frontend UI Standard: Single Title Pattern (Issue #67)

SYNC IMPACT REPORT (Constitution v1.4.0 - Single Title Pattern)

Version change: 1.3.0 → 1.4.0 (MINOR)
Modified sections:
  - Added new Frontend UI Standard: Single Title Pattern (Issue #67)

Added requirements:
  - Pages MUST NOT include h1 elements in content area
  - TopHeader is the single source of truth for page titles
  - Page descriptions MUST use pageHelp tooltip, not inline text
  - Tab content MUST NOT include h2 titles
  - Action button positioning follows three patterns (non-tabbed, tabbed with actions, tab content)
  - All action rows MUST use responsive stacking pattern

Rationale:
  - Issue #67 established Single Title Pattern to eliminate visual redundancy
  - Improves information hierarchy and creates usable screen real estate
  - pageHelp tooltip provides on-demand context without consuming permanent space
  - Consistent action button positioning enables muscle memory

Impact:
  - All new pages MUST NOT add h1 elements in content area
  - Code reviews MUST verify Single Title Pattern compliance
  - Action rows MUST use flex-col/sm:flex-row responsive pattern

Templates requiring updates:
  ✅ No template changes needed - this is a UI/UX standard

Previous Amendment (v1.3.0 - Global Unique Identifiers):
  - Added new Core Principle: IV. Global Unique Identifiers (GUIDs)

SYNC IMPACT REPORT (Constitution v1.3.0 - Global Unique Identifiers)

Version change: 1.2.0 → 1.3.0 (MINOR)
Modified principles:
  - Added new Core Principle: IV. Global Unique Identifiers (GUIDs)

Added requirements:
  - All entities MUST use GUIDs as their primary external identifier
  - GUIDs MUST use format: {prefix}_{26-char Crockford Base32 UUIDv7}
  - API responses MUST use .guid property, never expose internal numeric IDs
  - Path parameters MUST use {guid} for entity endpoints
  - Foreign key references MUST use _guid suffix (e.g., collection_guid)
  - New database entities MUST implement GuidMixin

Rationale:
  - Issue #42 established GUID pattern for all entities
  - GUIDs provide URL-safe, globally unique identifiers
  - Entity prefixes enable type identification from ID alone
  - UUIDv7 provides time-ordering for database efficiency
  - Separating internal IDs from external GUIDs improves security

Impact:
  - All new database entities MUST add GuidMixin
  - All new API endpoints MUST use GUIDs in paths and responses
  - Code reviews MUST verify GUID implementation follows this pattern
  - Frontend components MUST use .guid for entity references

Templates requiring updates:
  ✅ No template changes needed - this is a coding standard

Previous Amendment (v1.2.0 - Frontend UI Standards):
  - Added new section: Frontend UI Standards
  - TopHeader KPI display pattern requirements

Previous Amendment (v1.1.1 - Cross-Platform Encoding Standard):
  - Shared Infrastructure Standards: Added Cross-Platform File Encoding requirement

Previous Amendment (v1.1.0 - CLI Standards):
  - User-Centric Design: Added requirements for --help option and CTRL+C handling
  - Shared Infrastructure Standards: Added HTML Report Consistency requirement
-->

# photo-admin Constitution

## Core Principles

### I. Independent CLI Tools

Every tool in the photo-admin toolbox MUST be an independent Python script that can run standalone. Tools MUST use the shared `PhotoAdminConfig` class from `config_manager.py` for configuration management. Tools MAY share modules, utilities, and libraries but MUST NOT require other tools to function.

**Rationale**: This architecture enables users to adopt individual tools without installing the entire toolbox, simplifies testing, and allows tools to evolve independently while maintaining consistency through shared infrastructure.

### II. Testing & Quality

All features MUST have test coverage. Tests SHOULD be written before or alongside implementation. The project uses pytest for testing. New tools MUST achieve reasonable test coverage before being considered complete. Tests MUST be independently runnable and well-organized.

**Rationale**: Quality through testing ensures reliability and maintainability. A flexible approach (rather than strict TDD) allows developers to choose the testing workflow that best fits each feature while maintaining the quality bar.

### III. User-Centric Design

Analysis tools MUST generate interactive HTML reports with visualizations and clear presentation of results. All tools MUST provide helpful, actionable error messages. Code MUST prioritize simplicity over cleverness (YAGNI principle). Tools MUST include structured logging for observability and debugging.

All tools MUST provide `--help` and `-h` options that display comprehensive usage information without performing operations. All tools MUST handle CTRL+C (SIGINT) gracefully with user-friendly messages and appropriate exit codes (130).

**Rationale**: Users deserve clear, visual insights into their photo collections. Simplicity reduces maintenance burden and makes the codebase accessible to contributors. Good observability enables users to understand what's happening and troubleshoot issues effectively. Standard CLI conventions (help flags, interruption handling) create professional user experiences and meet established user expectations.

### IV. Global Unique Identifiers (GUIDs)

All entities in presentation layers (APIs, URLs, UI) MUST be identified exclusively by Global Unique Identifiers (GUIDs). Internal numeric IDs are for database operations only and MUST NOT be exposed externally.

**GUID Format**: `{prefix}_{26-char Crockford Base32}`

Example: `col_01hgw2bbg0000000000000001`

**Entity Prefixes** (Implemented):

| Entity | Prefix | Storage | Example |
|--------|--------|---------|---------|
| Collection | `col_` | Database | `col_01hgw2bbg...` |
| Connector | `con_` | Database | `con_01hgw2bbg...` |
| Pipeline | `pip_` | Database | `pip_01hgw2bbg...` |
| Result | `res_` | Database | `res_01hgw2bbg...` |
| Job | `job_` | In-memory | `job_01hgw2bbg...` |
| ImportSession | `imp_` | In-memory | `imp_01hgw2bbg...` |
| Event | `evt_` | Database | `evt_01hgw2bbg...` |
| EventSeries | `ser_` | Database | `ser_01hgw2bbg...` |
| Category | `cat_` | Database | `cat_01hgw2bbg...` |
| Location | `loc_` | Database | `loc_01hgw2bbg...` |
| Organizer | `org_` | Database | `org_01hgw2bbg...` |
| Performer | `prf_` | Database | `prf_01hgw2bbg...` |

**Implementation Requirements**:
- Database entities MUST use `GuidMixin` from `backend/src/models/mixins/guid.py`
- In-memory entities MUST use `GuidService.generate_guid(prefix)` from `backend/src/services/guid.py`
- API responses MUST use `.guid` property (never expose `.id`)
- Path parameters MUST use `{guid}` for entity endpoints
- Foreign key references in responses MUST use `_guid` suffix (e.g., `collection_guid`, `pipeline_guid`)
- Frontend utilities in `frontend/src/utils/guid.ts` for validation and prefix extraction

**Rationale**: GUIDs provide URL-safe, globally unique identifiers that can be safely shared, bookmarked, and used in external integrations. Entity prefixes enable immediate type identification from the ID alone. UUIDv7 provides time-ordering for database efficiency. Separating internal numeric IDs from external GUIDs improves security by not exposing database structure.

### V. Multi-Tenancy and Authentication (Web Application)

All Web Application features (backend APIs and frontend UI) MUST enforce authentication and tenant isolation. This principle applies to the web application only; CLI tools remain independent and do not require authentication.

**Authentication Requirements**:
- All API endpoints MUST require authentication EXCEPT explicit public endpoints (`/health`, `/api/version`, `/api/auth/*`)
- Authentication is provided via either:
  - **Session cookies**: For browser-based access (OAuth login flow)
  - **API tokens**: For programmatic access (Bearer token in Authorization header)
- API tokens MUST NOT grant access to super admin endpoints (`/api/admin/*`)
- Unauthenticated requests to protected endpoints MUST return 401 Unauthorized

**Tenant Isolation Requirements**:
- All data MUST be scoped to the authenticated user's team (`team_id`)
- Services MUST accept `TenantContext` and filter all queries by `team_id`
- Cross-team data access MUST return 404 Not Found (never 403 Forbidden, to avoid information leakage)
- New entities MUST be automatically assigned to the user's team on creation
- Database entities with tenant scope MUST have a `team_id` foreign key column

**Backend Implementation Pattern**:
```python
from backend.src.middleware.tenant import TenantContext, get_tenant_context

@router.get("/items")
async def list_items(
    ctx: TenantContext = Depends(get_tenant_context)
):
    # Service filters by team_id automatically
    return service.list_items(team_id=ctx.team_id)

@router.get("/items/{guid}")
async def get_item(
    guid: str,
    ctx: TenantContext = Depends(get_tenant_context)
):
    # Returns None (404) if item belongs to different team
    item = service.get_by_guid(guid, team_id=ctx.team_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item
```

**Frontend Implementation Pattern**:
```typescript
// All routes except /login MUST be wrapped with ProtectedRoute
<Route path="/items" element={
  <ProtectedRoute>
    <ItemsPage />
  </ProtectedRoute>
} />

// Components access user context via useAuth hook
const { user, isAuthenticated, logout } = useAuth()
```

**Key Files**:
- `backend/src/middleware/tenant.py` - TenantContext and get_tenant_context dependency
- `backend/src/middleware/auth.py` - Authentication middleware
- `frontend/src/contexts/AuthContext.tsx` - Frontend authentication context
- `frontend/src/components/auth/ProtectedRoute.tsx` - Route protection wrapper

**Entity Prefixes for Auth Entities**:

| Entity | Prefix | Description |
|--------|--------|-------------|
| Team | `tea_` | Tenant/organization |
| User | `usr_` | Human or system user |
| ApiToken | `tok_` | API token for programmatic access |

**Rationale**: Multi-tenancy enables the application to serve multiple organizations while ensuring complete data isolation. Authentication prevents unauthorized access. The consistent pattern of TenantContext injection ensures tenant isolation cannot be accidentally bypassed. Returning 404 for cross-team access prevents attackers from discovering which GUIDs exist in other tenants.

## Shared Infrastructure Standards

- **Configuration Management**: All tools MUST use `PhotoAdminConfig` from `config_manager.py` for loading and managing YAML configuration
- **Config File Location**: Standard locations are `./config/config.yaml` or `~/.photo-admin/config.yaml`
- **Interactive Setup**: Tools MUST prompt users to create configuration from template on first run if config is missing
- **Config Schema**: New tools MAY extend the shared config schema by adding top-level keys; existing keys MUST NOT be redefined
- **File Type Support**: Tools MUST respect `photo_extensions` and `metadata_extensions` from shared config
- **Report Output**: HTML reports MUST be timestamped (format: `tool_name_report_YYYY-MM-DD_HH-MM-SS.html`)
- **HTML Report Consistency**: All tools MUST use a centralized HTML templating approach with consistent styling for common elements (headers, footers, metadata sections, KPI cards, charts, warnings, errors). Tools MAY have tool-specific content sections but MUST maintain consistent visual design and user experience
- **Cross-Platform File Encoding**: All file read and write operations MUST explicitly specify `encoding='utf-8'` for text files. This includes `open()`, `Path.read_text()`, `Path.write_text()`, and similar operations. Never rely on platform default encodings (Windows defaults to cp1252, which causes failures on UTF-8 content)

## Frontend UI Standards

### TopHeader KPI Display Pattern

All frontend pages MUST display relevant Key Performance Indicators (KPIs) in the TopHeader stats area (next to the notification bell icon). This provides users with at-a-glance metrics for the current domain without consuming page content real estate.

**Implementation Requirements**:
- Pages MUST use `useHeaderStats()` hook from `HeaderStatsContext` to set their KPIs
- KPIs MUST be fetched from dedicated backend `/stats` API endpoints (e.g., `/api/collections/stats`)
- Stats MUST be cleared on page unmount (via useEffect cleanup) to prevent stale data when navigating
- Backend stats endpoints MUST return aggregated data independent of any filter parameters

**Standard Pattern**:
```typescript
// In page component
const { stats } = useCollectionStats()  // Fetch from API
const { setStats } = useHeaderStats()   // Context hook

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

**Rationale**: Consistent KPI placement in the topbar creates a predictable user experience across all pages. Users always know where to find key metrics. This pattern avoids duplicating KPIs in both the topbar and page content, which wastes space and creates confusion.

### Single Title Pattern (Issue #67)

All frontend pages MUST follow the Single Title Pattern: the page title appears ONLY in the TopHeader component. Pages MUST NOT include `<h1>` elements in their content area.

**Core Requirements**:
- TopHeader is the single source of truth for page titles
- Pages MUST NOT render `<h1>` elements in the content area
- Page descriptions MUST use the `pageHelp` tooltip mechanism, not inline text
- Tab content MUST NOT include `<h2>` titles - the tab label provides sufficient context

**Route Configuration Pattern**:
```typescript
// In App.tsx
const routes: RouteConfig[] = [
  {
    path: '/settings',
    element: <SettingsPage />,
    pageTitle: 'Settings',
    pageIcon: Settings,
    pageHelp: 'Configure tools, event categories, and storage connectors'  // Optional
  },
]
```

**Action Button Positioning**:
- Non-tabbed pages: Right-aligned action row (`flex justify-end`)
- Tabbed pages with actions: Tabs + buttons on same row with responsive stacking
- Tab content with search: Search + action on same row with responsive stacking

**Mobile Responsiveness**:
All action rows MUST stack vertically on mobile using the responsive pattern:
```tsx
<div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
  {/* Stacks vertically on mobile, horizontal on sm+ breakpoint */}
</div>
```

**Rationale**: A single title location eliminates visual redundancy, improves information hierarchy, and creates more usable screen real estate. The `pageHelp` tooltip provides on-demand context without consuming permanent screen space. Consistent action button positioning enables muscle memory for users navigating between pages.

## Development Philosophy

- **Simplicity First**: Start with the simplest implementation that solves the problem. Avoid premature abstraction or optimization.
- **YAGNI**: Implement only what is needed now. Future requirements will be addressed when they become actual requirements.
- **Clear Over Clever**: Code readability and maintainability trump cleverness. Prefer explicit over implicit.
- **No Over-Engineering**: Resist the urge to build frameworks, abstractions, or utilities until they are clearly needed by multiple features.
- **Incremental Improvement**: Small, focused changes are preferred over large rewrites. Refactor when there's clear benefit.

## Governance

**Constitution Authority**: This constitution defines the core principles and standards for the photo-admin project. All design decisions, code reviews, and feature implementations MUST comply with these principles.

**Amendment Process**:
- Amendments require documentation of rationale and impact analysis
- Version must be incremented according to semantic versioning (see below)
- Significant changes should be discussed before adoption
- Updates to constitution MUST trigger review of dependent templates

**Versioning Policy**:
- **MAJOR**: Backward-incompatible changes to principles, removal of core standards, or fundamental governance changes
- **MINOR**: New principles added, material expansions to existing guidance, or new governance sections
- **PATCH**: Clarifications, wording improvements, typo fixes, or non-semantic refinements

**Compliance**: All pull requests MUST verify compliance with this constitution. Any violations MUST be explicitly justified in the implementation plan's "Complexity Tracking" section. The Constitution Check in `plan-template.md` enforces this gate.

**Review Cycle**: Constitution should be reviewed when:
- A new major tool is added to the toolbox
- Repeated exceptions to a principle suggest it needs revision
- Project direction or scope changes significantly

**Version**: 1.5.0 | **Ratified**: 2025-12-23 | **Last Amended**: 2026-01-16
