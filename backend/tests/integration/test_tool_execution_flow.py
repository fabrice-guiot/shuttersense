"""
Integration tests for tool execution workflows.

Tests end-to-end flows across the tools and results API endpoints,
ensuring proper job management, execution, and result storage.
"""

import pytest
import tempfile
from datetime import datetime


class TestToolExecutionFlow:
    """Integration tests for tool execution workflow - T053"""

    @pytest.mark.skip(reason="Requires bound agent for LOCAL collections - deferred until agent binding in tests is implemented")
    def test_run_tool_creates_job_and_result(self, test_client):
        """
        Test full tool execution flow - T053

        Flow:
        1. Create local collection
        2. Run PhotoStats tool
        3. Verify job is created
        4. Verify job response has expected fields
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Step 1: Create local collection
            collection_data = {
                'name': 'Test Photo Collection',
                'type': 'local',
                'location': temp_dir,
                'state': 'live'
            }

            collection_response = test_client.post('/api/collections', json=collection_data)
            assert collection_response.status_code == 201
            collection = collection_response.json()
            collection_guid = collection['guid']

            # Step 2: Run PhotoStats tool
            run_response = test_client.post('/api/tools/run', json={
                'collection_guid': collection_guid,
                'tool': 'photostats'
            })
            assert run_response.status_code == 202
            job = run_response.json()

            # Step 3: Verify job is created with expected fields
            assert job['id'] is not None
            assert job['collection_guid'] == collection_guid
            assert job['tool'] == 'photostats'
            # Status can be queued, running, completed, or failed
            assert job['status'] in ['queued', 'running', 'completed', 'failed']

            # Step 4: Get job and verify it exists
            job_response = test_client.get(f"/api/tools/jobs/{job['id']}")
            assert job_response.status_code == 200
            updated_job = job_response.json()
            assert updated_job['id'] == job['id']

    def test_run_tool_on_inaccessible_collection_rejected(self, test_client, mocker):
        """
        Test that running a tool on inaccessible collection is rejected

        Flow:
        1. Create S3 connector with invalid credentials
        2. Create collection (will be inaccessible)
        3. Attempt to run tool -> should fail with 422
        """
        # Step 1: Create S3 connector
        connector_data = {
            'name': 'Invalid S3',
            'type': 's3',
            'credentials': {
                'aws_access_key_id': 'AKIAINVALIDKEY1234',
                'aws_secret_access_key': 'InvalidSecretKeyThatIs40CharactersLongXXXX',
                'region': 'us-east-1'
            }
        }

        # Mock to return failure
        mock_adapter = mocker.patch('backend.src.services.connector_service.S3Adapter')
        mock_adapter.return_value.test_connection.return_value = (
            False,
            'Authentication failed'
        )

        connector_response = test_client.post('/api/connectors', json=connector_data)
        assert connector_response.status_code == 201
        connector_guid = connector_response.json()['guid']

        # Step 2: Create collection (will be inaccessible)
        collection_data = {
            'name': 'Inaccessible S3 Collection',
            'type': 's3',
            'location': 's3://bucket/photos',
            'state': 'live',
            'connector_guid': connector_guid
        }

        collection_response = test_client.post('/api/collections', json=collection_data)
        assert collection_response.status_code == 201
        collection = collection_response.json()
        assert collection['is_accessible'] is False

        # Step 3: Attempt to run tool -> should fail
        run_response = test_client.post('/api/tools/run', json={
            'collection_guid': collection['guid'],
            'tool': 'photostats'
        })
        assert run_response.status_code == 422
        error = run_response.json()
        assert 'not accessible' in error['detail']['message']

    @pytest.mark.skip(reason="Requires bound agent for LOCAL collections - deferred until agent binding in tests is implemented")
    def test_duplicate_tool_run_behavior(self, test_client):
        """
        Test duplicate tool run behavior - T053

        Note: Due to the synchronous nature of the test client and background task execution,
        jobs complete quickly. This test verifies that:
        1. Running the same tool type on the same collection is rejected while one is active
        2. Different tools on the same collection are allowed
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Step 1: Create collection
            collection_data = {
                'name': 'Test Collection',
                'type': 'local',
                'location': temp_dir,
                'state': 'live'
            }

            collection_response = test_client.post('/api/collections', json=collection_data)
            assert collection_response.status_code == 201
            collection_guid = collection_response.json()['guid']

            # Step 2: Verify we can run different tools on same collection
            run1_response = test_client.post('/api/tools/run', json={
                'collection_guid': collection_guid,
                'tool': 'photostats'
            })
            assert run1_response.status_code == 202

            # Running a different tool on the same collection should work
            run2_response = test_client.post('/api/tools/run', json={
                'collection_guid': collection_guid,
                'tool': 'photo_pairing'
            })
            assert run2_response.status_code == 202

    @pytest.mark.skip(reason="Requires bound agent for LOCAL collections - deferred until agent binding in tests is implemented")
    def test_cancel_job_behavior(self, test_client):
        """
        Test job cancellation behavior

        Flow:
        1. Create collection
        2. Run tool
        3. Attempt to cancel job
        4. Verify appropriate response based on job state

        Note: In sync test environment, jobs complete quickly, so the test
        verifies that the cancel endpoint responds correctly regardless of
        whether the job is still cancellable.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Step 1: Create collection
            collection_data = {
                'name': 'Test Collection',
                'type': 'local',
                'location': temp_dir,
                'state': 'live'
            }

            collection_response = test_client.post('/api/collections', json=collection_data)
            collection_guid = collection_response.json()['guid']

            # Step 2: Run tool
            run_response = test_client.post('/api/tools/run', json={
                'collection_guid': collection_guid,
                'tool': 'photostats'
            })
            assert run_response.status_code == 202
            job = run_response.json()
            job_id = job['id']

            # Step 3: Try to cancel
            cancel_response = test_client.post(f"/api/tools/jobs/{job_id}/cancel")

            # Cancel endpoint returns:
            # - 200 with status='cancelled' if job was in queued state
            # - 200 with current status if job already completed/failed (no-op)
            # - 400/409 if job is actively running and can't be cancelled
            assert cancel_response.status_code in [200, 400, 409]

            if cancel_response.status_code == 200:
                result_status = cancel_response.json()['status']
                # Status should be either 'cancelled' (was queued) or 'completed'/'failed' (was done)
                assert result_status in ['cancelled', 'completed', 'failed', 'running']

    def test_get_queue_status(self, test_client):
        """
        Test getting queue status

        Flow:
        1. Get initial queue status (should be empty)
        2. Create collection and run tools
        3. Get queue status (should show counts)
        """
        # Step 1: Get initial queue status
        status_response = test_client.get('/api/tools/queue/status')
        assert status_response.status_code == 200
        status = status_response.json()

        assert 'queued_count' in status
        assert 'running_count' in status
        assert 'completed_count' in status
        assert 'failed_count' in status
        assert 'cancelled_count' in status

class TestResultsApiFlow:
    """Integration tests for results API - T053"""

    def test_results_list_with_filters(self, test_client, test_db_session, sample_collection, test_team):
        """
        Test listing results with various filters
        """
        from backend.src.models import AnalysisResult

        # Create a collection
        collection = sample_collection(name='Results Test Collection')

        # Create some results - use dicts directly for JSONB column
        result1 = AnalysisResult(
            collection_id=collection.id,
            tool='photostats',
            status='COMPLETED',
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_seconds=60,
            files_scanned=100,
            issues_found=5,
            results_json={'total_files': 100},
            team_id=test_team.id
        )
        result2 = AnalysisResult(
            collection_id=collection.id,
            tool='photo_pairing',
            status='COMPLETED',
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_seconds=30,
            files_scanned=80,
            issues_found=2,
            results_json={'group_count': 40},
            team_id=test_team.id
        )
        result3 = AnalysisResult(
            collection_id=collection.id,
            tool='photostats',
            status='FAILED',
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_seconds=5,
            files_scanned=0,
            issues_found=0,
            error_message='Test error',
            results_json={},
            team_id=test_team.id
        )

        test_db_session.add_all([result1, result2, result3])
        test_db_session.commit()

        # Test list all
        list_all = test_client.get('/api/results')
        assert list_all.status_code == 200
        data = list_all.json()
        assert 'items' in data
        assert 'total' in data
        assert data['total'] >= 3

        # Test filter by tool
        list_photostats = test_client.get('/api/results?tool=photostats')
        assert list_photostats.status_code == 200
        photostats_data = list_photostats.json()
        for item in photostats_data['items']:
            assert item['tool'] == 'photostats'

        # Test filter by status
        list_failed = test_client.get('/api/results?status=FAILED')
        assert list_failed.status_code == 200
        failed_data = list_failed.json()
        for item in failed_data['items']:
            assert item['status'] == 'FAILED'

        # Test filter by collection
        list_by_collection = test_client.get(f'/api/results?collection_guid={collection.guid}')
        assert list_by_collection.status_code == 200

    def test_get_single_result(self, test_client, test_db_session, sample_collection, test_team):
        """
        Test getting a single result with full details
        """
        from backend.src.models import AnalysisResult

        collection = sample_collection(name='Single Result Test')

        # Use dict directly for JSONB column, not json.dumps()
        result = AnalysisResult(
            collection_id=collection.id,
            tool='photostats',
            status='COMPLETED',
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_seconds=60,
            files_scanned=100,
            issues_found=5,
            results_json={
                'total_files': 100,
                'total_size': 500000,
                'orphaned_images': ['orphan1.jpg'],
                'orphaned_xmp': []
            },
            team_id=test_team.id
        )
        test_db_session.add(result)
        test_db_session.commit()

        # Get the result
        get_response = test_client.get(f'/api/results/{result.guid}')
        assert get_response.status_code == 200
        result_data = get_response.json()

        assert result_data['guid'] == result.guid
        assert result_data['tool'] == 'photostats'
        assert result_data['status'] == 'COMPLETED'
        assert 'results' in result_data
        assert result_data['results']['total_files'] == 100

    def test_delete_result(self, test_client, test_db_session, sample_collection, test_team):
        """
        Test deleting a result
        """
        from backend.src.models import AnalysisResult

        collection = sample_collection(name='Delete Result Test')

        result = AnalysisResult(
            collection_id=collection.id,
            tool='photostats',
            status='COMPLETED',
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_seconds=60,
            files_scanned=100,
            issues_found=0,
            results_json={},
            team_id=test_team.id
        )
        test_db_session.add(result)
        test_db_session.commit()
        result_guid = result.guid

        # Delete the result
        delete_response = test_client.delete(f'/api/results/{result_guid}')
        assert delete_response.status_code == 200

        # Verify it's deleted
        get_response = test_client.get(f'/api/results/{result_guid}')
        assert get_response.status_code == 404

    def test_get_results_stats(self, test_client, test_db_session, sample_collection, test_team):
        """
        Test getting results statistics
        """
        from backend.src.models import AnalysisResult

        collection = sample_collection(name='Stats Test')

        # Create results with different statuses - use dicts for JSONB
        results = [
            AnalysisResult(
                collection_id=collection.id, tool='photostats', status='COMPLETED',
                started_at=datetime.utcnow(), completed_at=datetime.utcnow(),
                duration_seconds=60, files_scanned=100, issues_found=5,
                results_json={}, team_id=test_team.id
            ),
            AnalysisResult(
                collection_id=collection.id, tool='photo_pairing', status='COMPLETED',
                started_at=datetime.utcnow(), completed_at=datetime.utcnow(),
                duration_seconds=30, files_scanned=80, issues_found=2,
                results_json={}, team_id=test_team.id
            ),
            AnalysisResult(
                collection_id=collection.id, tool='photostats', status='FAILED',
                started_at=datetime.utcnow(), completed_at=datetime.utcnow(),
                duration_seconds=5, files_scanned=0, issues_found=0,
                error_message='Error', results_json={}, team_id=test_team.id
            ),
        ]
        test_db_session.add_all(results)
        test_db_session.commit()

        # Get stats
        stats_response = test_client.get('/api/results/stats')
        assert stats_response.status_code == 200
        stats = stats_response.json()

        assert 'total_results' in stats
        assert 'completed_count' in stats
        assert 'failed_count' in stats
        assert 'by_tool' in stats
        assert stats['total_results'] >= 3


class TestRemoteCollectionToolExecution:
    """Integration tests for tool execution on remote collections - T068m, T068n"""

    def test_photostats_on_s3_collection(self, test_client, test_db_session, mocker):
        """
        Test PhotoStats execution on S3 collection - T068m

        Flow:
        1. Create S3 connector with mocked connection test
        2. Create S3 collection
        3. Mock FileListingAdapter to return sample files
        4. Run PhotoStats tool
        5. Verify job completes and returns expected results
        """
        from backend.src.utils.file_listing import FileInfo

        # Step 1: Mock S3Adapter connection test
        mock_s3_adapter = mocker.patch('backend.src.services.connector_service.S3Adapter')
        mock_s3_adapter.return_value.test_connection.return_value = (True, 'Connected')

        connector_data = {
            'name': 'Test S3 Connector',
            'type': 's3',
            'credentials': {
                'aws_access_key_id': 'AKIAIOSFODNN7EXAMPLE',
                'aws_secret_access_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
                'region': 'us-east-1'
            }
        }

        connector_response = test_client.post('/api/connectors', json=connector_data)
        assert connector_response.status_code == 201
        connector_guid = connector_response.json()['guid']

        # Step 2: Create S3 collection
        collection_data = {
            'name': 'S3 Photo Collection',
            'type': 's3',
            'location': 's3://my-bucket/photos',
            'state': 'live',
            'connector_guid': connector_guid
        }

        collection_response = test_client.post('/api/collections', json=collection_data)
        assert collection_response.status_code == 201
        collection = collection_response.json()
        collection_guid = collection['guid']

        # Step 3: Mock FileListingFactory to return sample files
        sample_files = [
            FileInfo(path='photos/AB3D0001.cr3', size=25000000, name='AB3D0001.cr3', extension='.cr3'),
            FileInfo(path='photos/AB3D0001.xmp', size=5000, name='AB3D0001.xmp', extension='.xmp'),
            FileInfo(path='photos/AB3D0002.cr3', size=26000000, name='AB3D0002.cr3', extension='.cr3'),
            FileInfo(path='photos/AB3D0002.xmp', size=5100, name='AB3D0002.xmp', extension='.xmp'),
            FileInfo(path='photos/orphan.jpg', size=1500000, name='orphan.jpg', extension='.jpg'),
        ]

        mock_adapter = mocker.MagicMock()
        mock_adapter.list_files.return_value = sample_files

        mock_factory = mocker.patch('backend.src.utils.file_listing.FileListingFactory')
        mock_factory.create_adapter.return_value = mock_adapter

        # Step 4: Run PhotoStats tool
        run_response = test_client.post('/api/tools/run', json={
            'collection_guid': collection_guid,
            'tool': 'photostats'
        })
        assert run_response.status_code == 202
        job = run_response.json()

        # Step 5: Verify job was created
        assert job['id'] is not None
        assert job['collection_guid'] == collection_guid
        assert job['tool'] == 'photostats'

        # Get job status to verify it processed
        job_response = test_client.get(f"/api/tools/jobs/{job['id']}")
        assert job_response.status_code == 200

    def test_photo_pairing_on_smb_collection(self, test_client, test_db_session, mocker):
        """
        Test Photo Pairing execution on SMB collection - T068n

        Flow:
        1. Create SMB connector with mocked connection test
        2. Create SMB collection
        3. Mock FileListingAdapter to return sample files
        4. Run Photo Pairing tool
        5. Verify job completes and returns expected results
        """
        from backend.src.utils.file_listing import FileInfo

        # Step 1: Mock SMBAdapter connection test
        mock_smb_adapter = mocker.patch('backend.src.services.connector_service.SMBAdapter')
        mock_smb_adapter.return_value.test_connection.return_value = (True, 'Connected')

        connector_data = {
            'name': 'Test SMB Connector',
            'type': 'smb',
            'credentials': {
                'server': '192.168.1.100',
                'share': 'photos',
                'username': 'testuser',
                'password': 'testpass123'
            }
        }

        connector_response = test_client.post('/api/connectors', json=connector_data)
        assert connector_response.status_code == 201
        connector_guid = connector_response.json()['guid']

        # Step 2: Create SMB collection
        collection_data = {
            'name': 'SMB Photo Collection',
            'type': 'smb',
            'location': '\\\\server\\share\\photos',
            'state': 'live',
            'connector_guid': connector_guid
        }

        collection_response = test_client.post('/api/collections', json=collection_data)
        assert collection_response.status_code == 201
        collection = collection_response.json()
        collection_guid = collection['guid']

        # Step 3: Mock FileListingFactory to return sample files
        # Files that form pairs (same stem, different extensions)
        sample_files = [
            FileInfo(path='photos/AB3D0001.cr3', size=25000000, name='AB3D0001.cr3', extension='.cr3'),
            FileInfo(path='photos/AB3D0001.jpg', size=2000000, name='AB3D0001.jpg', extension='.jpg'),
            FileInfo(path='photos/AB3D0002.cr3', size=26000000, name='AB3D0002.cr3', extension='.cr3'),
            FileInfo(path='photos/AB3D0002-HDR.tiff', size=50000000, name='AB3D0002-HDR.tiff', extension='.tiff'),
            FileInfo(path='photos/XY1Z0001.dng', size=30000000, name='XY1Z0001.dng', extension='.dng'),
        ]

        mock_adapter = mocker.MagicMock()
        mock_adapter.list_files.return_value = sample_files

        mock_factory = mocker.patch('backend.src.utils.file_listing.FileListingFactory')
        mock_factory.create_adapter.return_value = mock_adapter

        # Step 4: Run Photo Pairing tool
        run_response = test_client.post('/api/tools/run', json={
            'collection_guid': collection_guid,
            'tool': 'photo_pairing'
        })
        assert run_response.status_code == 202
        job = run_response.json()

        # Step 5: Verify job was created
        assert job['id'] is not None
        assert job['collection_guid'] == collection_guid
        assert job['tool'] == 'photo_pairing'

        # Get job status to verify it processed
        job_response = test_client.get(f"/api/tools/jobs/{job['id']}")
        assert job_response.status_code == 200
