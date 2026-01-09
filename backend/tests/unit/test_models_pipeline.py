"""
Unit tests for Pipeline and PipelineHistory models.

Tests the Pipeline model for:
- Model creation and field validation
- JSONB node and edge storage
- Version tracking
- Active/valid status management
- Helper methods and properties
- Relationships to PipelineHistory and AnalysisResult
"""

import pytest
from datetime import datetime

from backend.src.models import (
    Base,
    Pipeline,
    PipelineHistory,
)


class TestPipelineModel:
    """Tests for Pipeline model."""

    def test_create_basic_pipeline(self, test_db_session):
        """Test creating a basic pipeline with minimal fields."""
        pipeline = Pipeline(
            name="Basic Pipeline",
            nodes_json=[{"id": "node1", "type": "capture", "properties": {"sample_filename": "AB3D0001", "filename_regex": "([A-Z0-9]{4})([0-9]{4})", "camera_id_group": "1"}}],
            edges_json=[]
        )
        test_db_session.add(pipeline)
        test_db_session.commit()

        assert pipeline.id is not None
        assert pipeline.name == "Basic Pipeline"
        assert pipeline.version == 1
        assert pipeline.is_active is False
        assert pipeline.is_valid is False
        assert pipeline.created_at is not None
        assert pipeline.updated_at is not None

    def test_create_full_pipeline(self, test_db_session):
        """Test creating a pipeline with all fields."""
        nodes = [
            {"id": "capture", "type": "capture", "properties": {"sample_filename": "AB3D0001", "filename_regex": "([A-Z0-9]{4})([0-9]{4})", "camera_id_group": "1"}},
            {"id": "raw", "type": "file", "properties": {"extension": ".dng"}},
            {"id": "xmp", "type": "file", "properties": {"extension": ".xmp"}},
            {"id": "pair", "type": "pairing", "properties": {"inputs": ["raw", "xmp"]}},
            {"id": "end", "type": "termination", "properties": {"termination_type": "Black Box Archive"}}
        ]
        edges = [
            {"from": "capture", "to": "raw"},
            {"from": "capture", "to": "xmp"},
            {"from": "raw", "to": "pair"},
            {"from": "xmp", "to": "pair"},
            {"from": "pair", "to": "end"}
        ]

        pipeline = Pipeline(
            name="Full Workflow Pipeline",
            description="Complete photo processing workflow",
            nodes_json=nodes,
            edges_json=edges,
            is_active=True,
            is_valid=True
        )
        test_db_session.add(pipeline)
        test_db_session.commit()

        assert pipeline.id is not None
        assert pipeline.description == "Complete photo processing workflow"
        assert len(pipeline.nodes_json) == 5
        assert len(pipeline.edges_json) == 5
        assert pipeline.is_active is True
        assert pipeline.is_valid is True

    def test_unique_name_constraint(self, test_db_session):
        """Test that pipeline names must be unique."""
        from sqlalchemy.exc import IntegrityError

        pipeline1 = Pipeline(
            name="Unique Name",
            nodes_json=[],
            edges_json=[]
        )
        test_db_session.add(pipeline1)
        test_db_session.commit()

        pipeline2 = Pipeline(
            name="Unique Name",  # Same name
            nodes_json=[],
            edges_json=[]
        )
        test_db_session.add(pipeline2)

        with pytest.raises(IntegrityError):
            test_db_session.commit()

        test_db_session.rollback()

    def test_node_count_property(self, test_db_session):
        """Test node_count property."""
        pipeline = Pipeline(
            name="Node Count Test",
            nodes_json=[
                {"id": "n1", "type": "capture", "properties": {"sample_filename": "AB3D0001", "filename_regex": "([A-Z0-9]{4})([0-9]{4})", "camera_id_group": "1"}},
                {"id": "n2", "type": "file", "properties": {"extension": ".dng"}},
                {"id": "n3", "type": "termination", "properties": {"termination_type": "Archive"}}
            ],
            edges_json=[]
        )
        test_db_session.add(pipeline)
        test_db_session.commit()

        assert pipeline.node_count == 3

    def test_edge_count_property(self, test_db_session):
        """Test edge_count property."""
        pipeline = Pipeline(
            name="Edge Count Test",
            nodes_json=[{"id": "n1"}, {"id": "n2"}],
            edges_json=[
                {"from": "n1", "to": "n2"},
                {"from": "n2", "to": "n1"}
            ]
        )
        test_db_session.add(pipeline)
        test_db_session.commit()

        assert pipeline.edge_count == 2

    def test_get_node_by_id(self, test_db_session):
        """Test get_node_by_id method."""
        pipeline = Pipeline(
            name="Get Node Test",
            nodes_json=[
                {"id": "capture", "type": "capture", "properties": {"sample_filename": "AB3D0001", "filename_regex": "([A-Z0-9]{4})([0-9]{4})", "camera_id_group": "1"}},
                {"id": "file", "type": "file", "properties": {"extension": ".dng"}}
            ],
            edges_json=[]
        )
        test_db_session.add(pipeline)
        test_db_session.commit()

        # Find existing node
        node = pipeline.get_node_by_id("file")
        assert node is not None
        assert node["type"] == "file"
        assert node["properties"]["extension"] == ".dng"

        # Non-existent node
        missing = pipeline.get_node_by_id("nonexistent")
        assert missing is None

    def test_get_nodes_by_type(self, test_db_session):
        """Test get_nodes_by_type method."""
        pipeline = Pipeline(
            name="Get Nodes By Type Test",
            nodes_json=[
                {"id": "c1", "type": "capture", "properties": {"sample_filename": "AB3D0001", "filename_regex": "([A-Z0-9]{4})([0-9]{4})", "camera_id_group": "1"}},
                {"id": "f1", "type": "file", "properties": {"extension": ".dng"}},
                {"id": "f2", "type": "file", "properties": {"extension": ".xmp"}},
                {"id": "t1", "type": "termination", "properties": {"termination_type": "Archive"}}
            ],
            edges_json=[]
        )
        test_db_session.add(pipeline)
        test_db_session.commit()

        file_nodes = pipeline.get_nodes_by_type("file")
        assert len(file_nodes) == 2
        assert all(n["type"] == "file" for n in file_nodes)

        capture_nodes = pipeline.get_nodes_by_type("capture")
        assert len(capture_nodes) == 1

        # No nodes of this type
        process_nodes = pipeline.get_nodes_by_type("process")
        assert len(process_nodes) == 0

    def test_get_summary(self, test_db_session):
        """Test get_summary method."""
        pipeline = Pipeline(
            name="Summary Test",
            description="Test description",
            nodes_json=[{"id": "n1"}, {"id": "n2"}],
            edges_json=[{"from": "n1", "to": "n2"}],
            is_active=True,
            is_valid=True
        )
        test_db_session.add(pipeline)
        test_db_session.commit()

        summary = pipeline.get_summary()

        assert summary["id"] == pipeline.id
        assert summary["name"] == "Summary Test"
        assert summary["description"] == "Test description"
        assert summary["version"] == 1
        assert summary["is_active"] is True
        assert summary["is_valid"] is True
        assert summary["node_count"] == 2
        assert summary["created_at"] is not None

    def test_validation_errors_storage(self, test_db_session):
        """Test storing validation errors in JSONB."""
        pipeline = Pipeline(
            name="Validation Errors Test",
            nodes_json=[],
            edges_json=[],
            is_valid=False,
            validation_errors=[
                "Missing capture node",
                "No termination nodes found",
                "Cycle detected between nodes"
            ]
        )
        test_db_session.add(pipeline)
        test_db_session.commit()

        # Refresh from DB
        test_db_session.refresh(pipeline)

        assert pipeline.is_valid is False
        assert len(pipeline.validation_errors) == 3
        assert "Missing capture node" in pipeline.validation_errors

    def test_repr_and_str(self, test_db_session):
        """Test string representations."""
        pipeline = Pipeline(
            name="Repr Test Pipeline",
            nodes_json=[],
            edges_json=[],
            is_active=True,
            is_valid=True
        )
        test_db_session.add(pipeline)
        test_db_session.commit()

        # Test __repr__
        repr_str = repr(pipeline)
        assert "Pipeline" in repr_str
        assert "Repr Test Pipeline" in repr_str
        assert "active=True" in repr_str

        # Test __str__
        str_str = str(pipeline)
        assert "Repr Test Pipeline" in str_str
        assert "active" in str_str
        assert "valid" in str_str


