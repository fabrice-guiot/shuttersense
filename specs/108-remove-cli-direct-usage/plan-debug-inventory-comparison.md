# Plan: Agent Debug Command — Inventory Manifest Comparison

## Goal
Add a `debug` command group to the agent CLI, excluded from production builds, with a first subcommand `compare-inventory` that compares FileInfo from the two most recent inventory manifests to diagnose why Input State hashes change between runs.

---

## Step 1: New Backend Endpoint for Connector Debug Info

The existing `/connectors/{guid}/metadata` endpoint doesn't return `inventory_config` and rejects server-side connectors. A new lightweight endpoint is needed.

**Files:**
- [routes.py](backend/src/api/agent/routes.py) — add endpoint after line ~1648
- [schemas.py](backend/src/api/agent/schemas.py) — add response schema

**New endpoint:** `GET /api/agent/v1/connectors/{guid}/debug-info`

Response schema `AgentConnectorDebugInfoResponse`:
- `guid: str`
- `name: str`
- `type: str` (s3, gcs)
- `credential_location: str`
- `inventory_config: Optional[Dict[str, Any]]`

Unlike the metadata endpoint, this one does NOT reject server-side connectors (debug access for all connector types).

---

## Step 2: Create `agent/cli/debug.py`

Single file following the existing CLI patterns (Click group with subcommands, `_get_api_client()` helper).

**Command:** `shuttersense-agent debug compare-inventory <connector_guid>`

**Options:**
- `--folder PATH` — Filter entries to a specific folder prefix
- `--limit N` — Max diff entries to show (default 50)
- `--show-all` — Show all differences
- `--verbose` — Show full details per entry

**Implementation flow:**
1. Load `AgentConfig`, verify registration
2. Fetch connector debug info via `client.get(f"/connectors/{connector_guid}/debug-info")`
3. Validate `inventory_config` exists
4. Get credentials from `CredentialStore` (agent-side) or error
5. Create storage adapter (`S3Adapter` / `GCSAdapter`) — inline helper, same pattern as [job_executor.py:2490-2542](agent/src/job_executor.py#L2490-L2542)
6. Discover manifest files — call `adapter.list_files(location)`, filter to `manifest.json`, sort reverse
7. Validate at least 2 manifests exist (error if < 2, single-manifest summary if exactly 1)
8. Fetch and parse both manifests using existing parsers from [inventory_parser.py](agent/src/analysis/inventory_parser.py) (`parse_s3_manifest`, `parse_s3_csv_stream`, `parse_gcs_manifest`, etc.)
9. Optionally filter entries by `--folder` prefix (same logic as [inventory_import_tool.py:805-828](agent/src/tools/inventory_import_tool.py#L805-L828))
10. Compute diff: added, removed, changed entries (keyed by `entry.key`)
11. Compute Input State file list hash for both using [InputStateComputer](agent/src/input_state.py) from `compute_file_list_hash_from_file_info()`
12. Print structured comparison output

**Key reuse points:**
- `_fetch_object` / `_fetch_object_stream` — duplicate locally (~10 lines), same pattern as [inventory_import_tool.py:642-691](agent/src/tools/inventory_import_tool.py#L642-L691)
- Manifest path construction — same logic as `_execute_s3_import` / `_execute_gcs_import`
- Parsers — direct import from `src.analysis.inventory_parser`
- Hash computation — direct import from `src.input_state`

---

## Step 3: Wire Up Conditional Import in `main.py`

**File:** [main.py](agent/cli/main.py) — add after line 53

```python
import os as _os
if _os.environ.get("SHUSAI_DEBUG_COMMANDS", "").lower() in ("1", "true", "yes"):
    try:
        from cli.debug import debug
        cli.add_command(debug)
    except ImportError:
        pass
```

**Why this works for build exclusion:**
- PyInstaller does static analysis of module-level imports to determine what to bundle
- Since the `from cli.debug import debug` is inside a conditional block that evaluates at runtime (not a top-level import), PyInstaller will NOT follow it
- Even if it did, the `--add-data "cli:cli"` copies files but PyInstaller only bundles code it can trace from imports
- The `try/except ImportError` provides an additional safety net
- No changes to build scripts needed

---

## Step 4: Output Format

```
=== Inventory Manifest Comparison ===
Connector: con_xxx (My S3 Bucket)
Type: S3

Manifest A (newer): 2026-01-28T01-00Z/manifest.json
Manifest B (older): 2026-01-27T01-00Z/manifest.json

=== Entry Counts ===
  Manifest A: 145,230 entries
  Manifest B: 145,228 entries

=== Input State File List Hashes ===
  Manifest A: a1b2c3d4e5f6...
  Manifest B: f6e5d4c3b2a1...
  Match: NO

=== Differences ===
  Added (in A, not in B): 5
  Removed (in B, not in A): 3
  Changed (different size/mtime/etag): 12

--- Changed entries ---
  ~ path/to/photo.dng
    size: 25,200,000 → 25,200,000  (same)
    mtime: "2026-01-15T10:00:00Z" → "2026-01-15T10:00:01.000Z"  (CHANGED)
    etag: "abc123" → "abc123"  (same)

--- Added entries ---
  + path/to/new_photo.dng (25.2 MB, mtime=2026-01-28T10:30:00Z)
...
```

---

## Files Changed Summary

| File | Action | Lines |
|------|--------|-------|
| `agent/cli/debug.py` | CREATE | ~250 |
| `agent/cli/main.py` | MODIFY | +6 lines |
| `backend/src/api/agent/routes.py` | MODIFY | +25 lines |
| `backend/src/api/agent/schemas.py` | MODIFY | +12 lines |

No changes to build scripts, no changes to existing agent modules.

---

## Verification

1. **Unit test:** Run existing agent tests to confirm no regressions: `python3 -m pytest agent/tests/ -v`
2. **Manual test — env var gating:** Without `SHUSAI_DEBUG_COMMANDS=1`, run `shuttersense-agent --help` and verify `debug` does NOT appear in commands list
3. **Manual test — env var enabled:** With `SHUSAI_DEBUG_COMMANDS=1`, run `shuttersense-agent debug --help` and verify `compare-inventory` appears
4. **Manual test — full flow:** With env var set and a configured connector with inventory, run `SHUSAI_DEBUG_COMMANDS=1 shuttersense-agent debug compare-inventory <connector_guid>` and verify comparison output
