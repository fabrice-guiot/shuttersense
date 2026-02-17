"""
Configuration loader for agent job execution.

Fetches tool configuration from the server for job execution.
Also provides a DictConfigLoader for use with tools that accept
configuration dictionaries.

Issue #90 - Distributed Agent Architecture (Phase 5)
Tasks: T095, T101
"""

import logging
from typing import Dict, List, Any, Optional

from src.api_client import AgentApiClient


logger = logging.getLogger("shuttersense.agent.config")


class ApiConfigLoader:
    """
    Configuration loader that fetches from the server API.

    Fetches job-specific configuration from the server and caches it
    for the duration of job execution.

    Attributes:
        api_client: API client for server communication
        job_guid: GUID of the job to fetch config for
    """

    def __init__(self, api_client: AgentApiClient, job_guid: str):
        """
        Initialize the API config loader.

        Args:
            api_client: API client for server communication
            job_guid: GUID of the job to fetch config for
        """
        self._api_client = api_client
        self._job_guid = job_guid
        self._config_cache: Optional[Dict[str, Any]] = None

    async def load(self) -> Dict[str, Any]:
        """
        Load configuration from the server.

        Returns:
            Configuration dictionary with:
            - photo_extensions
            - metadata_extensions
            - camera_mappings
            - processing_methods
            - require_sidecar
            - collection_path (if applicable)
            - pipeline_guid (if applicable)
            - pipeline (if applicable) - dict with guid, name, nodes, edges
        """
        if self._config_cache is not None:
            return self._config_cache

        logger.debug(f"Fetching config for job {self._job_guid}")

        response = await self._api_client.get_job_config(self._job_guid)

        # Extract config from response
        config_data = response.get("config", {})

        # Remap server field name 'cameras' → 'camera_mappings' used by agent code
        if "cameras" in config_data and "camera_mappings" not in config_data:
            config_data["camera_mappings"] = config_data.pop("cameras")

        # Add job-specific fields
        config_data["collection_path"] = response.get("collection_path")
        config_data["pipeline_guid"] = response.get("pipeline_guid")
        config_data["pipeline"] = response.get("pipeline")  # Pipeline definition (nodes, edges)
        config_data["connector"] = response.get("connector")  # Connector info for remote collection tests

        self._config_cache = config_data

        logger.debug(f"Config loaded for job {self._job_guid}")

        return config_data


class DictConfigLoader:
    """
    Configuration loader that uses a pre-loaded dictionary.

    Used for passing configuration to tools that expect a ConfigLoader
    interface but we already have the config as a dictionary.

    Attributes:
        config: Configuration dictionary
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize with a configuration dictionary.

        Args:
            config: Configuration dictionary
        """
        self._config = config

    @property
    def photo_extensions(self) -> List[str]:
        """Get list of recognized photo file extensions."""
        return self._config.get('photo_extensions', [])

    @property
    def metadata_extensions(self) -> List[str]:
        """Get list of metadata file extensions."""
        return self._config.get('metadata_extensions', [])

    @property
    def camera_mappings(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get camera ID to camera info mappings."""
        return self._config.get('camera_mappings', {})

    @property
    def processing_methods(self) -> Dict[str, str]:
        """Get processing method code to description mappings."""
        return self._config.get('processing_methods', {})

    @property
    def require_sidecar(self) -> List[str]:
        """Get list of extensions that require sidecar files."""
        return self._config.get('require_sidecar', [])
