"""
Input State computation for no-change detection.

Issue #92: Storage Optimization for Analysis Results
Computes deterministic hashes of collection state (files + configuration)
to detect when a collection has not changed since the last analysis.

The Input State hash is computed from:
1. File list hash: SHA-256 of sorted (relative_path, size, mtime) tuples
2. Configuration hash: SHA-256 of sorted tool configuration

When the Input State hash matches the previous result's hash, the collection
has not changed and execution can be skipped.
"""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

from src.remote.base import FileInfo


logger = logging.getLogger("shuttersense.agent.input_state")


class InputStateComputer:
    """
    Computes Input State hashes for no-change detection.

    Supports both local files and remote FileInfo objects from storage adapters.

    Usage:
        >>> computer = InputStateComputer()
        >>> # From local files
        >>> file_hash = computer.compute_file_list_hash_from_path("/path/to/collection")
        >>> # From remote FileInfo list
        >>> file_hash = computer.compute_file_list_hash_from_file_info(file_info_list)
        >>> config_hash = computer.compute_configuration_hash(config)
        >>> state_hash = computer.compute_input_state_hash(file_hash, config_hash, tool)
    """

    def compute_file_list_hash_from_path(
        self,
        collection_path: str,
        extensions: Optional[List[str]] = None
    ) -> Tuple[str, int]:
        """
        Compute file list hash by scanning a local directory.

        Args:
            collection_path: Path to the collection directory
            extensions: Optional list of extensions to filter (e.g., [".dng", ".xmp"])

        Returns:
            Tuple of (hash, file_count)
        """
        path = Path(collection_path)
        files: List[Tuple[str, int, int]] = []

        for file_path in path.rglob("*"):
            if not file_path.is_file():
                continue

            # Filter by extension if specified
            if extensions and file_path.suffix.lower() not in extensions:
                continue

            try:
                stat = file_path.stat()
                relative_path = str(file_path.relative_to(path))
                files.append((relative_path, stat.st_size, int(stat.st_mtime)))
            except (OSError, ValueError) as e:
                logger.warning(f"Failed to stat file {file_path}: {e}")
                continue

        return self._compute_file_list_hash(files), len(files)

    def compute_file_list_hash_from_file_info(
        self,
        file_infos: List[FileInfo]
    ) -> Tuple[str, int]:
        """
        Compute file list hash from a list of FileInfo objects.

        Used for remote collections where file metadata comes from storage adapters.

        Args:
            file_infos: List of FileInfo objects from storage adapter

        Returns:
            Tuple of (hash, file_count)
        """
        files: List[Tuple[str, int, int]] = []

        for info in file_infos:
            # Parse last_modified string to timestamp, or use 0 if not available
            mtime = 0
            if info.last_modified:
                try:
                    # ISO format string to timestamp
                    dt = datetime.fromisoformat(info.last_modified.replace("Z", "+00:00"))
                    mtime = int(dt.timestamp())
                except (ValueError, AttributeError):
                    pass
            files.append((info.path, info.size, mtime))

        return self._compute_file_list_hash(files), len(files)

    def _compute_file_list_hash(
        self,
        files: List[Tuple[str, int, int]]
    ) -> str:
        """
        Compute SHA-256 hash of file list.

        The file list is sorted by path to ensure deterministic ordering.
        Each file is represented as (relative_path, size_bytes, mtime_timestamp).

        Args:
            files: List of (path, size, mtime) tuples

        Returns:
            64-character hex SHA-256 hash
        """
        # Sort by path for deterministic ordering
        sorted_files = sorted(files, key=lambda f: f[0])

        # Build canonical representation
        # Format: "path|size|mtime\n" for each file
        lines = []
        for path, size, mtime in sorted_files:
            lines.append(f"{path}|{size}|{mtime}")

        content = "\n".join(lines)

        # Compute SHA-256
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def compute_configuration_hash(
        self,
        configuration: Dict[str, Any]
    ) -> str:
        """
        Compute SHA-256 hash of tool configuration.

        Configuration is serialized as sorted JSON to ensure deterministic output.
        Only relevant configuration keys are included (extensions, processing methods, etc.)

        Args:
            configuration: Tool configuration dictionary

        Returns:
            64-character hex SHA-256 hash
        """
        # Extract only analysis-relevant configuration
        # This prevents hash changes from irrelevant config changes
        relevant_config = self._extract_relevant_config(configuration)

        # Serialize with sorted keys for determinism
        content = json.dumps(relevant_config, sort_keys=True, separators=(",", ":"))

        # Compute SHA-256
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _extract_relevant_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract only analysis-relevant configuration keys.

        This ensures the hash only changes when analysis-affecting config changes,
        not when unrelated settings are modified.
        """
        relevant_keys = [
            "photo_extensions",
            "metadata_extensions",
            "require_sidecar",
            "cameras",
            "processing_methods",
            "pipeline",  # Pipeline rules affect validation
        ]

        return {k: config[k] for k in relevant_keys if k in config}

    def compute_input_state_hash(
        self,
        file_list_hash: str,
        configuration_hash: str,
        tool: str
    ) -> str:
        """
        Compute combined Input State hash.

        Combines file list hash, configuration hash, and tool name into
        a single Input State hash.

        Args:
            file_list_hash: Hash from compute_file_list_hash_*
            configuration_hash: Hash from compute_configuration_hash()
            tool: Tool name (photostats, photo_pairing, pipeline_validation)

        Returns:
            64-character hex SHA-256 hash
        """
        # Combine hashes with separator, including tool for specificity
        content = f"{tool}|{file_list_hash}|{configuration_hash}"

        # Compute SHA-256
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def compute_input_state_json(
        self,
        files: List[Tuple[str, int, int]],
        configuration: Dict[str, Any],
        tool: str
    ) -> str:
        """
        Compute Input State as JSON for debugging.

        Returns the full Input State as a JSON string, useful for
        troubleshooting hash mismatches.

        Args:
            files: List of (path, size, mtime) tuples
            configuration: Tool configuration dictionary
            tool: Tool name

        Returns:
            JSON string representation of Input State
        """
        # Sort files for deterministic ordering
        sorted_files = sorted(files, key=lambda f: f[0])
        relevant_config = self._extract_relevant_config(configuration)

        state = {
            "tool": tool,
            "file_count": len(sorted_files),
            "files": [
                {"path": p, "size": s, "mtime": m}
                for p, s, m in sorted_files
            ],
            "configuration": relevant_config,
        }

        return json.dumps(state, sort_keys=True, indent=2)


def check_no_change(
    previous_result: Optional[Dict[str, Any]],
    current_hash: str
) -> bool:
    """
    Check if the current Input State matches the previous result.

    Args:
        previous_result: Previous result from job claim (may be None or missing hash)
        current_hash: Current Input State hash

    Returns:
        True if hashes match (no change), False otherwise
    """
    if not previous_result:
        logger.debug("No previous result - cannot skip execution")
        return False

    previous_hash = previous_result.get("input_state_hash")
    if not previous_hash:
        logger.debug("Previous result has no input_state_hash - cannot skip execution")
        return False

    if previous_hash == current_hash:
        logger.info(
            "Input State hash matches previous result - collection unchanged",
            extra={
                "previous_result_guid": previous_result.get("guid"),
                "input_state_hash": current_hash[:16] + "...",
            }
        )
        return True

    logger.info(
        "Input State hash differs from previous result - collection changed",
        extra={
            "previous_result_guid": previous_result.get("guid"),
            "previous_hash": previous_hash[:16] + "...",
            "current_hash": current_hash[:16] + "...",
        }
    )
    return False


# Module-level singleton for convenience
_computer: Optional[InputStateComputer] = None


def get_input_state_computer() -> InputStateComputer:
    """Get or create the InputStateComputer singleton."""
    global _computer
    if _computer is None:
        _computer = InputStateComputer()
    return _computer
