# Quickstart: Remove CLI Direct Usage

**Feature Branch**: `108-remove-cli-direct-usage`
**Created**: 2026-01-28

## Prerequisites

- ShutterSense agent binary installed (`shuttersense-agent`)
- Agent registered with the server (`shuttersense-agent register`)
- Agent started at least once to verify connectivity (`shuttersense-agent start`)
- A local directory containing photo files for testing

## Implementation Order

The feature is organized into 6 implementation phases. Each phase produces independently testable functionality.

### Phase 1: Test Command (P0)

**Goal**: Users can validate a local path before creating a Collection.

**Key files to create/modify**:
- `agent/cli/test.py` - Click command for `test`
- `agent/src/cache/test_cache.py` - Test result caching
- `agent/cli/main.py` - Register `test` command

**Verification**:
```bash
# Test a local directory
shuttersense-agent test /path/to/photos
# Should display file counts and analysis results

# Test with specific tool
shuttersense-agent test /path/to/photos --tool photostats

# Test accessibility only
shuttersense-agent test /path/to/photos --check-only

# Save HTML report
shuttersense-agent test /path/to/photos --output report.html
```

---

### Phase 2: Collection Create Command (P0)

**Goal**: Users can create a server-side Collection from a tested local path.

**Key files to create/modify**:
- `agent/cli/collection.py` - Click group + `create` subcommand
- `agent/src/api_client.py` - Add `create_collection()` method
- `backend/src/api/agent/routes.py` - Add `POST /api/agent/v1/collections`
- `backend/src/api/agent/schemas.py` - Add request/response schemas

**Verification**:
```bash
# Create Collection from tested path
shuttersense-agent test /path/to/photos
shuttersense-agent collection create /path/to/photos --name "My Photos"
# Should display Collection GUID and web URL

# Create and immediately analyze
shuttersense-agent collection create /path/to/photos --name "My Photos" --analyze
```

---

### Phase 3: Run and Sync Commands (P1)

**Goal**: Users can run analysis tools online or offline and sync results.

**Key files to create/modify**:
- `agent/cli/run.py` - Click command for `run`
- `agent/cli/sync_results.py` - Click command for `sync`
- `agent/src/cache/result_store.py` - Offline result storage
- `agent/src/api_client.py` - Add `upload_result()` method
- `backend/src/api/agent/routes.py` - Add `POST /api/agent/v1/results/upload`

**Verification**:
```bash
# Online run (creates job on server)
shuttersense-agent run col_01hgw2bbg... --tool photostats

# Offline run (saves result locally)
shuttersense-agent run col_01hgw2bbg... --tool photostats --offline

# Preview what would sync
shuttersense-agent sync --dry-run

# Upload offline results
shuttersense-agent sync
```

---

### Phase 4: Collection Management Commands (P1)

**Goal**: Users can list, sync cache, and re-test bound Collections.

**Key files to create/modify**:
- `agent/cli/collection.py` - Add `list`, `sync`, `test` subcommands
- `agent/src/cache/collection_cache.py` - Collection cache management
- `agent/src/api_client.py` - Add `list_collections()`, `test_collection()` methods
- `backend/src/api/agent/routes.py` - Add `GET /api/agent/v1/collections`, `POST .../test`

**Verification**:
```bash
# List all bound collections
shuttersense-agent collection list

# List offline (cached)
shuttersense-agent collection list --offline

# Refresh cache
shuttersense-agent collection sync

# Re-test accessibility
shuttersense-agent collection test col_01hgw2bbg...
```

---

### Phase 5: CLI Tool Removal (P2)

**Goal**: Remove standalone CLI tools and update project documentation.

**Key files to delete**:
- `photo_stats.py`
- `photo_pairing.py`
- `pipeline_validation.py`
- `tests/test_photo_stats.py`
- `tests/test_photo_pairing.py`

**Key files to update**:
- `.specify/memory/constitution.md` - Replace Principle I
- `CLAUDE.md` - Remove CLI references
- `README.md` - Agent-only workflow
- `docs/installation.md`, `docs/configuration.md` - Agent focus
- `docs/photostats.md`, `docs/photo-pairing.md` - Archive notice

**Verification**:
```bash
# Verify CLI tools are gone
python3 photo_stats.py  # Should fail: file not found

# Verify agent still works
shuttersense-agent test /path/to/photos
shuttersense-agent run col_01hgw2bbg... --tool photostats

# Verify analysis modules still importable
python3 -c "from src.analysis import calculate_stats; print('OK')"
```

---

### Phase 6: Self-Test and Polish (P2)

**Goal**: Users can verify their agent configuration.

**Key files to create/modify**:
- `agent/cli/self_test.py` - Click command for `self-test`
- `agent/cli/main.py` - Register `self-test` command

**Verification**:
```bash
# Run self-test
shuttersense-agent self-test
# Should show pass/fail for each check

# Simulate failure (e.g., stop server)
shuttersense-agent self-test
# Should show connectivity failure with remediation
```

---

## Architecture Notes

### Pattern: Reuse Existing Analysis Modules

All new commands use the analysis modules already in `agent/src/analysis/`:
- `photostats_analyzer.py` - `calculate_stats()`, `analyze_pairing()`
- `photo_pairing_analyzer.py` - `build_imagegroups()`, `calculate_analytics()`
- `pipeline_analyzer.py` - `run_pipeline_validation()`

The `test` and `run` commands invoke these modules directly (same as `JobExecutor` but without server job lifecycle).

### Pattern: Cache Module Structure

Each cache module (`agent/src/cache/`) follows the same pattern:
1. Pydantic model for cache entry
2. `save()` / `load()` / `is_valid()` methods
3. File-based storage using `platformdirs.user_data_dir()`
4. TTL-based expiration

### Pattern: Click Command Registration

New commands are registered in `agent/cli/main.py`:
```python
from cli.test import test
from cli.collection import collection
from cli.run import run
from cli.sync_results import sync
from cli.self_test import self_test

cli.add_command(test)
cli.add_command(collection)
cli.add_command(run)
cli.add_command(sync)
cli.add_command(self_test)
```
