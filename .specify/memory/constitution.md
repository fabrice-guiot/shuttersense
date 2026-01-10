<!--
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

**Implementation Requirements**:
- Database entities MUST use `GuidMixin` from `backend/src/models/mixins/guid.py`
- In-memory entities MUST use `GuidService.generate_guid(prefix)` from `backend/src/services/guid.py`
- API responses MUST use `.guid` property (never expose `.id`)
- Path parameters MUST use `{guid}` for entity endpoints
- Foreign key references in responses MUST use `_guid` suffix (e.g., `collection_guid`, `pipeline_guid`)
- Frontend utilities in `frontend/src/utils/guid.ts` for validation and prefix extraction

**Rationale**: GUIDs provide URL-safe, globally unique identifiers that can be safely shared, bookmarked, and used in external integrations. Entity prefixes enable immediate type identification from the ID alone. UUIDv7 provides time-ordering for database efficiency. Separating internal numeric IDs from external GUIDs improves security by not exposing database structure.

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

**Version**: 1.3.0 | **Ratified**: 2025-12-23 | **Last Amended**: 2026-01-10
