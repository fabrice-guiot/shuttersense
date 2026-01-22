# Implementation Guide

## Implementation Phases

### Phase 1: Enhance Agent's FileInfo

**File:** `agent/src/remote/base.py`

Add computed properties to existing FileInfo dataclass:

```python
@dataclass
class FileInfo:
    """Unified file information for both local and remote files."""
    path: str
    size: int
    last_modified: Optional[str] = None

    @property
    def name(self) -> str:
        """Filename without directory (like Path.name)."""
        return self.path.rsplit('/', 1)[-1] if '/' in self.path else self.path

    @property
    def extension(self) -> str:
        """Extension with dot, lowercase (e.g., '.dng')."""
        name = self.name
        parts = name.rsplit('.', 1)
        return f".{parts[-1].lower()}" if len(parts) > 1 else ""

    @property
    def stem(self) -> str:
        """Filename without extension (like Path.stem)."""
        name = self.name
        return name.rsplit('.', 1)[0] if '.' in name else name

    @classmethod
    def from_path_object(cls, file_path: Path, base_path: Path) -> "FileInfo":
        """Create FileInfo from pathlib.Path (for local files)."""
        from datetime import datetime
        stat = file_path.stat()
        return cls(
            path=str(file_path.relative_to(base_path)),
            size=stat.st_size,
            last_modified=datetime.fromtimestamp(stat.st_mtime).isoformat()
        )
```

**Tests:** Add unit tests for computed properties.

---

### Phase 2: Create LocalAdapter

**New file:** `agent/src/remote/local_adapter.py`

```python
"""
Local filesystem storage adapter.

Implements StorageAdapter interface for local directories,
enabling unified processing with remote collections.
"""
from pathlib import Path
from typing import List, Tuple

from src.remote.base import StorageAdapter, FileInfo


class LocalAdapter(StorageAdapter):
    """Local filesystem adapter."""

    def __init__(self, credentials: dict):
        """Initialize (credentials not needed for local)."""
        super().__init__(credentials)

    def list_files(self, location: str) -> List[str]:
        """List all files in local directory."""
        folder = Path(location)
        files = []
        for file_path in folder.rglob('*'):
            if file_path.is_file():
                files.append(str(file_path.relative_to(folder)))
        return files

    def list_files_with_metadata(self, location: str) -> List[FileInfo]:
        """List all files with metadata in local directory."""
        folder = Path(location)
        files = []
        for file_path in folder.rglob('*'):
            if file_path.is_file():
                files.append(FileInfo.from_path_object(file_path, folder))
        return files

    def test_connection(self) -> Tuple[bool, str]:
        """Test filesystem access."""
        return True, "Local filesystem access available"
```

**Update:** `agent/src/remote/__init__.py` to export LocalAdapter.

**Tests:** `agent/tests/unit/test_local_adapter.py`

---

### Phase 3: Create Shared Analysis Modules

**New directory:** `agent/src/analysis/`

Create four files:
1. `__init__.py` - exports
2. `photo_pairing_analyzer.py` - from photo_pairing.py
3. `photostats_analyzer.py` - from photo_stats.py
4. `pipeline_analyzer.py` - new unified entry point

See [03-analysis-modules.md](./03-analysis-modules.md) for full specifications.

**Tests:**
- `agent/tests/unit/test_photo_pairing_analyzer.py`
- `agent/tests/unit/test_photostats_analyzer.py`
- `agent/tests/unit/test_pipeline_analyzer.py`

---

### Phase 4: Refactor job_executor.py

**File:** `agent/src/job_executor.py`

#### Step 4.1: Add imports

```python
from src.analysis import (
    build_imagegroups, calculate_analytics,
    analyze_pairing, calculate_stats,
    run_pipeline_validation
)
```

#### Step 4.2: Refactor `_run_photo_pairing_remote()`

Replace inline analysis (~90 lines) with:

```python
async def _run_photo_pairing_remote(self, collection_path, config, connector):
    adapter = self._get_storage_adapter(connector)
    normalized_path = self._normalize_remote_path(collection_path, connector.get("type", ""))

    # List files with metadata
    start_time = time.time()
    all_files = adapter.list_files_with_metadata(normalized_path)

    # Filter to photo extensions
    photo_exts = set(config.get('photo_extensions', []))
    photo_files = [f for f in all_files if f.extension in photo_exts]

    # Use shared analysis
    result = build_imagegroups(photo_files)
    analytics = calculate_analytics(result['imagegroups'], config)

    results = {
        'group_count': analytics['group_count'],
        'image_count': analytics['image_count'],
        'file_count': len(photo_files),
        'camera_usage': analytics['camera_usage'],
        'method_usage': analytics['method_usage'],
        'invalid_files_count': len(result['invalid_files']),
        'scan_time': time.time() - start_time,
    }
    # Generate report...
```

