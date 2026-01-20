# Architecture Overview

## Future Direction

The architecture is designed with the following future direction in mind:

- **Server-side tools deprecated** - will be removed at end of Epic
- **CLI tools deprecated** - will only run through agent commands
- **Agent is primary executor** - all tool execution goes through agent

Therefore, **canonical analysis code lives in the agent**, not backend.

## Current vs Target Architecture

### Current Architecture (Problem)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         LOCAL COLLECTIONS                           │
├─────────────────────────────────────────────────────────────────────┤
│  photo_stats.py    ──► scan_folder() ──► _analyze_pairing()         │
│  photo_pairing.py  ──► scan_folder() ──► build_imagegroups()        │
│  pipeline_val.py   ──► scan + photo_pairing ──► validate_all()      │
└─────────────────────────────────────────────────────────────────────┘
                              ↓ DIFFERENT CODE PATH
┌─────────────────────────────────────────────────────────────────────┐
│                        REMOTE COLLECTIONS                           │
├─────────────────────────────────────────────────────────────────────┤
│  job_executor.py   ──► _run_photostats_remote()   [DUPLICATED]      │
│  job_executor.py   ──► _run_photo_pairing_remote() [DUPLICATED]     │
│  job_executor.py   ──► _run_pipeline_remote()      [STUB ONLY]      │
└─────────────────────────────────────────────────────────────────────┘
```

**Problems:**
1. ~250 lines of duplicated/stub code
2. Subtle behavioral differences leading to inconsistent results
3. Bugs must be fixed in two places
4. Pipeline Validation doesn't actually validate on remote (stub implementation)
5. Photo Pairing remote has wrong image counting logic
6. JSON results and HTML reports differ between local and remote

### Target Architecture (Solution)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    STORAGE ADAPTERS (Unified Interface)             │
├─────────────────────────────────────────────────────────────────────┤
│  LocalAdapter   │  S3Adapter   │  GCSAdapter   │  SMBAdapter        │
│       ↓                ↓              ↓              ↓               │
│                    List[FileInfo]                                    │
└─────────────────────────────────────────────────────────────────────┘
                              ↓ SAME CODE PATH
┌─────────────────────────────────────────────────────────────────────┐
│                    SHARED ANALYSIS MODULES                          │
├─────────────────────────────────────────────────────────────────────┤
│  photostats_analyzer.py    ──► calculate_stats(), analyze_pairing() │
│  photo_pairing_analyzer.py ──► build_imagegroups(), calculate_analytics()│
│  pipeline_analyzer.py      ──► run_pipeline_validation()            │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│                         IDENTICAL RESULTS                           │
├─────────────────────────────────────────────────────────────────────┤
│  Same JSON structure  │  Same HTML template  │  Same behavior       │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. FileInfo as Unified Interface

All storage adapters produce `List[FileInfo]` with the same structure:

```python
@dataclass
class FileInfo:
    path: str           # Relative path from collection root
    size: int           # File size in bytes
    last_modified: Optional[str] = None

    # Computed properties (like pathlib.Path)
    @property
    def name(self) -> str: ...      # Filename only
    @property
    def extension(self) -> str: ... # ".dng", ".xmp"
    @property
    def stem(self) -> str: ...      # Filename without extension
```

### 2. Analysis Modules in Agent

The shared analysis modules live in `agent/src/analysis/` because:
- Agent is the primary executor
- Backend is just API coordination
- CLI tools will be deprecated (become agent commands)

### 3. Existing Pipeline Processor Unchanged

The core validation logic in `utils/pipeline_processor.py` is already well-abstracted:
- `validate_all_images()` works with `SpecificImage` objects
- `classify_validation_status()` categorizes results
- `load_pipeline_config()` parses pipeline definitions

We add a thin adapter layer (`pipeline_analyzer.py`) that:
1. Converts `FileInfo` to `ImageGroups` via shared `build_imagegroups()`
2. Flattens to `SpecificImage` objects
3. Calls existing validation logic

## Data Flow

### Photo Pairing

```
FileInfo[] ──► build_imagegroups() ──► ImageGroup[] ──► calculate_analytics() ──► Results
```

### PhotoStats

```
FileInfo[] ──► calculate_stats() ──► Stats
FileInfo[] ──► analyze_pairing() ──► Pairing Results
```

### Pipeline Validation

```
FileInfo[] ──► build_imagegroups() ──► ImageGroup[]
                      ↓
          flatten_imagegroups_to_specific_images()
                      ↓
              SpecificImage[]
                      ↓
          add_metadata_files() (XMP files)
                      ↓
          validate_all_images() (from pipeline_processor)
                      ↓
              ValidationResult[]
                      ↓
          classify_validation_status()
                      ↓
                  Results
```

## Integration Points

### CLI Tools (Transitional)

Until fully deprecated, CLI tools can import from agent:

```python
import sys
sys.path.insert(0, str(Path(__file__).parent / 'agent'))

from src.remote.local_adapter import LocalAdapter
from src.analysis.photo_pairing_analyzer import build_imagegroups
```

### job_executor.py

Simplified to use shared modules:

```python
from src.analysis import build_imagegroups, calculate_analytics, run_pipeline_validation
from src.remote import LocalAdapter

async def _run_photo_pairing_remote(self, ...):
    adapter = self._get_storage_adapter(connector)
    files = adapter.list_files_with_metadata(path)
    result = build_imagegroups([f for f in files if f.extension in photo_exts])
    # Results identical to local
```

## Output Consistency Guarantee

### Golden Standard: LOCAL Collection Processing

The **current LOCAL collection processing** by the agent is the reference implementation that produces correct results:
- Correct ImageGroup structure with proper separate_image identification
- Accurate camera usage counts (images per camera, not files)
- Proper processing method tracking
- Complete pipeline validation (not just extension checking)

### Deprecated: Current REMOTE Implementations

The current REMOTE collection implementations in job_executor.py have defects:

| Tool | Current Remote Defect |
|------|----------------------|
| Photo Pairing | Wrong image counting, reimplemented algorithm inline |
| PhotoStats | Duplicated pairing logic, different code path |
| Pipeline Validation | **Stub only** - just checks file extensions exist |

### After Refactoring

| Output | Guarantee |
|--------|-----------|
| **JSON Results** | Identical structure and values for LOCAL and REMOTE |
| **HTML Reports** | Same Jinja2 template renders identical content |
| **Analysis Logic** | Single implementation used by both paths |
| **Behavior** | No behavioral differences between collection types |

The shared analysis modules extract the correct logic from LOCAL processing and make it available to both LOCAL and REMOTE collections through the unified `FileInfo` interface.