class TestPipelineHistoryModel:
    """Tests for PipelineHistory model."""

    @pytest.fixture
    def sample_pipeline(self, test_db_session):
        """Create a sample pipeline for testing."""
        pipeline = Pipeline(
            name="History Test Pipeline",
            nodes_json=[{"id": "n1", "type": "capture", "properties": {"sample_filename": "AB3D0001", "filename_regex": "([A-Z0-9]{4})([0-9]{4})", "camera_id_group": "1"}}],
            edges_json=[]
        )
        test_db_session.add(pipeline)
        test_db_session.commit()
        return pipeline

    def test_create_history_entry(self, test_db_session, sample_pipeline):
        """Test creating a pipeline history entry."""
        history = PipelineHistory(
            pipeline_id=sample_pipeline.id,
            version=1,
            nodes_json=[{"id": "n1", "type": "capture", "properties": {"sample_filename": "AB3D0001", "filename_regex": "([A-Z0-9]{4})([0-9]{4})", "camera_id_group": "1"}}],
            edges_json=[],
            change_summary="Initial version",
            changed_by="test_user"
        )
        test_db_session.add(history)
        test_db_session.commit()

        assert history.id is not None
        assert history.pipeline_id == sample_pipeline.id
        assert history.version == 1
        assert history.change_summary == "Initial version"
        assert history.changed_by == "test_user"
        assert history.created_at is not None

    def test_history_relationship(self, test_db_session, sample_pipeline):
        """Test relationship between Pipeline and PipelineHistory."""
        # Create multiple history entries
        history1 = PipelineHistory(
            pipeline_id=sample_pipeline.id,
            version=1,
            nodes_json=[{"id": "n1"}],
            edges_json=[],
            change_summary="Version 1"
        )
        history2 = PipelineHistory(
            pipeline_id=sample_pipeline.id,
            version=2,
            nodes_json=[{"id": "n1"}, {"id": "n2"}],
            edges_json=[{"from": "n1", "to": "n2"}],
            change_summary="Added node n2"
        )
        test_db_session.add_all([history1, history2])
        test_db_session.commit()

        # Access history through pipeline relationship
        test_db_session.refresh(sample_pipeline)
        assert len(list(sample_pipeline.history)) == 2

    def test_unique_version_per_pipeline(self, test_db_session, sample_pipeline):
        """Test that (pipeline_id, version) must be unique."""
        from sqlalchemy.exc import IntegrityError

        history1 = PipelineHistory(
            pipeline_id=sample_pipeline.id,
            version=1,
            nodes_json=[],
            edges_json=[]
        )
        test_db_session.add(history1)
        test_db_session.commit()

        history2 = PipelineHistory(
            pipeline_id=sample_pipeline.id,
            version=1,  # Same version
            nodes_json=[],
            edges_json=[]
        )
        test_db_session.add(history2)

        with pytest.raises(IntegrityError):
            test_db_session.commit()

        test_db_session.rollback()

    def test_cascade_delete_with_pipeline(self, test_db_session, sample_pipeline):
        """Test that history is deleted when pipeline is deleted."""
        history = PipelineHistory(
            pipeline_id=sample_pipeline.id,
            version=1,
            nodes_json=[],
            edges_json=[]
        )
        test_db_session.add(history)
        test_db_session.commit()

        history_id = history.id

        # Delete pipeline
        test_db_session.delete(sample_pipeline)
        test_db_session.commit()

        # Verify history was deleted
        deleted_history = test_db_session.query(PipelineHistory).filter_by(
            id=history_id
        ).first()
        assert deleted_history is None

    def test_get_summary(self, test_db_session, sample_pipeline):
        """Test get_summary method."""
        history = PipelineHistory(
            pipeline_id=sample_pipeline.id,
            version=3,
            nodes_json=[{"id": "n1"}],
            edges_json=[],
            change_summary="Major refactoring",
            changed_by="admin"
        )
        test_db_session.add(history)
        test_db_session.commit()

        summary = history.get_summary()

        assert summary["id"] == history.id
        assert summary["version"] == 3
        assert summary["change_summary"] == "Major refactoring"
        assert summary["changed_by"] == "admin"
        assert summary["created_at"] is not None

    def test_repr_and_str(self, test_db_session, sample_pipeline):
        """Test string representations."""
        history = PipelineHistory(
            pipeline_id=sample_pipeline.id,
            version=2,
            nodes_json=[],
            edges_json=[],
            change_summary="Test change"
        )
        test_db_session.add(history)
        test_db_session.commit()

        # Test __repr__
        repr_str = repr(history)
        assert "PipelineHistory" in repr_str
        assert str(sample_pipeline.id) in repr_str
        assert "version=2" in repr_str

        # Test __str__
        str_str = str(history)
        assert "v2" in str_str
        assert "Test change" in str_str
