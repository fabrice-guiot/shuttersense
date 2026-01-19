"""
ConfigLoader protocol and implementations for tool configuration.

Provides a unified interface for loading tool configuration from different
sources (file, database, API). Used by tool execution services to access
camera mappings, file extensions, and processing methods.

The ConfigLoader protocol allows tools to be agnostic of where configuration
comes from - it could be a local file for CLI tools, or database records
for web-based execution.

Issue #90 - Distributed Agent Architecture (Phase 5)
Tasks: T071, T086, T087, T088
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class ConfigLoader(Protocol):
    """
    Protocol for loading tool configuration.

    This protocol defines the interface that any configuration loader must
    implement. Implementations can load from files, databases, APIs, etc.

    Properties:
        photo_extensions: List of recognized photo file extensions
        metadata_extensions: List of metadata file extensions (e.g., .xmp)
        camera_mappings: Dict mapping camera IDs to camera info
        processing_methods: Dict mapping method codes to descriptions
        require_sidecar: List of extensions that require sidecar files

    Example:
        >>> config: ConfigLoader = FileConfigLoader("config.yaml")
        >>> for ext in config.photo_extensions:
        ...     print(ext)
    """

    @property
    def photo_extensions(self) -> List[str]:
        """Get list of recognized photo file extensions."""
        ...

    @property
    def metadata_extensions(self) -> List[str]:
        """Get list of metadata file extensions."""
        ...

    @property
    def camera_mappings(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get camera ID to camera info mappings."""
        ...

    @property
    def processing_methods(self) -> Dict[str, str]:
        """Get processing method code to description mappings."""
        ...

    @property
    def require_sidecar(self) -> List[str]:
        """Get list of extensions that require sidecar files."""
        ...


