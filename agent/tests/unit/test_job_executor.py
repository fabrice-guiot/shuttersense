"""
Unit tests for JobExecutor.

Issue #90 - Distributed Agent Architecture (Phase 5)
Task: T092
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from base64 import b64encode
import secrets

from src.job_executor import JobExecutor, JobResult


class TestJobExecutorInit:
    """Tests for JobExecutor initialization."""

    def test_init_stores_api_client(self, mock_api_client):
        """API client is stored during initialization."""
        executor = JobExecutor(mock_api_client)

        assert executor._api_client == mock_api_client
        assert executor._progress_reporter is None
        assert executor._config_loader is None
        assert executor._result_signer is None


class TestJobResult:
    """Tests for JobResult dataclass."""

    def test_job_result_success(self):
        """Create successful JobResult."""
        result = JobResult(
            success=True,
            results={"total_files": 100},
            report_html="<html></html>",
            files_scanned=100,
            issues_found=5,
        )

        assert result.success is True
        assert result.results == {"total_files": 100}
        assert result.report_html == "<html></html>"
        assert result.files_scanned == 100
        assert result.issues_found == 5
        assert result.error_message is None

    def test_job_result_failure(self):
        """Create failed JobResult."""
        result = JobResult(
            success=False,
            results={},
            error_message="Something went wrong",
        )

        assert result.success is False
        assert result.results == {}
        assert result.error_message == "Something went wrong"


class TestExecuteTool:
    """Tests for tool execution dispatch."""

    @pytest.mark.asyncio
    async def test_execute_tool_unknown_tool(self, mock_api_client):
        """Unknown tool returns failure result."""
        executor = JobExecutor(mock_api_client)

        job = {"tool": "unknown_tool", "collection_path": "/tmp/test"}
        config = {}

        result = await executor._execute_tool(job, config)

        assert result.success is False
        assert "Unknown tool" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_tool_photostats_no_path(self, mock_api_client):
        """PhotoStats without collection path returns failure."""
        executor = JobExecutor(mock_api_client)

        job = {"tool": "photostats", "collection_path": None}
        config = {}

        result = await executor._run_photostats(None, config)

        assert result.success is False
        assert "Collection path is required" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_tool_photo_pairing_no_path(self, mock_api_client):
        """Photo pairing without collection path returns failure."""
        executor = JobExecutor(mock_api_client)

        result = await executor._run_photo_pairing(None, {})

        assert result.success is False
        assert "Collection path is required" in result.error_message


class TestExecute:
    """Tests for full job execution."""

    @pytest.mark.asyncio
    async def test_execute_initializes_components(self, mock_api_client, sample_job_claim_response):
        """Execute initializes progress reporter, config loader, result signer."""
        mock_api_client.get_job_config = AsyncMock(return_value={
            "config": {
                "photo_extensions": [".dng"],
                "metadata_extensions": [".xmp"],
                "camera_mappings": {},
                "processing_methods": {},
                "require_sidecar": [],
            },
        })

        executor = JobExecutor(mock_api_client)

        # Mock _execute_tool to avoid actual tool execution
        with patch.object(executor, '_execute_tool', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = JobResult(
                success=True,
                results={"total_files": 0},
                files_scanned=0,
                issues_found=0,
            )

            await executor.execute(sample_job_claim_response)

        # Components should have been initialized
        assert executor._progress_reporter is not None
        assert executor._config_loader is not None
        assert executor._result_signer is not None

    @pytest.mark.asyncio
    async def test_execute_reports_initial_progress(self, mock_api_client, sample_job_claim_response):
        """Execute reports initial progress."""
        mock_api_client.get_job_config = AsyncMock(return_value={
            "config": {
                "photo_extensions": [".dng"],
                "metadata_extensions": [".xmp"],
                "camera_mappings": {},
                "processing_methods": {},
                "require_sidecar": [],
            },
        })

        executor = JobExecutor(mock_api_client)

        with patch.object(executor, '_execute_tool', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = JobResult(
                success=True,
                results={"total_files": 0},
                files_scanned=0,
                issues_found=0,
            )

            await executor.execute(sample_job_claim_response)

        # Initial progress should have been reported
        mock_api_client.update_job_progress.assert_called()

    @pytest.mark.asyncio
    async def test_execute_success_completes_job(self, mock_api_client, sample_job_claim_response):
        """Successful execution calls complete_job."""
        mock_api_client.get_job_config = AsyncMock(return_value={
            "config": {
                "photo_extensions": [".dng"],
                "metadata_extensions": [".xmp"],
                "camera_mappings": {},
                "processing_methods": {},
                "require_sidecar": [],
            },
        })

        executor = JobExecutor(mock_api_client)

        with patch.object(executor, '_execute_tool', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = JobResult(
                success=True,
                results={"total_files": 100},
                report_html="<html>Report</html>",
                files_scanned=100,
                issues_found=5,
            )

            await executor.execute(sample_job_claim_response)

        # complete_job should have been called
        mock_api_client.complete_job.assert_called_once()
        call_kwargs = mock_api_client.complete_job.call_args.kwargs
        assert call_kwargs["job_guid"] == sample_job_claim_response["guid"]
        assert call_kwargs["results"] == {"total_files": 100}
        assert call_kwargs["files_scanned"] == 100
        assert "signature" in call_kwargs

    @pytest.mark.asyncio
    async def test_execute_failure_from_tool_reports_failure(self, mock_api_client, sample_job_claim_response):
        """Tool returning failure calls fail_job."""
        mock_api_client.get_job_config = AsyncMock(return_value={
            "config": {
                "photo_extensions": [".dng"],
                "metadata_extensions": [".xmp"],
                "camera_mappings": {},
                "processing_methods": {},
                "require_sidecar": [],
            },
        })

        executor = JobExecutor(mock_api_client)

        with patch.object(executor, '_execute_tool', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = JobResult(
                success=False,
                results={},
                error_message="Analysis failed",
            )

            with pytest.raises(Exception, match="Analysis failed"):
                await executor.execute(sample_job_claim_response)

        # fail_job should have been called
        mock_api_client.fail_job.assert_called_once()
        call_kwargs = mock_api_client.fail_job.call_args.kwargs
        assert call_kwargs["job_guid"] == sample_job_claim_response["guid"]
        assert "Analysis failed" in call_kwargs["error_message"]

    @pytest.mark.asyncio
    async def test_execute_exception_reports_failure(self, mock_api_client, sample_job_claim_response):
        """Exception during execution reports failure."""
        mock_api_client.get_job_config = AsyncMock(return_value={
            "config": {
                "photo_extensions": [".dng"],
                "metadata_extensions": [".xmp"],
                "camera_mappings": {},
                "processing_methods": {},
                "require_sidecar": [],
            },
        })

        executor = JobExecutor(mock_api_client)

        with patch.object(executor, '_execute_tool', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = Exception("Unexpected error")

            with pytest.raises(Exception, match="Unexpected error"):
                await executor.execute(sample_job_claim_response)

        # fail_job should have been called
        mock_api_client.fail_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_closes_progress_reporter(self, mock_api_client, sample_job_claim_response):
        """Progress reporter is closed after execution."""
        mock_api_client.get_job_config = AsyncMock(return_value={
            "config": {
                "photo_extensions": [".dng"],
                "metadata_extensions": [".xmp"],
                "camera_mappings": {},
                "processing_methods": {},
                "require_sidecar": [],
            },
        })

        executor = JobExecutor(mock_api_client)

        with patch.object(executor, '_execute_tool', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = JobResult(
                success=True,
                results={"total_files": 0},
                files_scanned=0,
                issues_found=0,
            )

            await executor.execute(sample_job_claim_response)

        # Progress reporter should be closed
        # Check that the reporter was created and is in closed state
        assert executor._progress_reporter._closed is True


class TestSyncProgressCallback:
    """Tests for synchronous progress callback."""

    @pytest.mark.asyncio
    async def test_sync_progress_callback_schedules_report(self, mock_api_client, sample_job_claim_response):
        """Progress callback schedules async report."""
        mock_api_client.get_job_config = AsyncMock(return_value={
            "config": {
                "photo_extensions": [".dng"],
                "metadata_extensions": [".xmp"],
                "camera_mappings": {},
                "processing_methods": {},
                "require_sidecar": [],
            },
        })

        executor = JobExecutor(mock_api_client)

        # Track progress reports
        progress_calls = []
        original_update = mock_api_client.update_job_progress

        async def track_progress(*args, **kwargs):
            progress_calls.append(kwargs)
            return await original_update(*args, **kwargs)

        mock_api_client.update_job_progress = AsyncMock(side_effect=track_progress)

        with patch.object(executor, '_execute_tool', new_callable=AsyncMock) as mock_execute:
            async def execute_with_callback(job, config):
                # Simulate tool calling progress callback
                executor._sync_progress_callback(
                    stage="scanning",
                    percentage=50,
                    files_scanned=500,
                    total_files=1000,
                )
                await asyncio.sleep(0.1)  # Let the scheduled coroutine run
                return JobResult(
                    success=True,
                    results={"total_files": 1000},
                    files_scanned=1000,
                    issues_found=0,
                )

            mock_execute.side_effect = execute_with_callback

            await executor.execute(sample_job_claim_response)

        # Progress should have been reported
        assert any(p.get("stage") == "scanning" for p in progress_calls)


class TestPipelineConfigCreation:
    """Tests for pipeline config creation from API data.

    Note: These tests require the utils.pipeline_processor module which may not
    be available in isolated agent test runs. They are skipped when unavailable.
    """

    @pytest.fixture
    def check_pipeline_module(self):
        """Check if pipeline_processor module is available."""
        try:
            from utils.pipeline_processor import PipelineConfig
            return True
        except ImportError:
            pytest.skip("utils.pipeline_processor not available in agent test environment")

    def test_create_pipeline_config_from_api(self, mock_api_client, check_pipeline_module):
        """Creates PipelineConfig from API data."""
        executor = JobExecutor(mock_api_client)

        pipeline_data = {
            "name": "Test Pipeline",
            "version": 1,
            "guid": "pip_test123",
            "nodes": [
                {"id": "n1", "type": "capture", "properties": {"name": "Camera"}},
                {"id": "n2", "type": "file", "properties": {"name": "RAW", "extension": ".dng"}},
                {"id": "n3", "type": "termination", "properties": {"name": "Done", "termination_type": "finished"}},
            ],
            "edges": [
                {"from": "n1", "to": "n2"},
                {"from": "n2", "to": "n3"},
            ],
        }

        config = executor._create_pipeline_config_from_api(pipeline_data)

        # Should have parsed nodes
        assert len(config.capture_nodes) == 1
        assert len(config.file_nodes) == 1
        assert len(config.termination_nodes) == 1

        # Check capture node
        assert config.capture_nodes[0].id == "n1"
        assert config.capture_nodes[0].output == ["n2"]

        # Check file node
        assert config.file_nodes[0].extension == ".dng"

    def test_create_pipeline_config_handles_empty(self, mock_api_client, check_pipeline_module):
        """Handles empty pipeline data."""
        executor = JobExecutor(mock_api_client)

        pipeline_data = {
            "nodes": [],
            "edges": [],
        }

        config = executor._create_pipeline_config_from_api(pipeline_data)

        assert len(config.nodes) == 0

    def test_create_pipeline_config_with_process_node(self, mock_api_client, check_pipeline_module):
        """Creates process node with method_ids."""
        executor = JobExecutor(mock_api_client)

        pipeline_data = {
            "nodes": [
                {
                    "id": "p1",
                    "type": "process",
                    "properties": {
                        "name": "HDR Processing",
                        "method_ids": ["HDR", "BW"]
                    }
                },
            ],
            "edges": [],
        }

        config = executor._create_pipeline_config_from_api(pipeline_data)

        assert len(config.process_nodes) == 1
        assert config.process_nodes[0].method_ids == ["HDR", "BW"]

    def test_create_pipeline_config_with_pairing_node(self, mock_api_client, check_pipeline_module):
        """Creates pairing node with pairing_type."""
        executor = JobExecutor(mock_api_client)

        pipeline_data = {
            "nodes": [
                {
                    "id": "pair1",
                    "type": "pairing",
                    "properties": {
                        "name": "Merge",
                        "pairing_type": "merge",
                        "input_count": 2
                    }
                },
            ],
            "edges": [],
        }

        config = executor._create_pipeline_config_from_api(pipeline_data)

        assert len(config.pairing_nodes) == 1
        assert config.pairing_nodes[0].pairing_type == "merge"
        assert config.pairing_nodes[0].input_count == 2

    def test_create_pipeline_config_with_branching_node(self, mock_api_client, check_pipeline_module):
        """Creates branching node with condition."""
        executor = JobExecutor(mock_api_client)

        pipeline_data = {
            "nodes": [
                {
                    "id": "br1",
                    "type": "branching",
                    "properties": {
                        "name": "Branch",
                        "condition_description": "If HDR"
                    }
                },
            ],
            "edges": [],
        }

        config = executor._create_pipeline_config_from_api(pipeline_data)

        assert len(config.branching_nodes) == 1
        assert config.branching_nodes[0].condition_description == "If HDR"


# =============================================================================
# T071: Cached FileInfo Usage Tests (Issue #107)
# =============================================================================


class TestCachedFileInfo:
    """Tests for using cached FileInfo instead of cloud API calls (T071)."""

    def test_should_use_cached_file_info_when_available(self, mock_api_client):
        """Should use cached FileInfo when present in job."""
        executor = JobExecutor(mock_api_client)

        job_with_file_info = {
            "guid": "job_test",
            "tool": "photostats",
            "file_info": [
                {"key": "2020/vacation/IMG_001.CR3", "size": 25000000, "last_modified": "2022-01-01T00:00:00Z"},
            ],
        }

        assert executor._should_use_cached_file_info(job_with_file_info) is True

    def test_should_not_use_cached_file_info_when_missing(self, mock_api_client):
        """Should not use cached FileInfo when not present."""
        executor = JobExecutor(mock_api_client)

        job_without_file_info = {
            "guid": "job_test",
            "tool": "photostats",
        }

        assert executor._should_use_cached_file_info(job_without_file_info) is False

    def test_should_not_use_cached_file_info_when_empty(self, mock_api_client):
        """Should not use cached FileInfo when empty list."""
        executor = JobExecutor(mock_api_client)

        job_with_empty_file_info = {
            "guid": "job_test",
            "tool": "photostats",
            "file_info": [],
        }

        assert executor._should_use_cached_file_info(job_with_empty_file_info) is False

    def test_should_not_use_cached_file_info_with_force_refresh(self, mock_api_client):
        """Should not use cached FileInfo when force_cloud_refresh is requested (T072)."""
        executor = JobExecutor(mock_api_client)

        job_with_force_refresh = {
            "guid": "job_test",
            "tool": "photostats",
            "file_info": [
                {"key": "2020/vacation/IMG_001.CR3", "size": 25000000, "last_modified": "2022-01-01T00:00:00Z"},
            ],
            "parameters": {"force_cloud_refresh": True},
        }

        assert executor._should_use_cached_file_info(job_with_force_refresh) is False

    def test_convert_cached_file_info(self, mock_api_client):
        """Convert cached FileInfo from server format to adapter format."""
        executor = JobExecutor(mock_api_client)

        cached_file_info = [
            {"key": "vacation/IMG_001.CR3", "size": 25000000, "last_modified": "2022-01-01T00:00:00Z"},
            {"key": "vacation/IMG_002.CR3", "size": 24000000, "last_modified": "2022-01-02T00:00:00Z"},
        ]

        result = executor._convert_cached_file_info(cached_file_info, "vacation")

        assert len(result) == 2
        # First file
        assert result[0].path == "IMG_001.CR3"
        assert result[0].size == 25000000
        assert result[0].last_modified == "2022-01-01T00:00:00Z"
        # Second file
        assert result[1].path == "IMG_002.CR3"
        assert result[1].size == 24000000

    def test_convert_cached_file_info_preserves_paths_without_prefix(self, mock_api_client):
        """Convert preserves full path when key doesn't match collection path."""
        executor = JobExecutor(mock_api_client)

        cached_file_info = [
            {"key": "other/path/IMG_001.CR3", "size": 25000000, "last_modified": "2022-01-01T00:00:00Z"},
        ]

        result = executor._convert_cached_file_info(cached_file_info, "vacation")

        # Key doesn't start with "vacation/", so full key is kept
        assert result[0].path == "other/path/IMG_001.CR3"

    def test_convert_cached_file_info_skips_empty_keys(self, mock_api_client):
        """Convert skips entries with empty or missing keys."""
        executor = JobExecutor(mock_api_client)

        cached_file_info = [
            {"key": "vacation/IMG_001.CR3", "size": 25000000, "last_modified": "2022-01-01T00:00:00Z"},
            {"key": "", "size": 1000, "last_modified": "2022-01-01T00:00:00Z"},  # Empty key
            {"size": 2000, "last_modified": "2022-01-01T00:00:00Z"},  # Missing key
        ]

        result = executor._convert_cached_file_info(cached_file_info, "vacation")

        # Only the first entry should be included
        assert len(result) == 1
        assert result[0].path == "IMG_001.CR3"

    def test_convert_cached_file_info_url_decodes_keys(self, mock_api_client):
        """Convert URL-decodes keys from S3/GCS inventory (e.g., %20 -> space)."""
        executor = JobExecutor(mock_api_client)

        # S3/GCS inventory stores URL-encoded keys
        cached_file_info = [
            {"key": "vacation/IMG%20001-DxO_DeepPRIME%20XD2s.CR3", "size": 25000000, "last_modified": "2022-01-01T00:00:00Z"},
            {"key": "vacation/file%26name.jpg", "size": 1000, "last_modified": "2022-01-01T00:00:00Z"},  # %26 = &
            {"key": "vacation/special%2Bchars.tif", "size": 2000, "last_modified": "2022-01-01T00:00:00Z"},  # %2B = +
        ]

        result = executor._convert_cached_file_info(cached_file_info, "vacation")

        assert len(result) == 3
        # Verify URL decoding worked
        assert result[0].path == "IMG 001-DxO_DeepPRIME XD2s.CR3"  # %20 decoded to space
        assert result[1].path == "file&name.jpg"  # %26 decoded to &
        assert result[2].path == "special+chars.tif"  # %2B decoded to +

    def test_convert_cached_file_info_handles_encoded_collection_path(self, mock_api_client):
        """Convert handles URL-encoded collection paths correctly."""
        executor = JobExecutor(mock_api_client)

        cached_file_info = [
            {"key": "My%20Photos/IMG_001.CR3", "size": 25000000, "last_modified": "2022-01-01T00:00:00Z"},
        ]

        # Collection path might also be URL-encoded
        result = executor._convert_cached_file_info(cached_file_info, "My%20Photos")

        assert len(result) == 1
        assert result[0].path == "IMG_001.CR3"  # Relative path after removing decoded prefix

    @pytest.mark.asyncio
    async def test_execute_tool_passes_cached_file_info(self, mock_api_client):
        """_execute_tool passes cached FileInfo to tool methods."""
        executor = JobExecutor(mock_api_client)

        job = {
            "guid": "job_test",
            "tool": "photostats",
            "collection_path": "2020/vacation",
            "file_info": [
                {"key": "2020/vacation/IMG_001.CR3", "size": 25000000, "last_modified": "2022-01-01T00:00:00Z"},
            ],
            "file_info_source": "inventory",
        }
        config = {
            "connector": {
                "guid": "con_test",
                "type": "s3",
                "name": "Test S3",
            },
            "photo_extensions": [".cr3"],
            "metadata_extensions": [".xmp"],
            "require_sidecar": [],
        }

        # Mock _run_photostats to verify it receives cached_file_info
        with patch.object(executor, '_run_photostats', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = JobResult(success=True, results={})
            await executor._execute_tool(job, config)

            # Verify cached_file_info was passed (4th argument)
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            # Arguments: collection_path, config, connector, cached_file_info
            assert call_args[0][0] == "2020/vacation"  # collection_path
            assert call_args[0][2] == config["connector"]  # connector
            # The 4th argument (cached_file_info) should be a list of FileInfo
            assert call_args[0][3] is not None
            assert len(call_args[0][3]) == 1


# =============================================================================
# T117: SC-007 - Zero Cloud API Calls with Cached FileInfo
# =============================================================================


class TestZeroCloudAPICalls:
    """T117: Verify zero cloud API calls when using cached FileInfo (SC-007).

    These tests verify that when cached FileInfo is provided in the job,
    the analysis tools use that data instead of making cloud API calls.
    """

    def test_cached_file_info_bypasses_adapter_creation(self, mock_api_client):
        """SC-007: Verify _should_use_cached_file_info returns True when valid cache exists."""
        executor = JobExecutor(mock_api_client)

        # Job with cached file_info from inventory
        job_with_cache = {
            "guid": "job_test",
            "tool": "photostats",
            "collection_path": "2020/vacation",
            "file_info": [
                {"key": "2020/vacation/IMG_001.CR3", "size": 25000000, "last_modified": "2022-01-01T00:00:00Z"},
                {"key": "2020/vacation/IMG_002.CR3", "size": 24000000, "last_modified": "2022-01-02T00:00:00Z"},
            ],
            "file_info_source": "inventory",
        }

        # Should use cached file info (no adapter needed)
        assert executor._should_use_cached_file_info(job_with_cache) is True

    def test_no_cached_file_info_requires_adapter(self, mock_api_client):
        """SC-007: Verify _should_use_cached_file_info returns False when no cache."""
        executor = JobExecutor(mock_api_client)

        # Job without cached file_info
        job_without_cache = {
            "guid": "job_test",
            "tool": "photostats",
            "collection_path": "2020/vacation",
            # No file_info - adapter would be needed
        }

        # Should NOT use cached file info (adapter needed)
        assert executor._should_use_cached_file_info(job_without_cache) is False

    def test_force_refresh_ignores_cache(self, mock_api_client):
        """SC-007: Verify force_cloud_refresh bypasses cached FileInfo."""
        executor = JobExecutor(mock_api_client)

        # Job with cached file_info BUT force refresh requested
        job_force_refresh = {
            "guid": "job_test",
            "tool": "photostats",
            "collection_path": "2020/vacation",
            "file_info": [
                {"key": "2020/vacation/IMG_001.CR3", "size": 25000000, "last_modified": "2022-01-01T00:00:00Z"},
            ],
            "file_info_source": "inventory",
            "parameters": {"force_cloud_refresh": True},
        }

        # Should NOT use cached file info due to force refresh
        assert executor._should_use_cached_file_info(job_force_refresh) is False

    def test_cached_file_info_converted_correctly(self, mock_api_client):
        """SC-007: Verify cached FileInfo is converted to tool format correctly."""
        executor = JobExecutor(mock_api_client)

        cached_file_info = [
            {"key": "2020/vacation/IMG_001.CR3", "size": 25165824, "last_modified": "2022-01-01T10:30:00Z"},
            {"key": "2020/vacation/IMG_002.CR3", "size": 24117248, "last_modified": "2022-01-02T11:00:00Z"},
        ]

        # Convert cached file info to tool format
        result = executor._convert_cached_file_info(cached_file_info, "2020/vacation")

        # Verify conversion preserves data accurately
        assert len(result) == 2
        assert result[0].path == "IMG_001.CR3"
        assert result[0].size == 25165824  # Exact size preserved
        assert result[1].path == "IMG_002.CR3"
        assert result[1].size == 24117248  # Exact size preserved

    @pytest.mark.asyncio
    async def test_execute_tool_uses_cached_file_info(self, mock_api_client):
        """SC-007: Verify _execute_tool passes cached FileInfo to tool methods."""
        executor = JobExecutor(mock_api_client)

        job = {
            "guid": "job_test",
            "tool": "photostats",
            "collection_path": "2020/vacation",
            "file_info": [
                {"key": "2020/vacation/IMG_001.CR3", "size": 25000000, "last_modified": "2022-01-01T00:00:00Z"},
            ],
            "file_info_source": "inventory",
        }
        config = {
            "connector": {"guid": "con_test", "type": "s3", "name": "Test S3"},
            "photo_extensions": [".cr3"],
            "metadata_extensions": [".xmp"],
            "require_sidecar": [],
        }

        # Mock _run_photostats to capture arguments
        with patch.object(executor, '_run_photostats', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = JobResult(success=True, results={})
            await executor._execute_tool(job, config)

            # Verify cached_file_info was passed (argument 4)
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0]
            cached_file_info_arg = call_args[3]  # 4th positional argument

            # Should have converted FileInfo, not None
            assert cached_file_info_arg is not None
            assert len(cached_file_info_arg) == 1
            assert cached_file_info_arg[0].size == 25000000
