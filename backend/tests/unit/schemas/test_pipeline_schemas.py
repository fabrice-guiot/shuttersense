"""Tests for the NodePosition schema extension in pipeline schemas."""

import pytest
from backend.src.schemas.pipelines import (
    NodePosition,
    PipelineNode,
    PipelineCreateRequest,
)


class TestNodePosition:
    """Tests for the NodePosition schema."""

    def test_valid_position(self):
        pos = NodePosition(x=100.0, y=200.0)
        assert pos.x == 100.0
        assert pos.y == 200.0

    def test_integer_values_accepted(self):
        pos = NodePosition(x=0, y=0)
        assert pos.x == 0.0
        assert pos.y == 0.0

    def test_negative_values_accepted(self):
        pos = NodePosition(x=-50.5, y=-100.3)
        assert pos.x == -50.5
        assert pos.y == -100.3

    def test_model_dump(self):
        pos = NodePosition(x=150.0, y=250.0)
        data = pos.model_dump()
        assert data == {"x": 150.0, "y": 250.0}

    def test_model_validate(self):
        pos = NodePosition.model_validate({"x": 42.0, "y": 84.0})
        assert pos.x == 42.0
        assert pos.y == 84.0


class TestPipelineNodeWithPosition:
    """Tests for PipelineNode with the optional position field."""

    def test_node_without_position_validates(self):
        """Backward compatibility: nodes without position should still validate."""
        node = PipelineNode(id="file_raw", type="file", properties={"extension": ".dng"})
        assert node.position is None

    def test_node_with_position_validates(self):
        node = PipelineNode(
            id="file_raw",
            type="file",
            properties={"extension": ".dng"},
            position={"x": 100.0, "y": 200.0},
        )
        assert node.position is not None
        assert node.position.x == 100.0
        assert node.position.y == 200.0

    def test_position_roundtrip_via_model_dump(self):
        node = PipelineNode(
            id="capture_1",
            type="capture",
            properties={"sample_filename": "AB3D0001"},
            position={"x": 250.0, "y": 50.0},
        )
        data = node.model_dump()
        assert data["position"] == {"x": 250.0, "y": 50.0}

        restored = PipelineNode.model_validate(data)
        assert restored.position.x == 250.0
        assert restored.position.y == 50.0

    def test_position_none_in_model_dump(self):
        node = PipelineNode(id="file_1", type="file", properties={})
        data = node.model_dump()
        assert data["position"] is None

    def test_node_from_json_without_position(self):
        """Simulates loading pre-existing pipeline data from JSONB."""
        raw = {"id": "file_raw", "type": "file", "properties": {"extension": ".dng"}}
        node = PipelineNode.model_validate(raw)
        assert node.position is None
        assert node.id == "file_raw"

    def test_node_from_json_with_position(self):
        raw = {
            "id": "capture_1",
            "type": "capture",
            "properties": {},
            "position": {"x": 100, "y": 200},
        }
        node = PipelineNode.model_validate(raw)
        assert node.position.x == 100.0
        assert node.position.y == 200.0


class TestPipelineCreateRequestWithPositions:
    """Tests for PipelineCreateRequest with nodes containing positions."""

    def test_create_request_with_positioned_nodes(self):
        request = PipelineCreateRequest(
            name="Test Pipeline",
            nodes=[
                PipelineNode(
                    id="capture_1",
                    type="capture",
                    properties={"sample_filename": "AB3D0001", "filename_regex": "([A-Z0-9]{4})([0-9]{4})", "camera_id_group": "1"},
                    position={"x": 250, "y": 50},
                ),
                PipelineNode(
                    id="file_raw",
                    type="file",
                    properties={"extension": ".dng"},
                    position={"x": 150, "y": 200},
                ),
            ],
            edges=[{"from": "capture_1", "to": "file_raw"}],
        )
        assert len(request.nodes) == 2
        assert request.nodes[0].position.x == 250.0
        assert request.nodes[1].position.y == 200.0

    def test_create_request_mixed_positions(self):
        """Some nodes with positions, some without."""
        request = PipelineCreateRequest(
            name="Mixed Pipeline",
            nodes=[
                PipelineNode(id="capture_1", type="capture", properties={}, position={"x": 0, "y": 0}),
                PipelineNode(id="file_1", type="file", properties={"extension": ".dng"}),
            ],
            edges=[{"from": "capture_1", "to": "file_1"}],
        )
        assert request.nodes[0].position is not None
        assert request.nodes[1].position is None