class BaseConfigLoader(ABC):
    """
    Abstract base class for config loaders.

    Provides common functionality and enforces the ConfigLoader interface.
    Concrete implementations should inherit from this class.
    """

    @property
    @abstractmethod
    def photo_extensions(self) -> List[str]:
        """Get list of recognized photo file extensions."""
        pass

    @property
    @abstractmethod
    def metadata_extensions(self) -> List[str]:
        """Get list of metadata file extensions."""
        pass

    @property
    @abstractmethod
    def camera_mappings(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get camera ID to camera info mappings."""
        pass

    @property
    @abstractmethod
    def processing_methods(self) -> Dict[str, str]:
        """Get processing method code to description mappings."""
        pass

    @property
    @abstractmethod
    def require_sidecar(self) -> List[str]:
        """Get list of extensions that require sidecar files."""
        pass


class FileConfigLoader(BaseConfigLoader):
    """
    Config loader that reads from a YAML configuration file.

    Wraps the existing PhotoAdminConfig class to provide the ConfigLoader
    interface. Used for CLI tool execution and local agent configurations.

    Args:
        config_path: Optional path to config file. If None, uses default locations.

    Example:
        >>> loader = FileConfigLoader("/path/to/config.yaml")
        >>> print(loader.photo_extensions)
        ['.dng', '.cr3', '.tiff']
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the file config loader.

        Args:
            config_path: Optional path to YAML config file
        """
        from utils.config_manager import PhotoAdminConfig
        self._config = PhotoAdminConfig(config_path=config_path)

    @property
    def photo_extensions(self) -> List[str]:
        """Get list of recognized photo file extensions."""
        return self._config.photo_extensions

    @property
    def metadata_extensions(self) -> List[str]:
        """Get list of metadata file extensions."""
        return self._config.metadata_extensions

    @property
    def camera_mappings(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get camera ID to camera info mappings."""
        return self._config.camera_mappings

    @property
    def processing_methods(self) -> Dict[str, str]:
        """Get processing method code to description mappings."""
        return self._config.processing_methods

    @property
    def require_sidecar(self) -> List[str]:
        """Get list of extensions that require sidecar files."""
        return self._config.require_sidecar


class DatabaseConfigLoader(BaseConfigLoader):
    """
    Config loader that reads from database team settings.

    Loads configuration from the team's settings stored in the database.
    Used for server-side tool execution with team-specific configurations.

    Args:
        team_id: Team ID to load configuration for
        db: SQLAlchemy database session

    Note:
        Falls back to default values if team settings are not configured.
    """

    # Default values if not configured
    DEFAULT_PHOTO_EXTENSIONS = ['.dng', '.cr3', '.cr2', '.nef', '.arw', '.raf', '.tiff', '.tif', '.jpg', '.jpeg']
    DEFAULT_METADATA_EXTENSIONS = ['.xmp']
    DEFAULT_REQUIRE_SIDECAR = ['.cr3', '.cr2', '.nef', '.arw', '.raf']

    def __init__(self, team_id: int, db):
        """
        Initialize the database config loader.

        Args:
            team_id: Team ID to load configuration for
            db: SQLAlchemy database session
        """
        from sqlalchemy.orm import Session
        self._team_id = team_id
        self._db: Session = db
        self._config_cache: Optional[Dict[str, Any]] = None

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from database with caching.

        The Configuration model stores settings as individual rows:
        - category='extensions', key='photo_extensions' -> value_json=['.dng', ...]
        - category='extensions', key='metadata_extensions' -> value_json=['.xmp']
        - category='extensions', key='require_sidecar' -> value_json=['.cr3', ...]
        - category='cameras', key='AB3D' -> value_json={...}
        - category='processing_methods', key='HDR' -> value_json='High Dynamic Range'

        This method reconstructs the flat config dict expected by the loaders.
        """
        if self._config_cache is not None:
            return self._config_cache

        from backend.src.models import Configuration

        configs = self._db.query(Configuration).filter(
            Configuration.team_id == self._team_id
        ).all()

        result: Dict[str, Any] = {
            'camera_mappings': {},
            'processing_methods': {},
        }

        for config in configs:
            if config.category == 'extensions':
                # Direct mapping: key -> value_json
                result[config.key] = config.value_json
            elif config.category == 'cameras':
                # Camera mappings: key is camera ID, value is camera info
                # The camera_mappings structure expects a list of camera infos per ID
                camera_info = config.value_json
                if isinstance(camera_info, dict):
                    result['camera_mappings'][config.key] = [camera_info]
                elif isinstance(camera_info, list):
                    result['camera_mappings'][config.key] = camera_info
            elif config.category == 'processing_methods':
                # Processing methods: key is method code, value is description
                result['processing_methods'][config.key] = config.value_json

        self._config_cache = result
        return self._config_cache

    @property
    def photo_extensions(self) -> List[str]:
        """Get list of recognized photo file extensions."""
        config = self._load_config()
        return config.get('photo_extensions', self.DEFAULT_PHOTO_EXTENSIONS)

    @property
    def metadata_extensions(self) -> List[str]:
        """Get list of metadata file extensions."""
        config = self._load_config()
        return config.get('metadata_extensions', self.DEFAULT_METADATA_EXTENSIONS)

    @property
    def camera_mappings(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get camera ID to camera info mappings."""
        config = self._load_config()
        return config.get('camera_mappings', {})

    @property
    def processing_methods(self) -> Dict[str, str]:
        """Get processing method code to description mappings."""
        config = self._load_config()
        return config.get('processing_methods', {})

    @property
    def require_sidecar(self) -> List[str]:
        """Get list of extensions that require sidecar files."""
        config = self._load_config()
        return config.get('require_sidecar', self.DEFAULT_REQUIRE_SIDECAR)


class DictConfigLoader(BaseConfigLoader):
    """
    Config loader that uses a pre-loaded dictionary.

    Useful for testing, caching, or when configuration is already loaded
    from an API response.

    Args:
        config: Dictionary containing configuration values

    Example:
        >>> config_dict = {
        ...     'photo_extensions': ['.dng', '.cr3'],
        ...     'metadata_extensions': ['.xmp'],
        ...     'camera_mappings': {},
        ...     'processing_methods': {},
        ...     'require_sidecar': ['.cr3']
        ... }
        >>> loader = DictConfigLoader(config_dict)
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize with a configuration dictionary.

        Args:
            config: Dictionary containing configuration values
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
