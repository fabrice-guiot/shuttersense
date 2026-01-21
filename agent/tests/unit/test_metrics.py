"""
Unit tests for agent metrics collection.

Tests the MetricsCollector class and SystemMetrics dataclass.

Issue #90 - Distributed Agent Architecture (Phase 11)
Task: T170 - Unit tests for metrics collection
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.metrics import (
    SystemMetrics,
    MetricsCollector,
    collect_metrics,
    is_metrics_available,
    HAS_PSUTIL,
)


class TestSystemMetrics:
    """Tests for SystemMetrics dataclass."""

    def test_system_metrics_defaults(self):
        """Test SystemMetrics defaults to None values."""
        metrics = SystemMetrics()
        assert metrics.cpu_percent is None
        assert metrics.memory_percent is None
        assert metrics.disk_free_gb is None

    def test_system_metrics_with_values(self):
        """Test SystemMetrics with provided values."""
        metrics = SystemMetrics(
            cpu_percent=45.5,
            memory_percent=62.3,
            disk_free_gb=128.7
        )
        assert metrics.cpu_percent == 45.5
        assert metrics.memory_percent == 62.3
        assert metrics.disk_free_gb == 128.7

    def test_to_dict_excludes_none(self):
        """Test to_dict only includes non-None values."""
        metrics = SystemMetrics(cpu_percent=50.0)
        result = metrics.to_dict()

        assert result == {"cpu_percent": 50.0}
        assert "memory_percent" not in result
        assert "disk_free_gb" not in result

    def test_to_dict_includes_all_values(self):
        """Test to_dict includes all values when set."""
        metrics = SystemMetrics(
            cpu_percent=45.5,
            memory_percent=62.3,
            disk_free_gb=128.7
        )
        result = metrics.to_dict()

        assert result == {
            "cpu_percent": 45.5,
            "memory_percent": 62.3,
            "disk_free_gb": 128.7
        }

    def test_to_dict_rounds_values(self):
        """Test to_dict rounds values appropriately."""
        metrics = SystemMetrics(
            cpu_percent=45.5678,
            memory_percent=62.3456,
            disk_free_gb=128.78901
        )
        result = metrics.to_dict()

        # cpu and memory rounded to 1 decimal, disk to 2
        assert result["cpu_percent"] == 45.6
        assert result["memory_percent"] == 62.3
        assert result["disk_free_gb"] == 128.79

    def test_is_empty_when_all_none(self):
        """Test is_empty returns True when all values are None."""
        metrics = SystemMetrics()
        assert metrics.is_empty is True

    def test_is_empty_when_some_values(self):
        """Test is_empty returns False when any value is set."""
        metrics = SystemMetrics(cpu_percent=50.0)
        assert metrics.is_empty is False


class TestMetricsCollectorWithPsutil:
    """Tests for MetricsCollector when psutil is available."""

    @pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not installed")
    def test_collect_returns_metrics(self):
        """Test collect returns metrics when psutil is available."""
        collector = MetricsCollector()
        metrics = collector.collect()

        # Should return non-empty metrics
        assert not metrics.is_empty

        # CPU percent should be 0-100
        if metrics.cpu_percent is not None:
            assert 0 <= metrics.cpu_percent <= 100

        # Memory percent should be 0-100
        if metrics.memory_percent is not None:
            assert 0 <= metrics.memory_percent <= 100

        # Disk free should be non-negative
        if metrics.disk_free_gb is not None:
            assert metrics.disk_free_gb >= 0

    @pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not installed")
    def test_collect_with_custom_disk_path(self):
        """Test collect uses custom disk path."""
        collector = MetricsCollector(disk_path="/")
        metrics = collector.collect()

        # Should get disk metrics for root
        if metrics.disk_free_gb is not None:
            assert metrics.disk_free_gb >= 0


class TestMetricsCollectorMocked:
    """Tests for MetricsCollector with mocked psutil."""

    @pytest.mark.skipif(not HAS_PSUTIL, reason="psutil required for mocking tests")
    def test_collect_calls_psutil_functions(self):
        """Test collect calls all psutil functions."""
        with patch('psutil.cpu_percent', return_value=45.5), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:

            mock_memory_obj = Mock()
            mock_memory_obj.percent = 62.3
            mock_memory.return_value = mock_memory_obj
            mock_disk_obj = Mock()
            mock_disk_obj.free = 128.7 * (1024 ** 3)  # 128.7 GB in bytes
            mock_disk.return_value = mock_disk_obj

            collector = MetricsCollector()
            metrics = collector.collect()

            assert metrics.cpu_percent == 45.5
            assert metrics.memory_percent == 62.3
            assert 128.6 < metrics.disk_free_gb < 128.8  # Account for floating point

    @pytest.mark.skipif(not HAS_PSUTIL, reason="psutil required for mocking tests")
    def test_handles_cpu_error(self):
        """Test handles CPU percent error gracefully."""
        with patch('psutil.cpu_percent', side_effect=Exception("CPU error")), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:

            mock_memory_obj = Mock()
            mock_memory_obj.percent = 50.0
            mock_memory.return_value = mock_memory_obj
            mock_disk_obj = Mock()
            mock_disk_obj.free = 100 * (1024 ** 3)
            mock_disk.return_value = mock_disk_obj

            collector = MetricsCollector()
            metrics = collector.collect()

            assert metrics.cpu_percent is None
            assert metrics.memory_percent == 50.0
            assert metrics.disk_free_gb is not None

    @pytest.mark.skipif(not HAS_PSUTIL, reason="psutil required for mocking tests")
    def test_handles_memory_error(self):
        """Test handles memory percent error gracefully."""
        with patch('psutil.cpu_percent', return_value=50.0), \
             patch('psutil.virtual_memory', side_effect=Exception("Memory error")), \
             patch('psutil.disk_usage') as mock_disk:

            mock_disk_obj = Mock()
            mock_disk_obj.free = 100 * (1024 ** 3)
            mock_disk.return_value = mock_disk_obj

            collector = MetricsCollector()
            metrics = collector.collect()

            assert metrics.cpu_percent == 50.0
            assert metrics.memory_percent is None
            assert metrics.disk_free_gb is not None

    @pytest.mark.skipif(not HAS_PSUTIL, reason="psutil required for mocking tests")
    def test_handles_disk_error(self):
        """Test handles disk usage error gracefully."""
        with patch('psutil.cpu_percent', return_value=50.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage', side_effect=Exception("Disk error")):

            mock_memory_obj = Mock()
            mock_memory_obj.percent = 60.0
            mock_memory.return_value = mock_memory_obj

            collector = MetricsCollector()
            metrics = collector.collect()

            assert metrics.cpu_percent == 50.0
            assert metrics.memory_percent == 60.0
            assert metrics.disk_free_gb is None


class TestMetricsCollectorWithoutPsutil:
    """Tests for MetricsCollector when psutil is not available."""

    @patch('src.metrics.HAS_PSUTIL', False)
    def test_collect_returns_empty_metrics(self):
        """Test collect returns empty metrics without psutil."""
        collector = MetricsCollector()
        metrics = collector.collect()

        assert metrics.is_empty
        assert metrics.cpu_percent is None
        assert metrics.memory_percent is None
        assert metrics.disk_free_gb is None


class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    @pytest.mark.skipif(not HAS_PSUTIL, reason="psutil required for mocking tests")
    def test_collect_metrics_function(self):
        """Test collect_metrics convenience function."""
        with patch('psutil.cpu_percent', return_value=25.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:

            mock_memory_obj = Mock()
            mock_memory_obj.percent = 50.0
            mock_memory.return_value = mock_memory_obj
            mock_disk_obj = Mock()
            mock_disk_obj.free = 200 * (1024 ** 3)
            mock_disk.return_value = mock_disk_obj

            metrics = collect_metrics()

            assert metrics.cpu_percent == 25.0
            assert metrics.memory_percent == 50.0
            assert metrics.disk_free_gb is not None

    def test_is_metrics_available_returns_bool(self):
        """Test is_metrics_available returns boolean."""
        result = is_metrics_available()
        assert isinstance(result, bool)

    @pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not installed")
    def test_is_metrics_available_true_with_psutil(self):
        """Test is_metrics_available returns True when psutil is installed."""
        assert is_metrics_available() is True
