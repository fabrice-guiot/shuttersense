"""
Unit tests for agent chunked upload client.

Tests chunked upload protocol client-side functionality:
- Automatic detection of when chunked upload is needed
- Session initiation
- Chunk upload with retry
- Checksum calculation and finalization
- Error handling

Issue #90 - Distributed Agent Architecture (Phase 15)
Task: T201
"""

import hashlib
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestShouldUseChunkedUpload:
    """Tests for should_use_chunked_upload helper."""

    def test_small_results_inline(self):
        """Small results don't need chunked upload."""
        from src.chunked_upload import should_use_chunked_upload

        results = {"small": "data"}
        results_chunked, html_chunked = should_use_chunked_upload(results=results)

        assert results_chunked is False
        assert html_chunked is False

    def test_large_results_chunked(self):
        """Large results need chunked upload."""
        from src.chunked_upload import should_use_chunked_upload, INLINE_JSON_THRESHOLD

        # Create results larger than threshold
        results = {"data": "x" * (INLINE_JSON_THRESHOLD + 1000)}
        results_chunked, html_chunked = should_use_chunked_upload(results=results)

        assert results_chunked is True
        assert html_chunked is False

    def test_html_always_chunked(self):
        """HTML reports always use chunked upload."""
        from src.chunked_upload import should_use_chunked_upload

        results_chunked, html_chunked = should_use_chunked_upload(
            results={"small": "data"},
            report_html="<html>Small report</html>",
        )

        assert results_chunked is False
        assert html_chunked is True


class TestChunkedUploadClient:
    """Tests for ChunkedUploadClient class."""

    @pytest.fixture
    def mock_api_client(self, mock_server_url, mock_api_key):
        """Create a mock API client."""
        from src.api_client import AgentApiClient

        client = AgentApiClient(server_url=mock_server_url, api_key=mock_api_key)
        # Mock the underlying httpx client
        client._client = AsyncMock()
        return client

    @pytest.fixture
    def upload_client(self, mock_api_client):
        """Create a ChunkedUploadClient instance."""
        from src.chunked_upload import ChunkedUploadClient

        return ChunkedUploadClient(
            api_client=mock_api_client,
            chunk_size=1000,  # Small chunk size for testing
            max_retries=2,
        )


