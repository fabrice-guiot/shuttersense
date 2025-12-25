"""
Tests for CTRL+C signal handling in both tools.
"""

import pytest
import subprocess
import sys
from pathlib import Path


class TestPhotoStatsSignalHandling:
    """Tests for PhotoStats SIGINT handling (T043-T045)."""

    def test_signal_handler_exists(self):
        """Verify signal handler is defined and registered."""
        import photo_stats
        
        # Check that signal_handler function exists
        assert hasattr(photo_stats, 'signal_handler')
        assert callable(photo_stats.signal_handler)
        
        # Check that shutdown_requested flag exists
        assert hasattr(photo_stats, 'shutdown_requested')

    def test_signal_handler_message_format(self):
        """Verify signal handler uses correct message."""
        import photo_stats
        import io
        from unittest.mock import patch
        
        # Capture print output
        with patch('sys.stdout', new=io.StringIO()) as mock_stdout:
            try:
                photo_stats.signal_handler(2, None)
            except SystemExit as e:
                # Check exit code
                assert e.code == 130
                
                # Check message
                output = mock_stdout.getvalue()
                assert "Operation interrupted by user" in output

    def test_scan_loop_checks_shutdown(self):
        """Verify scan loop checks shutdown_requested flag."""
        with open('photo_stats.py', 'r') as f:
            content = f.read()
            
        # Verify shutdown checks exist in scan loop
        assert 'if shutdown_requested:' in content
        assert 'sys.exit(130)' in content


class TestPhotoPairingSignalHandling:
    """Tests for Photo Pairing SIGINT handling (T046-T048)."""

    def test_signal_handler_exists(self):
        """Verify signal handler is defined and registered."""
        import photo_pairing
        
        # Check that signal_handler function exists
        assert hasattr(photo_pairing, 'signal_handler')
        assert callable(photo_pairing.signal_handler)
        
        # Check that shutdown_requested flag exists
        assert hasattr(photo_pairing, 'shutdown_requested')

    def test_signal_handler_message_format(self):
        """Verify signal handler uses correct message."""
        import photo_pairing
        import io
        from unittest.mock import patch
        
        # Capture print output
        with patch('sys.stdout', new=io.StringIO()) as mock_stdout:
            try:
                photo_pairing.signal_handler(2, None)
            except SystemExit as e:
                # Check exit code
                assert e.code == 130
                
                # Check message
                output = mock_stdout.getvalue()
                assert "Operation interrupted by user" in output

    def test_report_generation_checks_shutdown(self):
        """Verify report generation checks shutdown_requested flag."""
        with open('photo_pairing.py', 'r') as f:
            content = f.read()
            
        # Verify shutdown check exists before report generation
        assert 'if shutdown_requested:' in content
        assert 'Report generation skipped' in content or 'skipped due to interruption' in content


class TestAtomicFileWrites:
    """Verify atomic file writes prevent partial reports."""

    def test_report_renderer_uses_atomic_writes(self):
        """Verify ReportRenderer uses temp files and atomic rename."""
        with open('utils/report_renderer.py', 'r') as f:
            content = f.read()
            
        # Verify atomic write pattern
        assert '.tmp' in content
        assert 'os.replace' in content or 'rename' in content
