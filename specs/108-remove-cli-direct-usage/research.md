# Research: Remove CLI Direct Usage

**Feature Branch**: `108-remove-cli-direct-usage`
**Created**: 2026-01-28
**Status**: Complete

## Research Summary

No NEEDS CLARIFICATION items were identified in the Technical Context. The PRD (docs/prd/000-remove-cli-direct-usage.md) is comprehensive and the codebase exploration resolved all technical questions. This document records the design decisions made during research.

---

## Decision 1: Agent CLI Command Structure

**Decision**: Use Click command groups with subcommands matching the PRD structure.

**Rationale**: The agent already uses Click 8.1+ with a `@click.group()` entry point in `agent/cli/main.py`. New commands follow the established pattern: one file per command/group in `agent/cli/`, registered via `cli.add_command()`. The `collection` command uses a nested `@click.group()` for subcommands (`create`, `list`, `sync`, `test`).

**Alternatives Considered**:
- **Typer**: More modern, auto-generates help from type hints. Rejected because the agent already uses Click and mixing frameworks adds complexity.
- **argparse**: Used by CLI tools being removed. Rejected because Click is already the agent standard.

---

## Decision 2: Local Cache Storage Format

**Decision**: Use JSON files in `~/.shuttersense-agent/` via `platformdirs`.

**Rationale**: The agent already uses `platformdirs.user_config_dir()` for configuration. Cache files are small (collection metadata, test results) and don't need database features. JSON is human-readable for debugging and natively supported by Pydantic v2's `model_dump_json()` / `model_validate_json()`.

**Alternatives Considered**:
- **SQLite**: Provides querying capability. Rejected because cache data is simple key-value/list structure; SQLite adds complexity without benefit.
- **YAML**: Already used for agent config. Rejected because JSON is faster to parse and Pydantic has native JSON support.

**Cache locations**:
- Test cache: `{data_dir}/test-cache/{path_hash}.json` (24h TTL)
- Collection cache: `{data_dir}/collection-cache.json` (7d TTL)
- Offline results: `{data_dir}/results/{result_id}.json` (persist until synced)

Where `data_dir` = `platformdirs.user_data_dir("shuttersense", "ShutterSense")`.

---

## Decision 3: Agent-Initiated Collection Creation API

**Decision**: Add `POST /api/agent/v1/collections` endpoint that reuses `CollectionService.create()` with agent context.

**Rationale**: The existing `CollectionService` already handles collection creation with tenant isolation. The new endpoint authenticates the agent, resolves the agent's `team_id`, and delegates to the same service. This avoids duplicating creation logic. The agent is automatically set as `bound_agent_id` for LOCAL collections.

**Alternatives Considered**:
- **Reuse user-facing `POST /api/collections`**: Would work but agent authentication uses a different middleware path (`AgentContext` vs `TenantContext`). A dedicated agent endpoint keeps concerns separated.
- **New service method**: Rejected because the existing `create()` method accepts all needed parameters; only the authentication/binding logic is new.

---

## Decision 4: Offline Result Upload API

**Decision**: Add `POST /api/agent/v1/results/upload` endpoint that creates an `AnalysisResult` and associates it with a Job record.

**Rationale**: Online execution creates a Job first, then the agent reports results via `POST /api/agent/v1/jobs/{guid}/complete`. For offline results, there's no pre-existing Job. The upload endpoint creates both the Job record (status=COMPLETED, with timestamps from the offline execution) and the AnalysisResult in a single transaction. This ensures offline results appear identically to online results in the web UI.

**Alternatives Considered**:
- **Create job-then-complete flow**: Agent would POST to create a job, then POST to complete it. Rejected because it's two round-trips for a single logical operation and the job was never "running" on the server.
- **Direct AnalysisResult creation**: Skip job record entirely. Rejected because SC-007 requires "100% of tool executions produce tracked job records."

---

## Decision 5: Test Command Execution Model

**Decision**: Test command runs synchronously in the CLI process (not via the polling loop).

**Rationale**: The test command is interactive - the user runs it and waits for output. It doesn't create a server job. It directly invokes analysis modules from `agent/src/analysis/` and the local filesystem adapter from `agent/src/remote/local_adapter.py`. This mirrors how `JobExecutor` works but without the server communication layer.

**Alternatives Considered**:
- **Create a local-only job**: Route through the job executor. Rejected because test is specifically designed to work without server connectivity.
- **Async execution with polling**: Overkill for a synchronous CLI command.

---

## Decision 6: Constitution Principle I Replacement

**Decision**: Replace "I. Independent CLI Tools" with "I. Agent-Only Tool Execution" that mandates all analysis runs through authenticated agents.

**Rationale**: The constitution (v1.6.0) already has Principle VI (Agent-Only Execution) for the web application. The replacement of Principle I makes this universal: no tool execution path exists outside the agent. This is the explicit goal of US5.

**Content for replacement**:
- All analysis tool execution MUST go through registered, authenticated agents
- Agents provide: authentication, tenant isolation, job tracking, result persistence, audit trail
- No standalone tool execution scripts may exist in the repository
- Shared analysis modules (`agent/src/analysis/`) remain as libraries consumed by the agent
- Shared utilities (`utils/`) remain for agent use

---

## Decision 7: CLI Tool Test File Handling

**Decision**: Delete `tests/test_photo_stats.py` and `tests/test_photo_pairing.py` entirely. Analysis module tests in `agent/tests/` are preserved.

**Rationale**: The CLI-specific test files test the standalone script entry points (argparse, signal handling, report file naming). These entry points are being deleted. The actual analysis logic is tested by `agent/tests/unit/` which exercises the same `agent/src/analysis/` modules. No test coverage is lost for business logic.

**Alternatives Considered**:
- **Convert CLI tests to agent command tests**: The tests are specific to argparse and standalone script patterns. New agent command tests will be written from scratch to test Click commands.
- **Keep and skip**: Keeping dead tests adds maintenance burden and confuses contributors.

---

## Decision 8: Run Command Online vs Offline Mode

**Decision**: Online mode (default) creates a server job via `POST /api/agent/v1/jobs` and executes it locally. Offline mode (`--offline`) runs locally without any server communication.

**Rationale**: Online mode ensures every execution is tracked as a Job with full audit trail. The agent effectively "self-assigns" the job by creating it and immediately executing it. Offline mode is the escape hatch for disconnected environments - results are stored locally and synced later via `shuttersense-agent sync`.

**Alternatives Considered**:
- **Always offline, sync later**: Simpler but loses real-time job tracking and progress visibility in the web UI.
- **Online-only**: Rejects the P1 offline use case entirely.

---

## Dependency Review

| Dependency | Status | Notes |
|------------|--------|-------|
| Click 8.1+ | Already installed | Agent CLI framework |
| httpx | Already installed | Agent HTTP client |
| Pydantic v2 | Already installed | Data validation |
| platformdirs | Already installed | Cross-platform paths |
| Agent analysis modules | Exist in `agent/src/analysis/` | No changes needed |
| Agent API client | Exists in `agent/src/api_client.py` | Needs new methods |
| Backend agent routes | Exist in `backend/src/api/agent/` | Needs new endpoints |
| CollectionService | Exists in `backend/src/services/` | Needs agent-creation method |

**No new dependencies required.** All needed libraries are already in the agent and backend dependency trees.