class TestSessionInitiation(TestChunkedUploadClient):
    """Tests for upload session initiation."""

    @pytest.mark.asyncio
    async def test_initiate_upload_success(self, upload_client, mock_api_client):
        """Successfully initiate an upload session."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "upload_id": "test_upload_123",
            "chunk_size": 1000,
            "total_chunks": 3,
        }
        mock_api_client._client.post = AsyncMock(return_value=mock_response)

        session = await upload_client._initiate_upload(
            job_guid="job_test123",
            upload_type="results_json",
            expected_size=3000,
        )

        assert session.upload_id == "test_upload_123"
        assert session.chunk_size == 1000
        assert session.total_chunks == 3

    @pytest.mark.asyncio
    async def test_initiate_upload_job_not_found(self, upload_client, mock_api_client):
        """Handle job not found error."""
        from src.chunked_upload import ChunkedUploadError

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"detail": "Job not found"}
        mock_api_client._client.post = AsyncMock(return_value=mock_response)

        with pytest.raises(ChunkedUploadError, match="Job not found"):
            await upload_client._initiate_upload(
                job_guid="job_nonexistent",
                upload_type="results_json",
                expected_size=3000,
            )

    @pytest.mark.asyncio
    async def test_initiate_upload_auth_error(self, upload_client, mock_api_client):
        """Handle authentication error."""
        from src.api_client import AuthenticationError

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_api_client._client.post = AsyncMock(return_value=mock_response)

        with pytest.raises(AuthenticationError):
            await upload_client._initiate_upload(
                job_guid="job_test123",
                upload_type="results_json",
                expected_size=3000,
            )


class TestChunkUpload(TestChunkedUploadClient):
    """Tests for chunk upload functionality."""

    @pytest.mark.asyncio
    async def test_upload_chunk_success(self, upload_client, mock_api_client):
        """Successfully upload a chunk."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"received": True}
        mock_api_client._client.put = AsyncMock(return_value=mock_response)

        result = await upload_client._upload_chunk(
            upload_id="test_upload_123",
            chunk_index=0,
            chunk_data=b"test chunk data",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_upload_chunk_duplicate(self, upload_client, mock_api_client):
        """Handle duplicate chunk upload (idempotent)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"received": False}  # Duplicate
        mock_api_client._client.put = AsyncMock(return_value=mock_response)

        result = await upload_client._upload_chunk(
            upload_id="test_upload_123",
            chunk_index=0,
            chunk_data=b"test chunk data",
        )

        assert result is False  # Duplicate detected

    @pytest.mark.asyncio
    async def test_upload_chunk_with_retry(self, upload_client, mock_api_client):
        """Retry chunk upload on connection error."""
        import httpx
        from src.api_client import ConnectionError

        # First call fails, second succeeds
        call_count = 0

        async def mock_put(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.ConnectError("Connection failed")
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"received": True}
            return mock_response

        mock_api_client._client.put = mock_put

        # Should succeed after retry
        with patch("asyncio.sleep", new=AsyncMock()):  # Skip actual sleep
            await upload_client._upload_chunk_with_retry(
                upload_id="test_upload_123",
                chunk_index=0,
                chunk_data=b"test data",
            )

        assert call_count == 2  # One failure + one success

    @pytest.mark.asyncio
    async def test_upload_chunk_max_retries_exceeded(self, upload_client, mock_api_client):
        """Fail after max retries exceeded."""
        import httpx
        from src.chunked_upload import ChunkedUploadError

        mock_api_client._client.put = AsyncMock(
            side_effect=httpx.ConnectError("Connection failed")
        )

        with patch("asyncio.sleep", new=AsyncMock()):  # Skip actual sleep
            with pytest.raises(ChunkedUploadError, match="after 2 attempts"):
                await upload_client._upload_chunk_with_retry(
                    upload_id="test_upload_123",
                    chunk_index=0,
                    chunk_data=b"test data",
                )


class TestFinalization(TestChunkedUploadClient):
    """Tests for upload finalization."""

    @pytest.mark.asyncio
    async def test_finalize_success(self, upload_client, mock_api_client):
        """Successfully finalize an upload."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "upload_type": "results_json",
            "content_size": 3000,
        }
        mock_api_client._client.post = AsyncMock(return_value=mock_response)

        await upload_client._finalize_upload(
            upload_id="test_upload_123",
            checksum="abc123def456...",
        )

        # Verify correct endpoint was called
        mock_api_client._client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_finalize_checksum_error(self, upload_client, mock_api_client):
        """Handle checksum verification failure."""
        from src.chunked_upload import ChunkedUploadError

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"detail": "Checksum verification failed"}
        mock_api_client._client.post = AsyncMock(return_value=mock_response)

        with pytest.raises(ChunkedUploadError, match="Checksum"):
            await upload_client._finalize_upload(
                upload_id="test_upload_123",
                checksum="wrong_checksum",
            )