#### Step 4.3: Refactor `_run_photostats_remote()`

Replace `_process_photostats_files()` with shared functions:

```python
async def _run_photostats_remote(self, collection_path, config, connector):
    adapter = self._get_storage_adapter(connector)
    all_files = adapter.list_files_with_metadata(normalized_path)

    photo_exts = set(config.get('photo_extensions', []))
    metadata_exts = set(config.get('metadata_extensions', []))
    require_sidecar = set(config.get('require_sidecar', []))

    # Use shared analysis
    stats = calculate_stats(all_files, photo_exts, metadata_exts)
    pairing = analyze_pairing(all_files, photo_exts, metadata_exts, require_sidecar)

    results = {**stats, **pairing, 'scan_time': elapsed_time}
    # Generate report...
```

#### Step 4.4: Refactor `_run_pipeline_validation_remote()`

Replace stub implementation (~50 lines) with:

```python
async def _run_pipeline_validation_remote(self, collection_path, pipeline_guid, config, connector):
    adapter = self._get_storage_adapter(connector)
    all_files = adapter.list_files_with_metadata(normalized_path)

    photo_exts = set(config.get('photo_extensions', []))
    metadata_exts = set(config.get('metadata_extensions', []))
    pipeline_def = config.get('pipeline', {})

    # Use shared analysis (full validation, not stub)
    results = run_pipeline_validation(
        files=all_files,
        pipeline_config=pipeline_def,
        photo_extensions=photo_exts,
        metadata_extensions=metadata_exts
    )

    results['pipeline_guid'] = pipeline_guid
    results['pipeline_name'] = pipeline_def.get('name', 'Unknown')
    results['scan_time'] = elapsed_time

    # Generate report...
```

#### Step 4.5: Delete unused methods

- Remove `_process_photostats_files()` (~90 lines)
- Remove inline analysis from `_run_photo_pairing_remote()` (~90 lines)
- Remove stub logic from `_run_pipeline_validation_remote()` (~50 lines)

---

### Phase 5: Update CLI Tools (Transitional)

**Optional** - CLI tools will be deprecated, but can be updated for consistency:

```python
# photo_pairing.py
import sys
sys.path.insert(0, str(Path(__file__).parent / 'agent'))

from src.remote.local_adapter import LocalAdapter
from src.analysis.photo_pairing_analyzer import build_imagegroups, calculate_analytics
```

---

### Phase 6: Deprecate Backend File Listing

**Optional/Later** - Add deprecation warning to `backend/src/utils/file_listing.py`.

---

## Output Consistency Guarantee

After implementation, LOCAL and REMOTE collections produce **identical**:
- JSON result structure and values
- HTML report content (same Jinja2 template)
- Analysis behavior

**Golden Standard:** LOCAL collection processing is correct and serves as the specification.

**Deprecated:** Current REMOTE implementations (duplicated/stub code) will be replaced entirely with calls to shared analysis modules.

---

## Verification Checklist

### Unit Tests

- [ ] FileInfo properties work correctly (name, extension, stem)
- [ ] FileInfo.from_path_object() creates correct instance
- [ ] LocalAdapter.list_files_with_metadata() returns correct FileInfo list
- [ ] build_imagegroups() produces correct structure
- [ ] calculate_analytics() resolves camera/method names
- [ ] analyze_pairing() detects orphaned files correctly
- [ ] run_pipeline_validation() returns correct status counts

### Integration Tests

- [ ] Photo Pairing: LOCAL collection produces same results as REMOTE
- [ ] PhotoStats: LOCAL collection produces same results as REMOTE
- [ ] Pipeline Validation: LOCAL collection produces same results as REMOTE

### Regression Tests

- [ ] Existing agent tests pass
- [ ] Existing CLI tests pass

### Manual Verification

- [ ] Photo Pairing on 372-file remote collection: 186 groups, 186 images
- [ ] Camera names resolved from config (not raw IDs)
- [ ] Method descriptions resolved from config
- [ ] Pipeline Validation shows proper status counts
- [ ] HTML reports render correctly

---

## Rollback Plan

If issues are discovered:

1. **Phase 4 rollback:** Revert job_executor.py changes, keep analysis modules
2. **Full rollback:** Revert all changes, analysis modules are self-contained

The analysis modules are additive - they don't break existing code until job_executor.py is updated to use them.
