"""
Unit tests for ResultService.

Tests result CRUD operations and statistics.
"""

import pytest
from datetime import datetime, date
from unittest.mock import Mock, MagicMock, patch

from sqlalchemy.orm import Session

from backend.src.models import AnalysisResult, Collection, Pipeline, ResultStatus
from backend.src.schemas.results import SortField, SortOrder
from backend.src.services.result_service import ResultService
from backend.src.services.exceptions import NotFoundError


class TestResultServiceList:
    """Tests for result listing."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = Mock(spec=Session)
        return db

    @pytest.fixture
    def sample_result(self):
        """Create sample result."""
        result = Mock(spec=AnalysisResult)
        result.id = 1
        result.guid = "res_01hgw2bbg00000000000000001"
        result.collection_id = 1
        result.tool = "photostats"
        result.pipeline_id = None
        result.pipeline_version = None  # PhotoStats runs without pipeline
        result.status = ResultStatus.COMPLETED
        result.started_at = datetime.utcnow()
        result.completed_at = datetime.utcnow()
        result.duration_seconds = 10.5
        result.files_scanned = 100
        result.issues_found = 5
        result.results_json = {"total_files": 100}
        result.report_html = "<html>Report</html>"
        result.error_message = None
        result.created_at = datetime.utcnow()
        result.has_report = True
        # Storage optimization fields (Issue #92)
        result.input_state_hash = None
        result.no_change_copy = False
        result.download_report_from = None
        # Polymorphic target (Issue #110)
        result.target_entity_type = None
        result.target_entity_id = None
        result.target_entity_guid = None
        result.target_entity_name = None
        result.context_json = None
        result.context = None
        # Connector fields (Issue #107)
        result.connector_id = None
        # Audit trail (Issue #120)
        result.audit = None
        return result

    @pytest.fixture
    def sample_collection(self):
        """Create sample collection."""
        collection = Mock(spec=Collection)
        collection.id = 1
        collection.guid = "col_01hgw2bbg00000000000000001"
        collection.name = "Test Collection"
        return collection

    def test_list_results_returns_summaries(self, mock_db, sample_result, sample_collection):
        """Test listing results returns summaries."""
        # Setup mock query chain
        mock_query = MagicMock()
        mock_query.outerjoin.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_result]

        mock_db.query.return_value = mock_query
        # For collection lookup
        mock_db.query.return_value.filter.return_value.first.return_value = sample_collection

        service = ResultService(db=mock_db)
        items, total = service.list_results(team_id=1)

        assert total == 1
        assert len(items) == 1
        assert items[0].tool == "photostats"
        assert items[0].audit is None  # No audit user set on mock

    def test_list_results_with_filters(self, mock_db):
        """Test listing results with filters."""
        mock_query = MagicMock()
        mock_query.outerjoin.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_db.query.return_value = mock_query

        service = ResultService(db=mock_db)
        items, total = service.list_results(
            team_id=1,
            collection_guid="col_01hgw2bbg00000000000000001",
            tool="photostats",
            status=ResultStatus.COMPLETED,
            from_date=date.today(),
            limit=10,
            offset=0,
            sort_by=SortField.DURATION_SECONDS,
            sort_order=SortOrder.ASC
        )

        assert total == 0
        assert len(items) == 0


class TestResultServiceGet:
    """Tests for getting result details."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def sample_result(self):
        """Create sample result."""
        result = Mock(spec=AnalysisResult)
        result.id = 1
        result.guid = "res_01hgw2bbg00000000000000001"
        result.collection_id = 1
        result.tool = "photostats"
        result.pipeline_id = None
        result.pipeline_version = None  # PhotoStats runs without pipeline
        result.status = ResultStatus.COMPLETED
        result.started_at = datetime.utcnow()
        result.completed_at = datetime.utcnow()
        result.duration_seconds = 10.5
        result.files_scanned = 100
        result.issues_found = 5
        result.results_json = {"total_files": 100}
        result.report_html = "<html>Report</html>"
        result.error_message = None
        result.created_at = datetime.utcnow()
        result.has_report = True
        # Storage optimization fields (Issue #92)
        result.input_state_hash = None
        result.no_change_copy = False
        result.download_report_from = None
        # Polymorphic target (Issue #110)
        result.target_entity_type = None
        result.target_entity_id = None
        result.target_entity_guid = None
        result.target_entity_name = None
        result.context_json = None
        result.context = None
        # Connector fields (Issue #107)
        result.connector_id = None
        # Audit trail (Issue #120)
        result.audit = None
        return result

    def test_get_result_returns_details(self, mock_db, sample_result):
        """Test getting result details."""
        collection = Mock()
        collection.name = "Test Collection"
        collection.guid = "col_01hgw2bbg00000000000000001"

        # Setup query to return result for first call, collection for second
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            sample_result,
            collection,
            None  # pipeline
        ]

        service = ResultService(db=mock_db)
        result = service.get_result(1)

        assert result.guid == sample_result.guid
        assert result.tool == "photostats"
        assert result.collection_name == "Test Collection"

    def test_get_result_not_found(self, mock_db):
        """Test 404 for non-existent result."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = ResultService(db=mock_db)
        with pytest.raises(NotFoundError):
            service.get_result(999)


class TestResultServiceDelete:
    """Tests for deleting results."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock(spec=Session)

    def test_delete_result_success(self, mock_db):
        """Test deleting a result."""
        result = Mock()
        result.id = 1
        result.guid = "res_01hgw2bbg00000000000000001"
        mock_db.query.return_value.filter.return_value.first.return_value = result

        service = ResultService(db=mock_db)
        deleted_guid = service.delete_result(1)

        assert deleted_guid == result.guid
        mock_db.delete.assert_called_once_with(result)
        mock_db.commit.assert_called_once()

    def test_delete_result_not_found(self, mock_db):
        """Test 404 when deleting non-existent result."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = ResultService(db=mock_db)
        with pytest.raises(NotFoundError):
            service.delete_result(999)


class TestResultServiceReport:
    """Tests for report retrieval."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock(spec=Session)

    def test_get_report_success(self, mock_db):
        """Test getting HTML report."""
        result = Mock()
        result.report_html = "<html><body>Report</body></html>"
        mock_db.query.return_value.filter.return_value.first.return_value = result

        service = ResultService(db=mock_db)
        report = service.get_report(1)

        assert report == "<html><body>Report</body></html>"

    def test_get_report_not_found(self, mock_db):
        """Test 404 for missing report."""
        result = Mock()
        result.report_html = None
        result.download_report_from = None  # Required for NO_CHANGE lookup logic
        mock_db.query.return_value.filter.return_value.first.return_value = result

        service = ResultService(db=mock_db)
        with pytest.raises(NotFoundError):
            service.get_report(1)


class TestResultServiceStats:
    """Tests for statistics."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = Mock(spec=Session)

        # Create separate mock query chains for each call
        count_query1 = MagicMock()
        count_query1.scalar.return_value = 50

        count_query2 = MagicMock()
        count_query2.filter.return_value.scalar.return_value = 45

        count_query3 = MagicMock()
        count_query3.filter.return_value.scalar.return_value = 5

        group_query = MagicMock()
        group_query.group_by.return_value.all.return_value = [
            ("photostats", 25),
            ("photo_pairing", 15),
            ("pipeline_validation", 10),
        ]

        last_result = Mock()
        last_result.completed_at = datetime.utcnow()
        order_query = MagicMock()
        order_query.order_by.return_value.first.return_value = last_result

        return db

    def test_get_stats_integration(self, test_db_session, test_team):
        """Test getting statistics with real database."""
        service = ResultService(db=test_db_session)
        stats = service.get_stats(team_id=test_team.id)

        # Empty database should return zeros
        assert stats.total_results == 0
        assert stats.completed_count == 0
        assert stats.failed_count == 0
        assert stats.last_run is None