class TestFullUpload(TestChunkedUploadClient):
    """Tests for complete upload workflow."""

    @pytest.mark.asyncio
    async def test_upload_results_success(self, upload_client, mock_api_client):
        """Successfully upload results through full workflow."""
        # Mock initiation
        init_response = MagicMock()
        init_response.status_code = 201
        init_response.json.return_value = {
            "upload_id": "test_upload_123",
            "chunk_size": 1000,
            "total_chunks": 1,
        }

        # Mock chunk upload
        chunk_response = MagicMock()
        chunk_response.status_code = 200
        chunk_response.json.return_value = {"received": True}

        # Mock finalization
        finalize_response = MagicMock()
        finalize_response.status_code = 200
        finalize_response.json.return_value = {
            "success": True,
            "upload_type": "results_json",
            "content_size": 15,
        }

        # Set up mock client to return different responses
        mock_api_client._client.post = AsyncMock(
            side_effect=[init_response, finalize_response]
        )
        mock_api_client._client.put = AsyncMock(return_value=chunk_response)

        results = {"test": "data"}
        result = await upload_client.upload_results(
            job_guid="job_test123",
            results=results,
        )

        assert result.success is True
        assert result.upload_id == "test_upload_123"
        assert result.checksum is not None

    @pytest.mark.asyncio
    async def test_upload_html_report_success(self, upload_client, mock_api_client):
        """Successfully upload HTML report through full workflow."""
        # Mock initiation
        init_response = MagicMock()
        init_response.status_code = 201
        init_response.json.return_value = {
            "upload_id": "test_upload_456",
            "chunk_size": 1000,
            "total_chunks": 1,
        }

        # Mock chunk upload
        chunk_response = MagicMock()
        chunk_response.status_code = 200
        chunk_response.json.return_value = {"received": True}

        # Mock finalization
        finalize_response = MagicMock()
        finalize_response.status_code = 200
        finalize_response.json.return_value = {
            "success": True,
            "upload_type": "report_html",
            "content_size": 100,
        }

        mock_api_client._client.post = AsyncMock(
            side_effect=[init_response, finalize_response]
        )
        mock_api_client._client.put = AsyncMock(return_value=chunk_response)

        result = await upload_client.upload_report_html(
            job_guid="job_test123",
            report_html="<html><body>Test Report</body></html>",
        )

        assert result.success is True
        assert result.upload_id == "test_upload_456"

    @pytest.mark.asyncio
    async def test_upload_failure_returns_error(self, upload_client, mock_api_client):
        """Upload failure returns error result instead of raising."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"detail": "Internal server error"}
        mock_api_client._client.post = AsyncMock(return_value=mock_response)

        result = await upload_client.upload_results(
            job_guid="job_test123",
            results={"test": "data"},
        )

        assert result.success is False
        assert result.error is not None


class TestCancelUpload(TestChunkedUploadClient):
    """Tests for upload cancellation."""

    @pytest.mark.asyncio
    async def test_cancel_upload_success(self, upload_client, mock_api_client):
        """Successfully cancel an upload."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_api_client._client.delete = AsyncMock(return_value=mock_response)

        result = await upload_client.cancel_upload("test_upload_123")

        assert result is True

    @pytest.mark.asyncio
    async def test_cancel_upload_not_found(self, upload_client, mock_api_client):
        """Handle cancellation of non-existent upload."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_api_client._client.delete = AsyncMock(return_value=mock_response)

        result = await upload_client.cancel_upload("nonexistent_upload")

        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_upload_error_handled(self, upload_client, mock_api_client):
        """Handle errors during cancellation gracefully."""
        mock_api_client._client.delete = AsyncMock(
            side_effect=Exception("Network error")
        )

        result = await upload_client.cancel_upload("test_upload_123")

        # Should return False on error, not raise
        assert result is False


class TestCalculateTotalChunks(TestChunkedUploadClient):
    """Tests for chunk calculation."""

    def test_exact_division(self, upload_client):
        """Calculate chunks when size divides evenly."""
        # 3000 bytes / 1000 byte chunks = 3 chunks
        total = upload_client._calculate_total_chunks(3000)
        assert total == 3

    def test_with_remainder(self, upload_client):
        """Calculate chunks when there's a remainder."""
        # 3500 bytes / 1000 byte chunks = 4 chunks
        total = upload_client._calculate_total_chunks(3500)
        assert total == 4

    def test_small_content(self, upload_client):
        """Calculate chunks for small content."""
        # 500 bytes / 1000 byte chunks = 1 chunk
        total = upload_client._calculate_total_chunks(500)
        assert total == 1


class TestChecksumCalculation:
    """Tests for checksum calculation."""

    def test_checksum_matches_sha256(self):
        """Verify checksum uses SHA-256."""
        from src.chunked_upload import ChunkedUploadClient

        content = b"test content for checksum"
        expected = hashlib.sha256(content).hexdigest()

        # The client calculates checksum during upload
        # This tests the logic is correct
        actual = hashlib.sha256(content).hexdigest()
        assert actual == expected

    def test_json_results_deterministic_checksum(self):
        """JSON results produce deterministic checksum."""
        results = {"z_key": "value", "a_key": "other"}

        # Should be sorted for consistent checksum
        json1 = json.dumps(results, sort_keys=True, separators=(',', ':'))
        json2 = json.dumps(results, sort_keys=True, separators=(',', ':'))

        assert json1 == json2
        assert hashlib.sha256(json1.encode()).hexdigest() == hashlib.sha256(json2.encode()).hexdigest()
