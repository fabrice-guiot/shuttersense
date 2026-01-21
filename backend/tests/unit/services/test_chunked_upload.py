"""
Unit tests for ChunkedUploadService.

Tests chunked upload protocol including:
- Session management
- Chunk upload and storage
- Checksum verification
- Content validation (JSON, HTML security)
- Session expiration and cleanup

Issue #90 - Distributed Agent Architecture (Phase 15)
Task: T200
"""

import hashlib
import json
import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from backend.src.services.chunked_upload_service import (
    ChunkedUploadService,
    UploadType,
    should_use_chunked_upload,
    INLINE_JSON_THRESHOLD,
    DEFAULT_CHUNK_SIZE,
    SESSION_TTL_HOURS,
)
from backend.src.services.exceptions import ValidationError, NotFoundError


class TestUploadSessionManagement:
    """Tests for upload session creation and management."""

    def test_initiate_upload_success(self):
        """Successfully initiate a chunked upload session."""
        service = ChunkedUploadService()

        result = service.initiate_upload(
            job_guid="job_test123",
            agent_id=1,
            team_id=1,
            upload_type=UploadType.RESULTS_JSON,
            expected_size=10_000_000,  # 10MB
        )

        assert result.upload_id is not None
        assert len(result.upload_id) > 0
        assert result.chunk_size == DEFAULT_CHUNK_SIZE
        assert result.total_chunks == 2  # 10MB / 5MB = 2 chunks

    def test_initiate_upload_custom_chunk_size(self):
        """Initiate upload with custom chunk size."""
        service = ChunkedUploadService()

        result = service.initiate_upload(
            job_guid="job_test123",
            agent_id=1,
            team_id=1,
            upload_type=UploadType.REPORT_HTML,
            expected_size=15_000_000,  # 15MB
            chunk_size=3_000_000,  # 3MB chunks
        )

        assert result.chunk_size == 3_000_000
        assert result.total_chunks == 5  # 15MB / 3MB = 5 chunks

    def test_initiate_upload_invalid_chunk_size(self):
        """Reject chunk size exceeding maximum."""
        service = ChunkedUploadService()

        with pytest.raises(ValidationError, match="Chunk size cannot exceed"):
            service.initiate_upload(
                job_guid="job_test123",
                agent_id=1,
                team_id=1,
                upload_type=UploadType.RESULTS_JSON,
                expected_size=100_000_000,
                chunk_size=20_000_000,  # 20MB - exceeds 10MB max
            )

    def test_initiate_upload_invalid_expected_size(self):
        """Reject zero or negative expected size."""
        service = ChunkedUploadService()

        with pytest.raises(ValidationError, match="Expected size must be positive"):
            service.initiate_upload(
                job_guid="job_test123",
                agent_id=1,
                team_id=1,
                upload_type=UploadType.RESULTS_JSON,
                expected_size=0,
            )

    def test_get_session_not_found(self):
        """Return None for non-existent session."""
        service = ChunkedUploadService()

        session = service.get_session("nonexistent_upload_id")
        assert session is None

    def test_validate_session_success(self):
        """Successfully validate an existing session."""
        service = ChunkedUploadService()

        result = service.initiate_upload(
            job_guid="job_test123",
            agent_id=1,
            team_id=1,
            upload_type=UploadType.RESULTS_JSON,
            expected_size=1_000_000,
        )

        session = service.validate_session(
            upload_id=result.upload_id,
            agent_id=1,
            team_id=1,
        )

        assert session is not None
        assert session.upload_id == result.upload_id

    def test_validate_session_wrong_agent(self):
        """Reject validation from wrong agent."""
        service = ChunkedUploadService()

        result = service.initiate_upload(
            job_guid="job_test123",
            agent_id=1,
            team_id=1,
            upload_type=UploadType.RESULTS_JSON,
            expected_size=1_000_000,
        )

        with pytest.raises(ValidationError, match="different agent"):
            service.validate_session(
                upload_id=result.upload_id,
                agent_id=2,  # Different agent
                team_id=1,
            )

    def test_validate_session_wrong_team(self):
        """Reject validation from wrong team."""
        service = ChunkedUploadService()

        result = service.initiate_upload(
            job_guid="job_test123",
            agent_id=1,
            team_id=1,
            upload_type=UploadType.RESULTS_JSON,
            expected_size=1_000_000,
        )

        with pytest.raises(ValidationError, match="different team"):
            service.validate_session(
                upload_id=result.upload_id,
                agent_id=1,
                team_id=2,  # Different team
            )


