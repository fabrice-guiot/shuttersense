# Unified Local and Remote Collection Processing

This folder contains the refactoring plan for unifying analysis logic across local and remote collections.

## Problem Statement

The codebase has parallel implementations of analysis logic for local and remote collections:
- ~250 lines of duplicated/stub analysis code
- Subtle behavioral differences between local and remote processing
- Maintenance burden (bugs must be fixed in two places)

**Current architecture:**
```
Local:  Path objects → photo_stats.py / photo_pairing.py → Results
Remote: FileInfo objects → job_executor.py (duplicated logic) → Results
```

**Target architecture:**
```
Local:  LocalAdapter → FileInfo → Shared Analyzer → Results
Remote: S3/GCS/SMB → FileInfo → Shared Analyzer → Results
```

## Documents

1. **[Architecture Overview](./01-architecture-overview.md)** - High-level design and rationale
2. **[FileInfo Contract](./02-fileinfo-contract.md)** - Unified file information interface
3. **[Analysis Modules](./03-analysis-modules.md)** - Shared analysis logic specifications
4. **[Implementation Guide](./04-implementation-guide.md)** - Step-by-step implementation phases

## Key Benefits

- **Single source of truth** for analysis logic (in agent)
- **Correct packaging** - agent owns tool execution
- **~250 lines removed** from job_executor.py
- **Future-proof** - ready for CLI tool deprecation
- **Testable** - analysis logic unit-testable independently
- **Consistent results** - identical JSON/HTML output for local and remote

## Output Consistency Guarantee

After this refactoring:

| Aspect | Outcome |
|--------|---------|
| **JSON Results** | Identical structure for LOCAL and REMOTE collections |
| **HTML Reports** | Same Jinja2 template, same content for both collection types |
| **Golden Standard** | LOCAL collection processing is the reference implementation |
| **Deprecated** | Current half-baked REMOTE implementations will be replaced |

**Important:** The current LOCAL collection processing by the agent produces correct results and serves as the specification. The current REMOTE implementations have bugs and inconsistencies that will be eliminated by using the shared analysis modules.

## Affected Tools

| Tool | Current State | After Refactoring |
|------|---------------|-------------------|
| PhotoStats | Duplicated pairing analysis | Shared `analyze_pairing()` |
| Photo Pairing | Duplicated group building | Shared `build_imagegroups()` |
| Pipeline Validation | Stub implementation | Full shared `run_pipeline_validation()` |

## File Structure After Refactoring

```
agent/
├── src/
│   ├── analysis/                        # NEW - shared analysis logic
│   │   ├── __init__.py
│   │   ├── photo_pairing_analyzer.py    # build_imagegroups(), calculate_analytics()
│   │   ├── photostats_analyzer.py       # analyze_pairing(), calculate_stats()
│   │   └── pipeline_analyzer.py         # run_pipeline_validation()
│   ├── remote/
│   │   ├── __init__.py                  # Add LocalAdapter export
│   │   ├── base.py                      # Enhanced FileInfo (canonical)
│   │   ├── local_adapter.py             # NEW - LocalAdapter
│   │   ├── s3_adapter.py
│   │   ├── gcs_adapter.py
│   │   └── smb_adapter.py
│   └── job_executor.py                  # Uses shared analysis (~250 lines removed)
```
