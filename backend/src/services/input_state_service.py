"""
Input State service for computing collection state hashes.

Issue #92: Storage Optimization for Analysis Results
Provides deterministic hash computation for Input State comparison.

The Input State hash is computed from:
1. File list hash: SHA-256 of sorted (relative_path, size, mtime) tuples
2. Configuration hash: SHA-256 of sorted tool configuration

This allows detecting when a collection has changed since the last analysis.
"""

import hashlib
import json
from typing import List, Tuple, Dict, Any, Optional

from backend.src.utils.logging_config import get_logger


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
        return {k: config[k] for k in self.RELEVANT_CONFIG_KEYS if k in config}

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


# Module-level singleton for convenience
_service: Optional[InputStateService] = None


def get_input_state_service() -> InputStateService:
    """Get or create the InputStateService singleton."""
    global _service
    if _service is None:
        _service = InputStateService()
    return _service