class TestChunkUpload:
    """Tests for chunk upload functionality."""

    def test_upload_chunk_success(self):
        """Successfully upload a chunk."""
        service = ChunkedUploadService()

        # Create session for 10KB content with 5KB chunks
        result = service.initiate_upload(
            job_guid="job_test123",
            agent_id=1,
            team_id=1,
            upload_type=UploadType.RESULTS_JSON,
            expected_size=10_000,
            chunk_size=5_000,
        )

        # Upload first chunk (5000 bytes)
        chunk_data = b"x" * 5000
        is_new = service.upload_chunk(
            upload_id=result.upload_id,
            chunk_index=0,
            chunk_data=chunk_data,
            agent_id=1,
            team_id=1,
        )

        assert is_new is True

        # Verify chunk was recorded
        session = service.get_session(result.upload_id)
        assert 0 in session.chunks
        assert session.chunks[0].size == 5000

    def test_upload_chunk_idempotent(self):
        """Duplicate chunk upload is idempotent."""
        service = ChunkedUploadService()

        result = service.initiate_upload(
            job_guid="job_test123",
            agent_id=1,
            team_id=1,
            upload_type=UploadType.RESULTS_JSON,
            expected_size=5_000,
            chunk_size=5_000,
        )

        chunk_data = b"x" * 5000

        # First upload
        is_new1 = service.upload_chunk(
            upload_id=result.upload_id,
            chunk_index=0,
            chunk_data=chunk_data,
            agent_id=1,
            team_id=1,
        )

        # Duplicate upload
        is_new2 = service.upload_chunk(
            upload_id=result.upload_id,
            chunk_index=0,
            chunk_data=chunk_data,
            agent_id=1,
            team_id=1,
        )

        assert is_new1 is True
        assert is_new2 is False  # Duplicate

    def test_upload_chunk_invalid_index(self):
        """Reject chunk with invalid index."""
        service = ChunkedUploadService()

        result = service.initiate_upload(
            job_guid="job_test123",
            agent_id=1,
            team_id=1,
            upload_type=UploadType.RESULTS_JSON,
            expected_size=5_000,
            chunk_size=5_000,
        )

        with pytest.raises(ValidationError, match="Invalid chunk index"):
            service.upload_chunk(
                upload_id=result.upload_id,
                chunk_index=5,  # Only 1 chunk expected (index 0)
                chunk_data=b"x" * 5000,
                agent_id=1,
                team_id=1,
            )

    def test_upload_chunk_size_mismatch(self):
        """Reject chunk with wrong size (non-last chunk)."""
        service = ChunkedUploadService()

        result = service.initiate_upload(
            job_guid="job_test123",
            agent_id=1,
            team_id=1,
            upload_type=UploadType.RESULTS_JSON,
            expected_size=10_000,
            chunk_size=5_000,
        )

        with pytest.raises(ValidationError, match="Chunk size mismatch"):
            service.upload_chunk(
                upload_id=result.upload_id,
                chunk_index=0,  # First chunk - should be full size
                chunk_data=b"x" * 3000,  # Wrong size
                agent_id=1,
                team_id=1,
            )

    def test_upload_last_chunk_smaller(self):
        """Last chunk can be smaller than chunk size."""
        service = ChunkedUploadService()

        # 8KB content with 5KB chunks = 2 chunks (5KB + 3KB)
        result = service.initiate_upload(
            job_guid="job_test123",
            agent_id=1,
            team_id=1,
            upload_type=UploadType.RESULTS_JSON,
            expected_size=8_000,
            chunk_size=5_000,
        )

        # Upload first chunk (5000 bytes)
        service.upload_chunk(
            upload_id=result.upload_id,
            chunk_index=0,
            chunk_data=b"x" * 5000,
            agent_id=1,
            team_id=1,
        )

        # Upload last chunk (3000 bytes)
        is_new = service.upload_chunk(
            upload_id=result.upload_id,
            chunk_index=1,
            chunk_data=b"y" * 3000,
            agent_id=1,
            team_id=1,
        )

        assert is_new is True
        session = service.get_session(result.upload_id)
        assert session.is_complete

    def test_upload_chunk_different_content_rejected(self):
        """Reject duplicate chunk with different content."""
        service = ChunkedUploadService()

        result = service.initiate_upload(
            job_guid="job_test123",
            agent_id=1,
            team_id=1,
            upload_type=UploadType.RESULTS_JSON,
            expected_size=5_000,
            chunk_size=5_000,
        )

        # First upload
        service.upload_chunk(
            upload_id=result.upload_id,
            chunk_index=0,
            chunk_data=b"x" * 5000,
            agent_id=1,
            team_id=1,
        )

        # Duplicate with different content
        with pytest.raises(ValidationError, match="different content"):
            service.upload_chunk(
                upload_id=result.upload_id,
                chunk_index=0,
                chunk_data=b"y" * 5000,  # Different content
                agent_id=1,
                team_id=1,
            )


