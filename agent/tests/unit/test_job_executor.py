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
