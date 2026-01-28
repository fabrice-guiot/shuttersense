# Agent CLI Command Contracts

**Feature Branch**: `108-remove-cli-direct-usage`
**Created**: 2026-01-28

## Command Tree

```
shuttersense-agent
├── test <path>                     # US1: Test local path
│   ├── --tool <tool>               # Filter to specific tool
│   ├── --check-only                # Accessibility check only
│   └── --output <file>             # Save HTML report
│
├── collection                      # US2 + US4: Collection management
│   ├── create <path>               # Create from local path
│   │   ├── --name <name>           # Collection name (skip prompt)
│   │   ├── --skip-test             # Skip test validation
│   │   └── --analyze               # Run initial analysis after creation
│   ├── list                        # List bound collections
│   │   ├── --type <type>           # Filter: local|remote|all
│   │   ├── --status <status>       # Filter: accessible|inaccessible|pending
│   │   └── --offline               # Use cached data
│   ├── sync                        # Refresh collection cache
│   └── test <guid>                 # Re-test accessibility
│
├── run <collection-guid>           # US3: Run analysis tool
│   ├── --tool <tool>               # Required: photostats|photo_pairing|pipeline_validation
│   ├── --offline                   # No server (LOCAL only)
│   └── --output <file>             # Save HTML report
│
├── sync                            # US3: Upload offline results
│   └── --dry-run                   # Preview without uploading
│
├── self-test                       # US6: Verify configuration
│
├── register                        # EXISTING
├── start                           # EXISTING
├── config                          # EXISTING
├── connectors                      # EXISTING
└── capabilities                    # EXISTING
```

---

## Command: `test`

**Purpose**: Test a local directory for accessibility and optionally run analysis tools.

```
shuttersense-agent test <path> [OPTIONS]
```

| Argument/Option | Type | Required | Default | Description |
|-----------------|------|----------|---------|-------------|
| `path` | string | Yes | — | Absolute path to test |
| `--tool` | string | No | all | Specific tool: `photostats`, `photo_pairing`, `pipeline_validation` |
| `--check-only` | flag | No | false | Only check accessibility, skip analysis |
| `--output` | string | No | — | Save HTML report to this file path |

**Exit codes**: 0 = success, 1 = path not accessible, 2 = analysis failed

**Output format** (stdout):
```
Testing path: /photos/2024
  Checking accessibility... OK (readable, 1,247 files found)
  Running photostats... OK (analysis complete)
  Running photo_pairing... OK (analysis complete)

Test Summary:
  Files: 1,247 (1,200 photos, 47 sidecars)
  Issues: 3 orphaned sidecars found
  Ready to create Collection: Yes
```

**Server communication**: None required.

---

## Command: `collection create`

**Purpose**: Create a Collection on the server from a local path.

```
shuttersense-agent collection create <path> [OPTIONS]
```

| Argument/Option | Type | Required | Default | Description |
|-----------------|------|----------|---------|-------------|
| `path` | string | Yes | — | Absolute path for the collection |
| `--name` | string | No | folder name | Collection display name |
| `--skip-test` | flag | No | false | Skip test validation |
| `--analyze` | flag | No | false | Queue initial analysis after creation |

**Exit codes**: 0 = created, 1 = test failed, 2 = server error, 3 = already exists

**Behavior**:
1. Check test cache for valid entry (within 24h)
2. If no valid cache and `--skip-test` not set → run test automatically
3. If `--name` not provided → prompt interactively (suggest folder name)
4. Call `POST /api/agent/v1/collections`
5. Display GUID and web URL
6. If `--analyze` → create job on server

**Server communication**: Required.

---

## Command: `collection list`

**Purpose**: List all Collections bound to this agent.

```
shuttersense-agent collection list [OPTIONS]
```

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `--type` | string | No | all | Filter: `local`, `remote`, `all` |
| `--status` | string | No | — | Filter: `accessible`, `inaccessible`, `pending` |
| `--offline` | flag | No | false | Use cached data (no server call) |