class TestFinalization:
    """Tests for upload finalization."""

    def test_finalize_success(self):
        """Successfully finalize a complete upload."""
        service = ChunkedUploadService()

        # Create and upload a simple JSON content
        content = json.dumps({"test": "data"}).encode('utf-8')
        checksum = hashlib.sha256(content).hexdigest()

        result = service.initiate_upload(
            job_guid="job_test123",
            agent_id=1,
            team_id=1,
            upload_type=UploadType.RESULTS_JSON,
            expected_size=len(content),
            chunk_size=len(content),  # Single chunk
        )

        service.upload_chunk(
            upload_id=result.upload_id,
            chunk_index=0,
            chunk_data=content,
            agent_id=1,
            team_id=1,
        )

        finalize_result = service.finalize_upload(
            upload_id=result.upload_id,
            expected_checksum=checksum,
            agent_id=1,
            team_id=1,
        )

        assert finalize_result.success is True
        assert finalize_result.content == content
        assert finalize_result.content_type == UploadType.RESULTS_JSON

    def test_finalize_incomplete_upload(self):
        """Reject finalization of incomplete upload."""
        service = ChunkedUploadService()

        result = service.initiate_upload(
            job_guid="job_test123",
            agent_id=1,
            team_id=1,
            upload_type=UploadType.RESULTS_JSON,
            expected_size=10_000,
            chunk_size=5_000,
        )

        # Only upload first chunk
        service.upload_chunk(
            upload_id=result.upload_id,
            chunk_index=0,
            chunk_data=b"x" * 5000,
            agent_id=1,
            team_id=1,
        )

        with pytest.raises(ValidationError, match="Upload incomplete"):
            service.finalize_upload(
                upload_id=result.upload_id,
                expected_checksum="dummy_checksum",
                agent_id=1,
                team_id=1,
            )

    def test_finalize_checksum_mismatch(self):
        """Reject finalization with wrong checksum."""
        service = ChunkedUploadService()

        content = b"test content"

        result = service.initiate_upload(
            job_guid="job_test123",
            agent_id=1,
            team_id=1,
            upload_type=UploadType.RESULTS_JSON,
            expected_size=len(content),
            chunk_size=len(content),
        )

        service.upload_chunk(
            upload_id=result.upload_id,
            chunk_index=0,
            chunk_data=content,
            agent_id=1,
            team_id=1,
        )

        with pytest.raises(ValidationError, match="Checksum verification failed"):
            service.finalize_upload(
                upload_id=result.upload_id,
                expected_checksum="wrong_checksum_here_1234567890abcdef1234567890abcdef1234567890abcdef1234",
                agent_id=1,
                team_id=1,
            )


