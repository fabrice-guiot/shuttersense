"""
Unit tests for chunked upload support in offline result upload.

Tests that upload_result() in api_client.py automatically uses chunked
upload for large analysis data (>1MB) and always for HTML reports.

Issue #108 - Remove CLI Direct Usage
Tasks: T032, T033
"""

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.api_client import AgentApiClient, ApiError
from src.chunked_upload import INLINE_JSON_THRESHOLD


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def small_analysis_data():
    """Analysis data well under the 1MB threshold."""
    return {"total_files": 100, "results": {"orphaned": []}}


@pytest.fixture
def large_analysis_data():
    """Analysis data exceeding the 1MB threshold."""
    # Create a results dict that serializes to > 1MB
    # Each entry is ~42 bytes; need ~25000 to exceed 1MB
    large_list = [{"file": f"photo_{i:06d}.cr3", "status": "ok"} for i in range(26000)]
    data = {"total_files": 26000, "results": {"files": large_list}}
    # Verify it actually exceeds the threshold
    serialized = json.dumps(data, sort_keys=True, separators=(",", ":"))
    assert len(serialized.encode("utf-8")) > INLINE_JSON_THRESHOLD
    return data


@pytest.fixture
def html_report():
    """An HTML report string."""
    return "<html><body><h1>Analysis Report</h1><p>Results here.</p></body></html>"


@pytest.fixture
def upload_response():
    """Standard upload response."""
    return {
        "job_guid": "job_01hgw2bbg0000000000000001",
        "result_guid": "res_01hgw2bbg0000000000000001",
        "collection_guid": "col_test",
        "status": "uploaded",
    }


@pytest.fixture
def prepare_response():
    """Standard prepare response."""
    return {"job_guid": "job_placeholder_001"}


def _make_api_client():
    """Create an AgentApiClient with a mocked httpx client."""
    client_instance = AsyncMock()
    api = AgentApiClient.__new__(AgentApiClient)
    api._client = client_instance
    return api, client_instance


# ============================================================================
# Small Data - Inline Mode Tests
# ============================================================================


class TestInlineUpload:
    """Tests that small data is uploaded inline (no chunked upload)."""

    def test_small_data_uses_inline(self, small_analysis_data, upload_response):
        """Small analysis data with no HTML report uses inline upload."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = upload_response

        api, client_instance = _make_api_client()
        client_instance.post.return_value = mock_response

        result = asyncio.run(api.upload_result(
            result_id="uuid-001",
            collection_guid="col_test",
            tool="photostats",
            executed_at="2026-01-28T10:00:00Z",
            analysis_data=small_analysis_data,
        ))

        assert result["status"] == "uploaded"
        # Verify POST was called with inline analysis_data (not upload_id)
        call_args = client_instance.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert "analysis_data" in payload
        assert "analysis_data_upload_id" not in payload
        assert "report_upload_id" not in payload

    def test_no_prepare_called_for_small_data(self, small_analysis_data, upload_response):
        """Prepare endpoint is NOT called when data is small."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = upload_response

        api, client_instance = _make_api_client()
        client_instance.post.return_value = mock_response

        asyncio.run(api.upload_result(
            result_id="uuid-001",
            collection_guid="col_test",
            tool="photostats",
            executed_at="2026-01-28T10:00:00Z",
            analysis_data=small_analysis_data,
        ))

        # Only one POST call (the upload itself), no prepare call
        assert client_instance.post.call_count == 1
        call_path = client_instance.post.call_args[0][0]
        assert "/results/upload" in call_path
        assert "/prepare" not in call_path


# ============================================================================
# Large Data - Chunked Mode Tests
# ============================================================================


