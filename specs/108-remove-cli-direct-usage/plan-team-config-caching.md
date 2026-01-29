# Plan: Team Config Caching for Agent CLI Commands

## Problem

`agent/cli/test.py:86-91` passes `pipeline_config=None` to `run_pipeline_validation()`, crashing with `'NoneType' object has no attribute 'pairing_nodes'`. More broadly, all three tools in the `test` command (and `run` command) use hardcoded default extensions with no camera mappings or processing methods — producing inaccurate results.

## Solution Overview

1. **New backend endpoint** `GET /api/agent/v1/config` — returns team config + default pipeline without requiring a job
2. **New agent-side config cache** — persists team config as JSON to disk (24h TTL)
3. **Modified `test` command** — fetches/loads config before running tools; `--check-only` unchanged
4. **Modified `run` command** — same config resolution (server fetch or cached), both online and offline modes
5. **Extract shared pipeline builder** — reuse `_create_pipeline_config_from_api` from `job_executor.py`

## Config Resolution Logic (for `test` without `--check-only` and `run`)

```
1. Agent registered + server reachable?
   → Fetch from server, cache to disk, run with fresh config
2. Server unreachable, valid cache exists (< 24h)?
   → Use cache silently (no warning needed, still fresh)
3. Server unreachable, expired cache exists?
   → Warning: "Using cached config from {date}, may be outdated"
   → Run with expired cache
4. No cache at all, server unreachable?
   → Error: "Team config required for analysis tools. Connect to server
     or use --check-only for accessibility testing only."
   → Exit code 1
```

## Implementation Steps

### Step 1: Backend — `TeamConfigResponse` schema

**File:** `backend/src/api/agent/schemas.py`

Add after `JobConfigResponse` (line ~935):

```python
class TeamConfigResponse(BaseModel):
    """Standalone team configuration (not job-specific)."""
    config: JobConfigData
    default_pipeline: Optional[PipelineData] = None
```

Reuses existing `JobConfigData` and `PipelineData` — no new field definitions needed.

### Step 2: Backend — `GET /api/agent/v1/config` endpoint

**File:** `backend/src/api/agent/routes.py`

Add import of `TeamConfigResponse` to the schema import block (line ~34-108). Add route after the existing `get_job_config` endpoint (after line 978, before the chunked upload section):

- Uses `AgentContext` for auth (same as all agent endpoints)
- Loads config via `DatabaseConfigLoader(team_id=ctx.team_id, db=db)`
- Queries default pipeline: `Pipeline.is_default == True` filtered by `team_id`
- Returns `TeamConfigResponse`

### Step 3: Agent cache — `TeamConfigCache` model

**File:** `agent/src/cache/__init__.py`

Add constant `TEAM_CONFIG_CACHE_TTL_HOURS = 24` and two models:

- `CachedPipeline(BaseModel)` — guid, name, version, nodes, edges
- `TeamConfigCache(BaseModel)` — agent_guid, fetched_at, expires_at, photo_extensions, metadata_extensions, cameras, processing_methods, require_sidecar, default_pipeline (Optional[CachedPipeline])
- `is_valid()` method (same pattern as `CollectionCache`)
- Add to `__all__`

### Step 4: Agent cache — `team_config_cache.py` storage module

**New file:** `agent/src/cache/team_config_cache.py`

Following `collection_cache.py` pattern exactly:
- `_get_cache_file()` → `{data_dir}/team-config-cache.json`
- `save(cache)` → write JSON
- `load()` → parse JSON or return None
- `load_valid()` → load + check `is_valid()`
- `make_cache(agent_guid, server_response)` → construct `TeamConfigCache` from API response dict

### Step 5: Agent config — update `get_cache_paths()`

**File:** `agent/src/config.py` (line 94-99)

Add `"team_config_cache_file": data_dir / "team-config-cache.json"` to the returned dict.

### Step 6: Agent API client — `get_team_config()` method

**File:** `agent/src/api_client.py`

Add sync method using existing `self.get("/config")` pattern (returns `httpx.Response`):

```python
def get_team_config(self) -> dict:
    response = self.get("/config")
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 401:
        raise AuthenticationError(...)
    else:
        raise ApiError(...)
```