class TestJSONValidation:
    """Tests for JSON results validation."""

    def test_valid_json_object(self):
        """Accept valid JSON object."""
        service = ChunkedUploadService()

        content = json.dumps({"results": {"files": 100}}).encode('utf-8')
        checksum = hashlib.sha256(content).hexdigest()

        result = service.initiate_upload(
            job_guid="job_test123",
            agent_id=1,
            team_id=1,
            upload_type=UploadType.RESULTS_JSON,
            expected_size=len(content),
            chunk_size=len(content),
        )

        service.upload_chunk(
            upload_id=result.upload_id,
            chunk_index=0,
            chunk_data=content,
            agent_id=1,
            team_id=1,
        )

        finalize_result = service.finalize_upload(
            upload_id=result.upload_id,
            expected_checksum=checksum,
            agent_id=1,
            team_id=1,
        )

        assert finalize_result.success is True

    def test_invalid_json_syntax(self):
        """Reject invalid JSON syntax."""
        service = ChunkedUploadService()

        content = b"{ invalid json }"
        checksum = hashlib.sha256(content).hexdigest()

        result = service.initiate_upload(
            job_guid="job_test123",
            agent_id=1,
            team_id=1,
            upload_type=UploadType.RESULTS_JSON,
            expected_size=len(content),
            chunk_size=len(content),
        )

        service.upload_chunk(
            upload_id=result.upload_id,
            chunk_index=0,
            chunk_data=content,
            agent_id=1,
            team_id=1,
        )

        with pytest.raises(ValidationError, match="Invalid JSON"):
            service.finalize_upload(
                upload_id=result.upload_id,
                expected_checksum=checksum,
                agent_id=1,
                team_id=1,
            )

    def test_json_array_rejected(self):
        """Reject JSON array (must be object)."""
        service = ChunkedUploadService()

        content = json.dumps([1, 2, 3]).encode('utf-8')
        checksum = hashlib.sha256(content).hexdigest()

        result = service.initiate_upload(
            job_guid="job_test123",
            agent_id=1,
            team_id=1,
            upload_type=UploadType.RESULTS_JSON,
            expected_size=len(content),
            chunk_size=len(content),
        )

        service.upload_chunk(
            upload_id=result.upload_id,
            chunk_index=0,
            chunk_data=content,
            agent_id=1,
            team_id=1,
        )

        with pytest.raises(ValidationError, match="must be a JSON object"):
            service.finalize_upload(
                upload_id=result.upload_id,
                expected_checksum=checksum,
                agent_id=1,
                team_id=1,
            )