class TestChunkedUpload:
    """Tests that large data triggers chunked upload."""

    def test_large_data_uses_chunked(
        self, large_analysis_data, upload_response, prepare_response
    ):
        """Large analysis data (>1MB) triggers prepare + chunked upload."""
        mock_prepare_resp = MagicMock()
        mock_prepare_resp.status_code = 201
        mock_prepare_resp.json.return_value = prepare_response

        mock_upload_resp = MagicMock()
        mock_upload_resp.status_code = 201
        mock_upload_resp.json.return_value = upload_response

        mock_chunked_result = MagicMock()
        mock_chunked_result.success = True
        mock_chunked_result.upload_id = "upload_results_001"

        with patch("src.chunked_upload.ChunkedUploadClient") as MockChunkedClient:
            mock_chunked_instance = AsyncMock()
            mock_chunked_instance.upload_results.return_value = mock_chunked_result
            MockChunkedClient.return_value = mock_chunked_instance

            api, client_instance = _make_api_client()
            # First call: prepare, Second call: upload
            client_instance.post.side_effect = [mock_prepare_resp, mock_upload_resp]

            result = asyncio.run(api.upload_result(
                result_id="uuid-001",
                collection_guid="col_test",
                tool="photostats",
                executed_at="2026-01-28T10:00:00Z",
                analysis_data=large_analysis_data,
            ))

        assert result["status"] == "uploaded"

        # Verify prepare was called first
        first_call = client_instance.post.call_args_list[0]
        assert "/results/upload/prepare" in first_call[0][0]

        # Verify chunked upload was used for results
        mock_chunked_instance.upload_results.assert_called_once()

        # Verify final upload uses upload_id
        second_call = client_instance.post.call_args_list[1]
        final_payload = second_call.kwargs.get("json") or second_call[1].get("json")
        assert final_payload["analysis_data_upload_id"] == "upload_results_001"
        assert "analysis_data" not in final_payload

    def test_html_report_always_chunked(
        self, small_analysis_data, html_report, upload_response, prepare_response
    ):
        """HTML reports always use chunked upload regardless of size."""
        mock_prepare_resp = MagicMock()
        mock_prepare_resp.status_code = 201
        mock_prepare_resp.json.return_value = prepare_response

        mock_upload_resp = MagicMock()
        mock_upload_resp.status_code = 201
        mock_upload_resp.json.return_value = upload_response

        mock_html_chunked = MagicMock()
        mock_html_chunked.success = True
        mock_html_chunked.upload_id = "upload_html_001"

        with patch("src.chunked_upload.ChunkedUploadClient") as MockChunkedClient:
            mock_chunked_instance = AsyncMock()
            mock_chunked_instance.upload_report_html.return_value = mock_html_chunked
            MockChunkedClient.return_value = mock_chunked_instance

            api, client_instance = _make_api_client()
            client_instance.post.side_effect = [mock_prepare_resp, mock_upload_resp]

            result = asyncio.run(api.upload_result(
                result_id="uuid-001",
                collection_guid="col_test",
                tool="photostats",
                executed_at="2026-01-28T10:00:00Z",
                analysis_data=small_analysis_data,
                html_report=html_report,
            ))

        assert result["status"] == "uploaded"

        # Verify prepare was called (html triggers chunked)
        assert client_instance.post.call_count == 2
        first_call = client_instance.post.call_args_list[0]
        assert "/results/upload/prepare" in first_call[0][0]

        # Verify HTML chunked upload was called
        mock_chunked_instance.upload_report_html.assert_called_once()

        # Verify final payload has report_upload_id
        second_call = client_instance.post.call_args_list[1]
        final_payload = second_call.kwargs.get("json") or second_call[1].get("json")
        assert final_payload["report_upload_id"] == "upload_html_001"
        assert "html_report" not in final_payload
        # Small analysis data should be inline
        assert "analysis_data" in final_payload
        assert "analysis_data_upload_id" not in final_payload

    def test_large_data_with_html_both_chunked(
        self, large_analysis_data, html_report, upload_response, prepare_response
    ):
        """Both large analysis data AND HTML report use chunked upload."""
        mock_prepare_resp = MagicMock()
        mock_prepare_resp.status_code = 201
        mock_prepare_resp.json.return_value = prepare_response

        mock_upload_resp = MagicMock()
        mock_upload_resp.status_code = 201
        mock_upload_resp.json.return_value = upload_response

        mock_results_chunked = MagicMock()
        mock_results_chunked.success = True
        mock_results_chunked.upload_id = "upload_results_002"

        mock_html_chunked = MagicMock()
        mock_html_chunked.success = True
        mock_html_chunked.upload_id = "upload_html_002"

        with patch("src.chunked_upload.ChunkedUploadClient") as MockChunkedClient:
            mock_chunked_instance = AsyncMock()
            mock_chunked_instance.upload_results.return_value = mock_results_chunked
            mock_chunked_instance.upload_report_html.return_value = mock_html_chunked
            MockChunkedClient.return_value = mock_chunked_instance

            api, client_instance = _make_api_client()
            client_instance.post.side_effect = [mock_prepare_resp, mock_upload_resp]

            result = asyncio.run(api.upload_result(
                result_id="uuid-001",
                collection_guid="col_test",
                tool="photostats",
                executed_at="2026-01-28T10:00:00Z",
                analysis_data=large_analysis_data,
                html_report=html_report,
            ))

        assert result["status"] == "uploaded"

        # Both chunked uploads were called
        mock_chunked_instance.upload_results.assert_called_once()
        mock_chunked_instance.upload_report_html.assert_called_once()

        # Final payload uses upload_ids for both
        second_call = client_instance.post.call_args_list[1]
        final_payload = second_call.kwargs.get("json") or second_call[1].get("json")
        assert final_payload["analysis_data_upload_id"] == "upload_results_002"
        assert final_payload["report_upload_id"] == "upload_html_002"
        assert "analysis_data" not in final_payload
        assert "html_report" not in final_payload


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestChunkedUploadErrors:
    """Tests for chunked upload error handling."""

    def test_chunked_results_failure_raises(self, large_analysis_data, prepare_response):
        """Failed chunked results upload raises ApiError."""
        mock_prepare_resp = MagicMock()
        mock_prepare_resp.status_code = 201
        mock_prepare_resp.json.return_value = prepare_response

        mock_chunked_result = MagicMock()
        mock_chunked_result.success = False
        mock_chunked_result.error = "Upload session expired"

        with patch("src.chunked_upload.ChunkedUploadClient") as MockChunkedClient:
            mock_chunked_instance = AsyncMock()
            mock_chunked_instance.upload_results.return_value = mock_chunked_result
            MockChunkedClient.return_value = mock_chunked_instance

            api, client_instance = _make_api_client()
            client_instance.post.return_value = mock_prepare_resp

            with pytest.raises(ApiError) as exc_info:
                asyncio.run(api.upload_result(
                    result_id="uuid-001",
                    collection_guid="col_test",
                    tool="photostats",
                    executed_at="2026-01-28T10:00:00Z",
                    analysis_data=large_analysis_data,
                ))

        assert "Chunked analysis data upload failed" in str(exc_info.value)

    def test_chunked_html_failure_raises(
        self, small_analysis_data, html_report, prepare_response
    ):
        """Failed chunked HTML upload raises ApiError."""
        mock_prepare_resp = MagicMock()
        mock_prepare_resp.status_code = 201
        mock_prepare_resp.json.return_value = prepare_response

        mock_html_result = MagicMock()
        mock_html_result.success = False
        mock_html_result.error = "Checksum mismatch"

        with patch("src.chunked_upload.ChunkedUploadClient") as MockChunkedClient:
            mock_chunked_instance = AsyncMock()
            mock_chunked_instance.upload_report_html.return_value = mock_html_result
            MockChunkedClient.return_value = mock_chunked_instance

            api, client_instance = _make_api_client()
            client_instance.post.return_value = mock_prepare_resp

            with pytest.raises(ApiError) as exc_info:
                asyncio.run(api.upload_result(
                    result_id="uuid-001",
                    collection_guid="col_test",
                    tool="photostats",
                    executed_at="2026-01-28T10:00:00Z",
                    analysis_data=small_analysis_data,
                    html_report=html_report,
                ))

        assert "Chunked HTML report upload failed" in str(exc_info.value)

    def test_prepare_failure_raises(self, large_analysis_data):
        """Failed prepare call raises ApiError."""
        mock_prepare_resp = MagicMock()
        mock_prepare_resp.status_code = 404
        mock_prepare_resp.json.return_value = {"detail": "Collection not found"}

        api, client_instance = _make_api_client()
        client_instance.post.return_value = mock_prepare_resp

        with pytest.raises(ApiError) as exc_info:
            asyncio.run(api.upload_result(
                result_id="uuid-001",
                collection_guid="col_test",
                tool="photostats",
                executed_at="2026-01-28T10:00:00Z",
                analysis_data=large_analysis_data,
            ))

        assert "Collection not found" in str(exc_info.value)
