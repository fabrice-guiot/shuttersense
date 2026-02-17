"""
Input State service for computing collection state hashes.

Issue #92: Storage Optimization for Analysis Results
Issue #107 Phase 7: Server-Side No-Change Detection

Provides deterministic hash computation for Input State comparison.

The Input State hash is computed from:
1. File list hash: SHA-256 of sorted (relative_path, size, mtime) tuples
2. Configuration hash: SHA-256 of sorted tool configuration

This allows detecting when a collection has changed since the last analysis.

Phase 7 adds server-side detection for inventory-sourced FileInfo:
- Server can compute hash from Collection.file_info (inventory source)
- During job claim, server compares hash to previous result
- If match, job is auto-completed without sending to agent
"""

import hashlib
import json
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional, TYPE_CHECKING

from backend.src.utils.logging_config import get_logger

if TYPE_CHECKING:
    from backend.src.models import Collection

logger = get_logger("services")


class InputStateService:
    """
    Service for computing Input State hashes.

    The Input State uniquely identifies the state of a collection's files
    and tool configuration at a point in time. When two Input States match,
    the collection has not changed and analysis can be skipped.

    Usage:
        >>> service = InputStateService()
        >>> file_hash = service.compute_file_list_hash(files)
        >>> config_hash = service.compute_configuration_hash(config)
        >>> state_hash = service.compute_input_state_hash(file_hash, config_hash)
    """

    def compute_file_list_hash(
        self,
        files: List[Tuple[str, int, float]]
    ) -> str:
        """
        Compute SHA-256 hash of file list.

        The file list is sorted by path to ensure deterministic ordering.
        Each file is represented as (relative_path, size_bytes, mtime_timestamp).

        Args:
            files: List of (path, size, mtime) tuples

        Returns:
            64-character hex SHA-256 hash

        Example:
            >>> files = [
            ...     ("photos/IMG_001.dng", 25000000, 1704067200.0),
            ...     ("photos/IMG_001.xmp", 4096, 1704067201.0),
            ... ]
            >>> hash = service.compute_file_list_hash(files)
        """
        # Sort by path for deterministic ordering
        sorted_files = sorted(files, key=lambda f: f[0])

        # Build canonical representation
        # Format: "path|size|mtime\n" for each file
        lines = []
        for path, size, mtime in sorted_files:
            # Round mtime to integer to avoid floating point issues
            lines.append(f"{path}|{size}|{int(mtime)}")

        content = "\n".join(lines)

        # Compute SHA-256
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    # Configuration keys relevant for analysis hash computation
    # Must match agent/src/input_state.py _extract_relevant_config
    RELEVANT_CONFIG_KEYS = [
        "photo_extensions",
        "metadata_extensions",
        "require_sidecar",
        "cameras",
        "processing_methods",
        "pipeline",  # Pipeline rules affect validation
    ]

    def _extract_relevant_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract only analysis-relevant configuration keys.

        This ensures the hash only changes when analysis-affecting config changes,
        not when unrelated settings are modified.

        Must stay in sync with agent/src/input_state.py _extract_relevant_config.
        """
        result = {k: config[k] for k in self.RELEVANT_CONFIG_KEYS if k in config}
        result["_hash_version"] = 2  # v2: results now include path_stats
        return result

    def compute_configuration_hash(
        self,
        configuration: Dict[str, Any]
    ) -> str:
        """
        Compute SHA-256 hash of tool configuration.

        Configuration is serialized as sorted JSON to ensure deterministic output.
        Only relevant configuration keys are included to prevent hash changes from
        irrelevant config changes.

        Args:
            configuration: Tool configuration dictionary

        Returns:
            64-character hex SHA-256 hash

        Example:
            >>> config = {
            ...     "photo_extensions": [".dng", ".cr3"],
            ...     "require_sidecar": [".cr3"],
            ... }
            >>> hash = service.compute_configuration_hash(config)
        """
        # Extract only analysis-relevant configuration
        # This prevents hash changes from irrelevant config changes
        relevant_config = self._extract_relevant_config(configuration)

        # Serialize with sorted keys for determinism
        content = json.dumps(relevant_config, sort_keys=True, separators=(",", ":"))

        # Compute SHA-256
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def compute_input_state_hash(
        self,
        file_list_hash: str,
        configuration_hash: str,
        tool: Optional[str] = None
    ) -> str:
        """
        Compute combined Input State hash.

        Combines file list hash and configuration hash into a single
        Input State hash. Optionally includes tool name for extra specificity.

        Args:
            file_list_hash: Hash from compute_file_list_hash()
            configuration_hash: Hash from compute_configuration_hash()
            tool: Optional tool name to include in hash

        Returns:
            64-character hex SHA-256 hash

        Example:
            >>> state_hash = service.compute_input_state_hash(
            ...     file_hash, config_hash, tool="photostats"
            ... )
        """
        # Combine hashes with separator
        if tool:
            content = f"{tool}|{file_list_hash}|{configuration_hash}"
        else:
            content = f"{file_list_hash}|{configuration_hash}"

        # Compute SHA-256
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def compute_input_state_json(
        self,
        files: List[Tuple[str, int, float]],
        configuration: Dict[str, Any],
        tool: Optional[str] = None
    ) -> str:
        """
        Compute Input State as JSON for debugging.

        Returns the full Input State as a JSON string, useful for
        troubleshooting hash mismatches.

        Args:
            files: List of (path, size, mtime) tuples
            configuration: Tool configuration dictionary
            tool: Optional tool name

        Returns:
            JSON string representation of Input State
        """
        # Sort files for deterministic ordering
        sorted_files = sorted(files, key=lambda f: f[0])

        # Extract only relevant config (same as hash computation)
        relevant_config = self._extract_relevant_config(configuration)

        state = {
            "tool": tool,
            "file_count": len(sorted_files),
            "files": [
                {"path": p, "size": s, "mtime": int(m)}
                for p, s, m in sorted_files
            ],
            "configuration": relevant_config,
        }

        return json.dumps(state, sort_keys=True, indent=2)


    # =========================================================================
    # Phase 7: Server-Side No-Change Detection (Issue #107)
    # =========================================================================

    def compute_inventory_file_hash(
        self,
        file_info: List[Dict[str, Any]]
    ) -> str:
        """
        Compute SHA-256 hash from inventory-sourced FileInfo.

        Converts inventory FileInfo format (key, size, last_modified) to the
        same format used by agent-side file list hashing for compatibility.

        Note: S3/GCS inventory keys are URL-encoded (e.g., %20 for space).
        The agent URL-decodes these keys before hashing, so we must do the same
        to ensure hash compatibility.

        Args:
            file_info: List of FileInfo dicts from Collection.file_info
                       Each dict has: key, size, last_modified, etag?, storage_class?

        Returns:
            64-character hex SHA-256 hash

        Example:
            >>> file_info = [
            ...     {"key": "2020/IMG_001.dng", "size": 25000000, "last_modified": "2022-11-25T13:30:49.000Z"},
            ...     {"key": "2020/IMG_001.xmp", "size": 4096, "last_modified": "2022-11-25T13:30:50.000Z"},
            ... ]
            >>> hash = service.compute_inventory_file_hash(file_info)
        """
        from urllib.parse import unquote

        # Convert inventory FileInfo to (path, size, mtime) tuples
        # This matches the agent-side format for compatibility
        files: List[Tuple[str, int, float]] = []
        for fi in file_info:
            key = fi.get("key", "")
            size = fi.get("size", 0)
            last_modified = fi.get("last_modified", "")

            # URL-decode the key to match agent-side behavior
            # (S3/GCS inventory keys are URL-encoded, agent decodes them)
            decoded_key = unquote(key)

            # Parse ISO8601 timestamp to Unix timestamp
            mtime = self._parse_iso8601_to_timestamp(last_modified)
            if mtime is not None:
                files.append((decoded_key, size, mtime))

        # Use existing file list hash computation
        return self.compute_file_list_hash(files)

    def _parse_iso8601_to_timestamp(self, iso_string: str) -> Optional[float]:
        """
        Parse ISO8601 timestamp to Unix timestamp.

        Handles various ISO8601 formats including:
        - 2022-11-25T13:30:49.000Z
        - 2022-11-25T13:30:49Z
        - 2022-11-25T13:30:49+00:00

        Args:
            iso_string: ISO8601 formatted timestamp string

        Returns:
            Unix timestamp as float, or None if parsing fails
        """
        if not iso_string:
            return None

        try:
            # Try standard ISO format with Z suffix
            if iso_string.endswith("Z"):
                # Remove Z and parse
                dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
            else:
                dt = datetime.fromisoformat(iso_string)

            return dt.timestamp()
        except (ValueError, TypeError):
            logger.warning(f"Failed to parse ISO8601 timestamp: {iso_string}")
            return None

    def can_compute_server_side_hash(
        self,
        collection: "Collection"
    ) -> bool:
        """
        Check if server-side hash computation is possible for a collection.

        Server-side detection is only possible when:
        1. Collection has file_info data
        2. file_info_source is "inventory" (not "api" or null)

        Args:
            collection: Collection model instance

        Returns:
            True if server-side hash computation is possible
        """
        if collection is None:
            return False

        if not collection.file_info:
            return False

        # Only compute hash for inventory-sourced FileInfo
        # API-sourced or null means agent must compute hash from actual files
        return collection.file_info_source == "inventory"

    def compute_collection_input_state_hash(
        self,
        collection: "Collection",
        configuration: Dict[str, Any],
        tool: str
    ) -> Optional[str]:
        """
        Compute Input State hash for a collection using server-side data.

        This is the main entry point for server-side no-change detection.
        Returns None if server-side computation is not possible.

        Args:
            collection: Collection with file_info from inventory
            configuration: Tool configuration dictionary
            tool: Tool name (e.g., "photostats", "photo_pairing")

        Returns:
            64-character hex SHA-256 hash, or None if computation not possible
        """
        if not self.can_compute_server_side_hash(collection):
            return None

        # Compute file hash from inventory FileInfo
        file_hash = self.compute_inventory_file_hash(collection.file_info)

        # Compute configuration hash
        config_hash = self.compute_configuration_hash(configuration)

        # Combine into final Input State hash
        return self.compute_input_state_hash(file_hash, config_hash, tool)


# Module-level singleton for convenience
_service: Optional[InputStateService] = None


def get_input_state_service() -> InputStateService:
    """Get or create the InputStateService singleton."""
    global _service
    if _service is None:
        _service = InputStateService()
    return _service