class TestHTMLSecurityValidation:
    """Tests for HTML report security validation."""

    def test_valid_html_self_contained(self):
        """Accept self-contained HTML."""
        service = ChunkedUploadService()

        content = b"""
        <!DOCTYPE html>
        <html>
        <head><title>Report</title></head>
        <body>
            <h1>Analysis Report</h1>
            <script>console.log('inline script');</script>
            <style>.test { color: red; }</style>
        </body>
        </html>
        """
        checksum = hashlib.sha256(content).hexdigest()

        result = service.initiate_upload(
            job_guid="job_test123",
            agent_id=1,
            team_id=1,
            upload_type=UploadType.REPORT_HTML,
            expected_size=len(content),
            chunk_size=len(content),
        )

        service.upload_chunk(
            upload_id=result.upload_id,
            chunk_index=0,
            chunk_data=content,
            agent_id=1,
            team_id=1,
        )

        finalize_result = service.finalize_upload(
            upload_id=result.upload_id,
            expected_checksum=checksum,
            agent_id=1,
            team_id=1,
        )

        assert finalize_result.success is True

    def test_trusted_cdn_scripts_allowed(self):
        """Accept HTML with scripts from trusted CDNs."""
        service = ChunkedUploadService()

        content = b"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Report</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
        </head>
        <body>
            <h1>Analysis Report</h1>
            <canvas id="chart"></canvas>
        </body>
        </html>
        """
        checksum = hashlib.sha256(content).hexdigest()

        result = service.initiate_upload(
            job_guid="job_test123",
            agent_id=1,
            team_id=1,
            upload_type=UploadType.REPORT_HTML,
            expected_size=len(content),
            chunk_size=len(content),
        )

        service.upload_chunk(
            upload_id=result.upload_id,
            chunk_index=0,
            chunk_data=content,
            agent_id=1,
            team_id=1,
        )

        finalize_result = service.finalize_upload(
            upload_id=result.upload_id,
            expected_checksum=checksum,
            agent_id=1,
            team_id=1,
        )

        assert finalize_result.success is True

    def test_external_script_rejected(self):
        """Reject HTML with external scripts from untrusted sources."""
        service = ChunkedUploadService()

        content = b"""
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://evil.com/script.js"></script>
        </head>
        <body>Test</body>
        </html>
        """
        checksum = hashlib.sha256(content).hexdigest()

        result = service.initiate_upload(
            job_guid="job_test123",
            agent_id=1,
            team_id=1,
            upload_type=UploadType.REPORT_HTML,
            expected_size=len(content),
            chunk_size=len(content),
        )

        service.upload_chunk(
            upload_id=result.upload_id,
            chunk_index=0,
            chunk_data=content,
            agent_id=1,
            team_id=1,
        )

        with pytest.raises(ValidationError, match="External script sources"):
            service.finalize_upload(
                upload_id=result.upload_id,
                expected_checksum=checksum,
                agent_id=1,
                team_id=1,
            )

    def test_javascript_url_rejected(self):
        """Reject HTML with javascript: URLs."""
        service = ChunkedUploadService()

        content = b"""
        <!DOCTYPE html>
        <html>
        <body>
            <a href="javascript:alert('xss')">Click me</a>
        </body>
        </html>
        """
        checksum = hashlib.sha256(content).hexdigest()

        result = service.initiate_upload(
            job_guid="job_test123",
            agent_id=1,
            team_id=1,
            upload_type=UploadType.REPORT_HTML,
            expected_size=len(content),
            chunk_size=len(content),
        )

        service.upload_chunk(
            upload_id=result.upload_id,
            chunk_index=0,
            chunk_data=content,
            agent_id=1,
            team_id=1,
        )

        with pytest.raises(ValidationError, match="javascript: URLs"):
            service.finalize_upload(
                upload_id=result.upload_id,
                expected_checksum=checksum,
                agent_id=1,
                team_id=1,
            )

    def test_external_stylesheet_rejected(self):
        """Reject HTML with external stylesheets."""
        service = ChunkedUploadService()

        content = b"""
        <!DOCTYPE html>
        <html>
        <head>
            <link rel="stylesheet" href="https://evil.com/style.css">
        </head>
        <body>Test</body>
        </html>
        """
        checksum = hashlib.sha256(content).hexdigest()

        result = service.initiate_upload(
            job_guid="job_test123",
            agent_id=1,
            team_id=1,
            upload_type=UploadType.REPORT_HTML,
            expected_size=len(content),
            chunk_size=len(content),
        )

        service.upload_chunk(
            upload_id=result.upload_id,
            chunk_index=0,
            chunk_data=content,
            agent_id=1,
            team_id=1,
        )

        with pytest.raises(ValidationError, match="External stylesheets"):
            service.finalize_upload(
                upload_id=result.upload_id,
                expected_checksum=checksum,
                agent_id=1,
                team_id=1,
            )

    def test_dangerous_data_url_rejected(self):
        """Reject HTML with dangerous data: URLs."""
        service = ChunkedUploadService()

        content = b"""
        <!DOCTYPE html>
        <html>
        <body>
            <iframe src="data:text/html,<script>alert('xss')</script>"></iframe>
        </body>
        </html>
        """
        checksum = hashlib.sha256(content).hexdigest()

        result = service.initiate_upload(
            job_guid="job_test123",
            agent_id=1,
            team_id=1,
            upload_type=UploadType.REPORT_HTML,
            expected_size=len(content),
            chunk_size=len(content),
        )

        service.upload_chunk(
            upload_id=result.upload_id,
            chunk_index=0,
            chunk_data=content,
            agent_id=1,
            team_id=1,
        )

        with pytest.raises(ValidationError, match="Dangerous data: URLs"):
            service.finalize_upload(
                upload_id=result.upload_id,
                expected_checksum=checksum,
                agent_id=1,
                team_id=1,
            )


class TestSessionCleanup:
    """Tests for session cleanup functionality."""

    def test_cancel_upload(self):
        """Successfully cancel an upload."""
        service = ChunkedUploadService()

        result = service.initiate_upload(
            job_guid="job_test123",
            agent_id=1,
            team_id=1,
            upload_type=UploadType.RESULTS_JSON,
            expected_size=5_000,
            chunk_size=5_000,
        )

        cancelled = service.cancel_upload(
            upload_id=result.upload_id,
            agent_id=1,
            team_id=1,
        )

        assert cancelled is True
        assert service.get_session(result.upload_id) is None

    def test_cancel_wrong_agent(self):
        """Reject cancellation from wrong agent."""
        service = ChunkedUploadService()

        result = service.initiate_upload(
            job_guid="job_test123",
            agent_id=1,
            team_id=1,
            upload_type=UploadType.RESULTS_JSON,
            expected_size=5_000,
            chunk_size=5_000,
        )

        with pytest.raises(ValidationError, match="different agent"):
            service.cancel_upload(
                upload_id=result.upload_id,
                agent_id=2,
                team_id=1,
            )

    def test_cleanup_expired_sessions(self):
        """Clean up expired sessions."""
        service = ChunkedUploadService()

        # Create a session
        result = service.initiate_upload(
            job_guid="job_test123",
            agent_id=1,
            team_id=1,
            upload_type=UploadType.RESULTS_JSON,
            expected_size=5_000,
            chunk_size=5_000,
        )

        # Manually expire the session
        session = service.get_session(result.upload_id)
        session.expires_at = datetime.utcnow() - timedelta(hours=1)

        # Cleanup should remove expired session
        cleaned = service.cleanup_expired_sessions()

        assert cleaned == 1
        assert service.get_session(result.upload_id) is None


class TestShouldUseChunkedUpload:
    """Tests for the should_use_chunked_upload helper."""

    def test_small_results_inline(self):
        """Small results don't need chunked upload."""
        results = {"small": "data"}
        results_chunked, html_chunked = should_use_chunked_upload(results=results)

        assert results_chunked is False
        assert html_chunked is False

    def test_large_results_chunked(self):
        """Large results need chunked upload."""
        # Create results larger than threshold
        results = {"data": "x" * (INLINE_JSON_THRESHOLD + 1000)}
        results_chunked, html_chunked = should_use_chunked_upload(results=results)

        assert results_chunked is True
        assert html_chunked is False

    def test_html_always_chunked(self):
        """HTML reports always use chunked upload."""
        results_chunked, html_chunked = should_use_chunked_upload(
            results={"small": "data"},
            report_html="<html>Small report</html>",
        )

        assert results_chunked is False
        assert html_chunked is True

    def test_both_chunked(self):
        """Both large results and HTML trigger chunked upload."""
        results = {"data": "x" * (INLINE_JSON_THRESHOLD + 1000)}
        results_chunked, html_chunked = should_use_chunked_upload(
            results=results,
            report_html="<html>Report</html>",
        )

        assert results_chunked is True
        assert html_chunked is True


class TestUploadStatus:
    """Tests for upload status retrieval."""

    def test_get_upload_status(self):
        """Get current upload status."""
        service = ChunkedUploadService()

        result = service.initiate_upload(
            job_guid="job_test123",
            agent_id=1,
            team_id=1,
            upload_type=UploadType.RESULTS_JSON,
            expected_size=10_000,
            chunk_size=5_000,
        )

        # Upload first chunk
        service.upload_chunk(
            upload_id=result.upload_id,
            chunk_index=0,
            chunk_data=b"x" * 5000,
            agent_id=1,
            team_id=1,
        )

        status = service.get_upload_status(
            upload_id=result.upload_id,
            agent_id=1,
            team_id=1,
        )

        assert status["upload_id"] == result.upload_id
        assert status["job_guid"] == "job_test123"
        assert status["upload_type"] == "results_json"
        assert status["expected_size"] == 10_000
        assert status["received_size"] == 5000
        assert status["total_chunks"] == 2
        assert status["received_chunks"] == 1
        assert status["received_chunk_indices"] == [0]
        assert status["missing_chunk_indices"] == [1]
        assert status["is_complete"] is False
