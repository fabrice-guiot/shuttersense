# Implementation Plan: Remove CLI Direct Usage

**Branch**: `108-remove-cli-direct-usage` | **Date**: 2026-01-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/108-remove-cli-direct-usage/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Consolidate all tool execution through the Agent interface by adding new CLI commands (test, collection management, run, sync, self-test), extending the backend API for agent-initiated collection creation and offline result upload, then removing standalone CLI tools (photo_stats.py, photo_pairing.py, pipeline_validation.py) and updating the project constitution to enforce agent-only execution. The agent already has shared analysis modules in `agent/src/analysis/` and a Click-based CLI framework, so new commands extend the existing architecture.

## Technical Context

**Language/Version**: Python 3.10+ (agent and backend), TypeScript 5.9.3 (frontend - minimal changes)
**Primary Dependencies**: Click 8.1+ (agent CLI), FastAPI (backend API), httpx (agent HTTP client), Pydantic v2 (data validation), platformdirs (config paths)
**Storage**: PostgreSQL 12+ (server), JSON files (agent local cache), SQLAlchemy 2.0+ (ORM)
**Testing**: pytest with async support, fixtures in conftest.py
**Target Platform**: Linux/macOS/Windows (agent binary), Linux server (backend)
**Project Type**: Web application with distributed agent
**Performance Goals**: Test command < 30s for 10K files, Collection creation < 5s, sync handles files up to 100MB
**Constraints**: Offline-capable for LOCAL collections, agent authentication required for all server operations
**Scale/Scope**: ~15 new agent CLI source files, ~4 new backend endpoint files, ~3 CLI tools to delete, ~7 docs to update

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] **Independent CLI Tools → Agent-Only Tool Execution**: This feature explicitly transitions from Principle I (Independent CLI Tools) to agent-only execution. US5 replaces the constitution principle. This is a planned, justified transition - not a violation.
- [x] **Testing & Quality**: Tests planned for all new agent commands (unit + integration), all new backend endpoints (unit + integration). pytest framework used throughout.
- [x] **User-Centric Design**:
  - HTML report generation supported via `--output` flag on test and run commands
  - Clear, actionable error messages defined for all failure modes (see PRD Appendix C)
  - YAGNI: Commands use existing analysis modules, no new abstractions
  - Structured logging via Python `logging` module (agent pattern established)
- [x] **Shared Infrastructure**: Agent uses `PhotoAdminConfig` via `ApiConfigLoader`. Config schema respected. Standard file locations via `platformdirs`.
- [x] **Simplicity**: New commands are thin wrappers around existing analysis modules and API client. No new frameworks or abstractions. Cache uses simple JSON files.
- [x] **Global Unique Identifiers**: All entities use GUID format (`col_`, `job_`, `agt_`). Run command takes collection GUID, not path. Offline results reference `collection_guid`.
- [x] **Multi-Tenancy & Authentication**: Agent authenticates via API key. Server endpoints use `TenantContext` / agent context. Collections inherit agent's `team_id`. Cross-team = 404.
- [x] **Agent-Only Execution**: This feature enforces this principle by removing the alternative (CLI tools).
- [x] **Frontend UI Standards**: No new frontend pages. Existing Collection/Job pages display agent-created results automatically.

**Violations/Exceptions**: None. The transition from Principle I to agent-only execution is the explicit purpose of this feature and is documented in the constitution sync impact report (v1.6.0).

## Project Structure

### Documentation (this feature)

```text
specs/108-remove-cli-direct-usage/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
agent/
├── cli/
│   ├── main.py                    # UPDATE: Register new commands
│   ├── test.py                    # NEW: Test command (US1)
│   ├── collection.py              # NEW: Collection subcommands (US2, US4)
│   ├── run.py                     # NEW: Run tool command (US3)
│   ├── sync_results.py            # NEW: Sync offline results (US3)
│   └── self_test.py               # NEW: Self-test command (US6)
├── src/
│   ├── cache/
│   │   ├── __init__.py            # NEW
│   │   ├── test_cache.py          # NEW: Test result caching (24h)
│   │   ├── collection_cache.py    # NEW: Collection cache (7d)
│   │   └── result_store.py        # NEW: Offline result storage
│   ├── analysis/                  # EXISTING: Shared analysis modules (no changes)
│   │   ├── photostats_analyzer.py
│   │   ├── photo_pairing_analyzer.py
│   │   ├── pipeline_analyzer.py
│   │   └── inventory_parser.py
│   ├── remote/                    # EXISTING: Storage adapters (no changes)
│   ├── job_executor.py            # EXISTING: Reuse patterns for local execution
│   ├── api_client.py              # UPDATE: Add collection/result upload methods
│   └── config.py                  # UPDATE: Add cache directory paths
└── tests/
    ├── unit/
    │   ├── test_test_command.py       # NEW
    │   ├── test_collection_command.py # NEW
    │   ├── test_run_command.py        # NEW
    │   ├── test_sync_command.py       # NEW
    │   ├── test_self_test.py          # NEW
    │   ├── test_test_cache.py         # NEW
    │   ├── test_collection_cache.py   # NEW
    │   └── test_result_store.py       # NEW
    └── integration/
        ├── test_test_create_flow.py   # NEW
        └── test_offline_sync_flow.py  # NEW

backend/
├── src/
│   ├── api/
│   │   └── agent/
│   │       ├── routes.py          # UPDATE: Add collection + result endpoints
│   │       └── schemas.py         # UPDATE: Add new request/response schemas
│   ├── services/
│   │   ├── collection_service.py  # UPDATE: Add agent-initiated creation method
│   │   └── tool_service.py        # UPDATE: Add offline result ingestion
│   └── models/                    # EXISTING: No model changes needed
└── tests/
    └── test_agent_collection_api.py   # NEW

# FILES TO DELETE (US5):
photo_stats.py                     # DELETE
photo_pairing.py                   # DELETE
pipeline_validation.py             # DELETE
tests/test_photo_stats.py          # DELETE (CLI-specific tests only)
tests/test_photo_pairing.py        # DELETE (CLI-specific tests only)

# FILES TO UPDATE (US5):
.specify/memory/constitution.md    # UPDATE: Replace Principle I
CLAUDE.md                          # UPDATE: Remove CLI references
README.md                          # UPDATE: Agent-only workflow
docs/installation.md               # UPDATE: Agent-only installation
docs/configuration.md              # UPDATE: Remove CLI config sections
docs/photostats.md                 # UPDATE: Archive notice + agent redirect
docs/photo-pairing.md              # UPDATE: Archive notice + agent redirect
```

**Structure Decision**: Web application structure with distributed agent. New agent CLI commands (`cli/`) delegate to cache modules (`src/cache/`) and existing analysis modules (`src/analysis/`). New backend endpoints extend the existing `api/agent/` module. No new projects or directories at the top level.

## Complexity Tracking

> **No violations. Constitution check passes for all principles.**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