**Exit codes**: 0 = success, 1 = no collections found

**Output format** (table):
```
GUID                  TYPE    NAME                LOCATION                STATUS         LAST ANALYSIS  OFFLINE
col_01hgw2bbg00001    LOCAL   Vacation 2024       /photos/2024           Accessible     2024-01-20     Yes
col_01hgw2ccc00001    S3      Cloud Backup        my-bucket/photos       Accessible     2024-01-18     No
```

**Server communication**: Required unless `--offline` flag set.

---

## Command: `collection sync`

**Purpose**: Refresh the local collection cache from the server.

```
shuttersense-agent collection sync
```

No options. Always requires server connection.

**Exit codes**: 0 = success, 1 = server unreachable

---

## Command: `collection test`

**Purpose**: Re-test a Collection's local path accessibility and update the server.

```
shuttersense-agent collection test <guid>
```

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `guid` | string | Yes | Collection GUID to test |

**Exit codes**: 0 = accessible, 1 = not accessible, 2 = collection not found

**Server communication**: Required (updates server status).

---

## Command: `run`

**Purpose**: Run an analysis tool against a Collection.

```
shuttersense-agent run <collection-guid> --tool <tool> [OPTIONS]
```

| Argument/Option | Type | Required | Default | Description |
|-----------------|------|----------|---------|-------------|
| `collection-guid` | string | Yes | — | Collection GUID |
| `--tool` | string | Yes | — | Tool: `photostats`, `photo_pairing`, `pipeline_validation` |
| `--offline` | flag | No | false | Run locally without server |
| `--output` | string | No | — | Save HTML report to this file |

**Exit codes**: 0 = success, 1 = collection not found, 2 = execution error, 3 = cannot run offline on remote

**Online mode behavior**:
1. Create job on server via API
2. Execute tool locally
3. Report results to server
4. Display summary

**Offline mode behavior**:
1. Load collection from cache
2. Verify it's LOCAL type (reject remote)
3. Execute tool locally
4. Save OfflineResult to `{data_dir}/results/`
5. Display summary + sync reminder

**Server communication**: Required for online mode. Not used in offline mode.

---

## Command: `sync`

**Purpose**: Upload pending offline analysis results to the server.

```
shuttersense-agent sync [OPTIONS]
```

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `--dry-run` | flag | No | false | Show what would be uploaded |

**Exit codes**: 0 = success (or nothing to sync), 1 = upload error, 2 = server unreachable

**Behavior**:
1. Scan `{data_dir}/results/` for unsynced results
2. If `--dry-run` → list results and exit
3. Upload each result via `POST /api/agent/v1/results/upload`
4. Mark uploaded results as synced
5. Delete synced result files
6. Resume from last successful upload on retry

**Server communication**: Required.

---

## Command: `self-test`

**Purpose**: Verify agent configuration and server connectivity.

```
shuttersense-agent self-test
```

No options.

**Checks performed**:
1. Server connectivity (URL reachable, latency)
2. Agent registration (API key valid, not revoked)
3. Tool availability (all three tools importable)
4. Authorized roots (each configured root accessible)

**Exit codes**: 0 = all pass, 1 = warnings only, 2 = failures

**Output format**:
```
Agent Self-Test
═══════════════════════════════════════════════════

Server Connection:
  URL: https://api.shuttersense.ai      OK
  Latency: 45ms                         OK

Agent Registration:
  Agent ID: agt_01hgw2bbg...            OK
  Status: ONLINE                        OK

Tools:
  photostats                            OK
  photo_pairing                         OK
  pipeline_validation                   OK

Authorized Roots:
  /photos                               OK (readable)
  /mnt/nas                              WARN (not mounted)

═══════════════════════════════════════════════════
Self-test complete: 1 warning
```

**Server communication**: Required.