### Step 7: Extract pipeline config builder

**New file:** `agent/src/analysis/pipeline_config_builder.py`

Extract `_create_pipeline_config_from_api` logic from `job_executor.py:1299-1390` into a standalone function `build_pipeline_config(nodes_json, edges_json) -> PipelineConfig`. This function:
- Builds output map from edges
- Parses node dicts into typed node objects (CaptureNode, FileNode, ProcessNode, PairingNode, BranchingNode, TerminationNode)
- Creates and returns `PipelineConfig`

Update `job_executor.py:_create_pipeline_config_from_api` to delegate to the new shared function.

### Step 8: Shared config resolver module

**New file:** `agent/src/config_resolver.py`

Contains `resolve_team_config(quiet=False) -> Optional[TeamConfigCache]`:
- Encapsulates the server-fetch → fresh-cache → expired-cache → None chain
- `quiet=False` prints warnings/status to stderr via `click.echo(..., err=True)`
- Used by both `test.py` and `run.py`

### Step 9: Modify `test` command

**File:** `agent/cli/test.py`

**A. Use shared config resolver:**
- After accessibility check, before tool loop:
  - If not `--check-only`: call `resolve_team_config()`
  - If config is `None` and not `--check-only`: print error, suggest `--check-only`, `sys.exit(1)`
  - Use config values for `photo_extensions`, `metadata_extensions`, `require_sidecar`
  - Keep `DEFAULT_*` constants as fallback only for `--check-only` file categorization

**B. Fix `_run_pipeline_validation`:**
- Accept `pipeline_config: Optional[PipelineConfig]` parameter
- If `None`: return a result dict with `skipped=True` and reason message, plus print a warning
- If provided: call `run_pipeline_validation()` with the real config

**C. Update `_run_photostats` and `_run_photo_pairing`:**
- Accept extensions/config from caller instead of using hardcoded values

### Step 10: Apply same pattern to `run` command

**File:** `agent/cli/run.py`

The `run` command should use the same config resolution. The behavior depends on connectivity:

- **`--offline` flag or server unreachable:** Use cached config (same fallback chain as `test`)
- **Online (server reachable):** Fetch config from server, cache it, then run

Changes:
- Import `resolve_team_config` from shared module
- Replace hardcoded extensions in `_run_photostats` (lines 289-295) and `_run_photo_pairing` with config values
- Replace `_run_pipeline_validation` stub (lines 373-390) with real execution using cached pipeline config (skip with warning if no pipeline available)
- `_execute_tool` gains a `team_config` parameter passed through to tool functions

## Files Modified

| File | Change |
|------|--------|
| `backend/src/api/agent/schemas.py` | Add `TeamConfigResponse` |
| `backend/src/api/agent/routes.py` | Add `GET /config` endpoint + import |
| `agent/src/cache/__init__.py` | Add `TeamConfigCache`, `CachedPipeline`, constant |
| `agent/src/cache/team_config_cache.py` | **New** — cache storage module |
| `agent/src/config.py` | Add key to `get_cache_paths()` |
| `agent/src/api_client.py` | Add `get_team_config()` sync method |
| `agent/src/analysis/pipeline_config_builder.py` | **New** — extracted from job_executor |
| `agent/src/job_executor.py` | Delegate to shared builder |
| `agent/src/config_resolver.py` | **New** — shared config resolution logic |
| `agent/cli/test.py` | Use config resolver + fix all 3 tool functions |
| `agent/cli/run.py` | Use config resolver + real config for all 3 tools |

## Verification

1. `shuttersense-agent test /path --check-only` — still works without config
2. `shuttersense-agent test /path` with server up — fetches config, caches, all 3 tools use real config
3. Stop server, `shuttersense-agent test /path` — uses cached config with appropriate warning
4. Delete cache, stop server, `shuttersense-agent test /path` — error with suggestion
5. `shuttersense-agent run col_xxx --tool photostats` — uses real config from server/cache
6. `shuttersense-agent run col_xxx --tool pipeline_validation --offline` — uses cached pipeline config
7. Run existing agent tests: `python3 -m pytest agent/tests/ -v`
8. Run backend tests: `python3 -m pytest backend/tests/unit/ -v`
