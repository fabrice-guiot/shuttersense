# FileInfo Contract

## Overview

`FileInfo` is the unified file information interface that all storage adapters produce. It provides a consistent contract for analysis modules regardless of whether files are local or remote.

## Location

**Canonical source:** `agent/src/remote/base.py`

## Interface Definition

```python
from dataclasses import dataclass
from typing import Optional
from pathlib import Path
from datetime import datetime


@dataclass
class FileInfo:
    """
    Unified file information for both local and remote files.

    This dataclass provides a storage-agnostic representation of file metadata.
    All storage adapters (Local, S3, GCS, SMB) produce List[FileInfo] with
    the same structure, enabling unified analysis logic.

    Attributes:
        path: Relative path from collection root (e.g., "photos/2024/IMG_001.dng")
        size: File size in bytes
        last_modified: ISO 8601 timestamp string (optional)

    Properties:
        name: Filename without directory (like Path.name)
        extension: File extension with dot, lowercase (like Path.suffix.lower())
        stem: Filename without extension (like Path.stem)
    """
    path: str
    size: int
    last_modified: Optional[str] = None

    @property
    def name(self) -> str:
        """
        Filename without directory.

        Examples:
            "photos/2024/IMG_001.dng" -> "IMG_001.dng"
            "IMG_001.dng" -> "IMG_001.dng"
        """
        return self.path.rsplit('/', 1)[-1] if '/' in self.path else self.path

    @property
    def extension(self) -> str:
        """
        File extension with dot, lowercase.

        Examples:
            "IMG_001.DNG" -> ".dng"
            "IMG_001.CR3" -> ".cr3"
            "README" -> ""
        """
        name = self.name
        parts = name.rsplit('.', 1)
        return f".{parts[-1].lower()}" if len(parts) > 1 else ""

    @property
    def stem(self) -> str:
        """
        Filename without extension.

        Examples:
            "IMG_001.dng" -> "IMG_001"
            "AB3D0001-HDR.dng" -> "AB3D0001-HDR"
        """
        name = self.name
        return name.rsplit('.', 1)[0] if '.' in name else name

    @classmethod
    def from_path_object(cls, file_path: Path, base_path: Path) -> "FileInfo":
        """
        Create FileInfo from pathlib.Path (for local files).

        Args:
            file_path: Absolute path to the file
            base_path: Collection root path for relative path calculation

        Returns:
            FileInfo with path relative to base_path
        """
        stat = file_path.stat()
        return cls(
            path=str(file_path.relative_to(base_path)),
            size=stat.st_size,
            last_modified=datetime.fromtimestamp(stat.st_mtime).isoformat()
        )
```

## Adapter Implementations

### LocalAdapter

```python
def list_files_with_metadata(self, location: str) -> List[FileInfo]:
    folder = Path(location)
    files = []
    for file_path in folder.rglob('*'):
        if file_path.is_file():
            files.append(FileInfo.from_path_object(file_path, folder))
    return files
```

### S3Adapter

```python
def list_files_with_metadata(self, location: str) -> List[FileInfo]:
    # Uses list_objects_v2 which returns Size and LastModified
    for obj in response["Contents"]:
        files.append(FileInfo(
            path=obj["Key"],
            size=obj["Size"],
            last_modified=obj["LastModified"].isoformat()
        ))
    return files
```

### GCSAdapter

```python
def list_files_with_metadata(self, location: str) -> List[FileInfo]:
    # Uses blob.size and blob.updated
    for blob in blobs:
        files.append(FileInfo(
            path=blob.name,
            size=blob.size,
            last_modified=blob.updated.isoformat()
        ))
    return files
```

### SMBAdapter

```python
def list_files_with_metadata(self, location: str) -> List[FileInfo]:
    # Uses stat() for size and mtime
    for file_path in self._list_directory_recursive(path):
        file_stat = stat(file_path)
        files.append(FileInfo(
            path=relative_path,
            size=file_stat.st_size,
            last_modified=datetime.fromtimestamp(file_stat.st_mtime).isoformat()
        ))
    return files
```

## Usage in Analysis Modules

### Filtering by Extension

```python
photo_extensions = {'.dng', '.cr3', '.tiff'}
photo_files = [f for f in files if f.extension in photo_extensions]
```

### Grouping by Stem (for pairing analysis)

```python
from collections import defaultdict

file_groups = defaultdict(list)
for f in files:
    file_groups[f.stem].append(f)
```

### Extracting Filename for Parsing

```python
from utils.filename_parser import FilenameParser

for file_info in files:
    is_valid, error = FilenameParser.validate_filename(file_info.name)
    if is_valid:
        parsed = FilenameParser.parse_filename(file_info.name)
```

## Migration Notes

### Backend FileInfo (Deprecated)

The backend has a separate `FileInfo` in `backend/src/utils/file_listing.py`:

```python
@dataclass
class FileInfo:
    path: str
    size: int
    name: str       # Stored field (vs computed property)
    extension: str  # Stored field (vs computed property)
```

This will be deprecated in favor of the agent's `FileInfo`. The backend can import from agent or use a compatibility shim.

### Agent Remote FileInfo (Enhanced)

The existing `FileInfo` in `agent/src/remote/base.py` is enhanced with:
- `name` property (computed)
- `extension` property (computed)
- `stem` property (computed)
- `from_path_object()` classmethod

Existing remote adapters continue to work unchanged - they already populate `path`, `size`, and `last_modified`.
