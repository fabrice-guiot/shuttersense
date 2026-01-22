"""
Agent system metrics collection.

Collects system resource metrics (CPU, memory, disk) for reporting
to the server during heartbeat. Uses psutil when available, with
graceful fallback when not installed.

Issue #90 - Distributed Agent Architecture (Phase 11)
Task: T171 - Collect and report system metrics in agent
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("shuttersense.agent")


# ============================================================================
# Check for psutil availability
# ============================================================================

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    logger.debug("psutil not installed - system metrics will not be collected")


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class SystemMetrics:
    """
    Container for system resource metrics.

    Attributes:
        cpu_percent: CPU usage percentage (0-100), None if unavailable
        memory_percent: Memory usage percentage (0-100), None if unavailable
        disk_free_gb: Free disk space in GB, None if unavailable
    """
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    disk_free_gb: Optional[float] = None

    def to_dict(self) -> dict:
        """
        Convert to dictionary for API transmission.

        Only includes non-None values.

        Returns:
            Dictionary with metric values
        """
        result = {}
        if self.cpu_percent is not None:
            result["cpu_percent"] = round(self.cpu_percent, 1)
        if self.memory_percent is not None:
            result["memory_percent"] = round(self.memory_percent, 1)
        if self.disk_free_gb is not None:
            result["disk_free_gb"] = round(self.disk_free_gb, 2)
        return result

    @property
    def is_empty(self) -> bool:
        """Check if no metrics were collected."""
        return (
            self.cpu_percent is None and
            self.memory_percent is None and
            self.disk_free_gb is None
        )


# ============================================================================
# Metrics Collector
# ============================================================================

class MetricsCollector:
    """
    Collects system resource metrics.

    Uses psutil when available for accurate metrics. Falls back to
    returning empty metrics when psutil is not installed.

    Usage:
        >>> collector = MetricsCollector()
        >>> metrics = collector.collect()
        >>> if not metrics.is_empty:
        ...     print(f"CPU: {metrics.cpu_percent}%")
    """

    def __init__(self, disk_path: str = "/"):
        """
        Initialize the metrics collector.

        Args:
            disk_path: Path to check for disk space (default: root)
        """
        self._disk_path = disk_path

    def collect(self) -> SystemMetrics:
        """
        Collect current system metrics.

        Returns:
            SystemMetrics with current values, or empty if collection fails
        """
        if not HAS_PSUTIL:
            return SystemMetrics()

        return SystemMetrics(
            cpu_percent=self._get_cpu_percent(),
            memory_percent=self._get_memory_percent(),
            disk_free_gb=self._get_disk_free_gb(),
        )

    def _get_cpu_percent(self) -> Optional[float]:
        """
        Get CPU usage percentage.

        Uses psutil.cpu_percent with a 0.1 second interval for accuracy.
        On the first call, this may return 0.0 as it needs to compare
        two measurements.

        Returns:
            CPU percentage (0-100) or None on error
        """
        try:
            # Use a small interval for non-blocking call
            # interval=None would be blocking and inaccurate on first call
            return psutil.cpu_percent(interval=0.1)
        except Exception as e:
            logger.debug(f"Failed to get CPU percent: {e}")
            return None

    def _get_memory_percent(self) -> Optional[float]:
        """
        Get memory usage percentage.

        Returns:
            Memory percentage (0-100) or None on error
        """
        try:
            memory = psutil.virtual_memory()
            return memory.percent
        except Exception as e:
            logger.debug(f"Failed to get memory percent: {e}")
            return None

    def _get_disk_free_gb(self) -> Optional[float]:
        """
        Get free disk space in GB.

        Args:
            path: Path to check (uses disk_path from init)

        Returns:
            Free disk space in GB or None on error
        """
        try:
            disk = psutil.disk_usage(self._disk_path)
            # Convert bytes to GB
            return disk.free / (1024 ** 3)
        except Exception as e:
            logger.debug(f"Failed to get disk free space: {e}")
            return None


# ============================================================================
# Module-level functions
# ============================================================================

# Default collector instance
_default_collector: Optional[MetricsCollector] = None


def get_default_collector() -> MetricsCollector:
    """
    Get or create the default metrics collector.

    Returns:
        The default MetricsCollector instance
    """
    global _default_collector
    if _default_collector is None:
        _default_collector = MetricsCollector()
    return _default_collector


def collect_metrics(disk_path: str = "/") -> SystemMetrics:
    """
    Convenience function to collect metrics.

    Args:
        disk_path: Path to check for disk space

    Returns:
        SystemMetrics with current values
    """
    collector = MetricsCollector(disk_path=disk_path)
    return collector.collect()


def is_metrics_available() -> bool:
    """
    Check if metrics collection is available.

    Returns:
        True if psutil is installed and metrics can be collected
    """
    return HAS_PSUTIL
