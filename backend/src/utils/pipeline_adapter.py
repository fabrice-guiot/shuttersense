"""
Pipeline Adapter for Backend to CLI Tool Integration

Converts pipeline data stored in the database (JSON format) to the format
expected by the pipeline_validation CLI tool (PipelineConfig).

This adapter bridges the gap between:
- Backend storage: Pipeline model with nodes_json (list of dicts) and edges_json (list of dicts)
- CLI tool: PipelineConfig with typed node objects and edges derived from node.output lists

Node Type Mapping:
- "capture" -> CaptureNode
- "file" -> FileNode
- "process" -> ProcessNode
- "pairing" -> PairingNode
- "branching" -> BranchingNode
- "termination" -> TerminationNode

Edge Handling:
- Backend: edges_json = [{"from": "node1", "to": "node2"}, ...]
- CLI: Each node has an "output" list of node IDs it connects to

Author: photo-admin project
License: AGPL-3.0
"""

from typing import List, Dict, Any

from utils.pipeline_processor import (
    PipelineConfig,
    CaptureNode,
    FileNode,
    ProcessNode,
    PairingNode,
    BranchingNode,
    TerminationNode,
    PipelineNode,
)


def convert_db_pipeline_to_config(
    nodes_json: List[Dict[str, Any]],
    edges_json: List[Dict[str, Any]]
) -> PipelineConfig:
    """
    Convert database pipeline format to PipelineConfig.

    Args:
        nodes_json: List of node dictionaries from database
            Each dict has: id, type, properties
        edges_json: List of edge dictionaries from database
            Each dict has: from, to

    Returns:
        PipelineConfig with typed node objects

    Example:
        nodes_json = [
            {"id": "capture", "type": "capture", "properties": {"camera_id_pattern": "[A-Z0-9]{4}"}},
            {"id": "raw", "type": "file", "properties": {"extension": ".dng"}},
            {"id": "done", "type": "termination", "properties": {"termination_type": "Black Box Archive"}}
        ]
        edges_json = [
            {"from": "capture", "to": "raw"},
            {"from": "raw", "to": "done"}
        ]
    """
    # Build output map from edges
    outputs_by_node: Dict[str, List[str]] = {}
    for edge in edges_json:
        from_node = edge.get("from", "")
        to_node = edge.get("to", "")
        if from_node not in outputs_by_node:
            outputs_by_node[from_node] = []
        outputs_by_node[from_node].append(to_node)

    # Convert nodes
    all_nodes: List[PipelineNode] = []
    capture_nodes: List[CaptureNode] = []
    file_nodes: List[FileNode] = []
    process_nodes: List[ProcessNode] = []
    pairing_nodes: List[PairingNode] = []
    branching_nodes: List[BranchingNode] = []
    termination_nodes: List[TerminationNode] = []

    for node_data in nodes_json:
        node_id = node_data.get("id", "")
        node_type = node_data.get("type", "").lower()
        properties = node_data.get("properties", {})
        output = outputs_by_node.get(node_id, [])

        # Get name from properties or use id
        name = properties.get("name", node_id)

        if node_type == "capture":
            node = CaptureNode(
                id=node_id,
                name=name,
                output=output
            )
            capture_nodes.append(node)
            all_nodes.append(node)

        elif node_type == "file":
            extension = properties.get("extension", ".unknown")
            node = FileNode(
                id=node_id,
                name=name,
                output=output,
                extension=extension
            )
            file_nodes.append(node)
            all_nodes.append(node)

        elif node_type == "process":
            # Get method_ids from properties (array of processing method identifiers)
            method_ids = properties.get("method_ids", [])
            # Ensure it's a list (handle legacy single string format)
            if isinstance(method_ids, str):
                method_ids = [method_ids] if method_ids else []
            elif not isinstance(method_ids, list):
                method_ids = []
            node = ProcessNode(
                id=node_id,
                name=name,
                output=output,
                method_ids=method_ids
            )
            process_nodes.append(node)
            all_nodes.append(node)

        elif node_type == "pairing":
            pairing_type = properties.get("pairing_type", "HDR")
            inputs = properties.get("inputs", [])
            node = PairingNode(
                id=node_id,
                name=name,
                output=output,
                pairing_type=pairing_type,
                input_count=len(inputs) if inputs else 2
            )
            pairing_nodes.append(node)
            all_nodes.append(node)

        elif node_type == "branching":
            condition = properties.get("condition", "")
            value = properties.get("value", "")
            condition_description = f"{condition}: {value}" if condition else "User choice"
            node = BranchingNode(
                id=node_id,
                name=name,
                output=output,
                condition_description=condition_description
            )
            branching_nodes.append(node)
            all_nodes.append(node)

        elif node_type == "termination":
            # Support both termination_type (new) and classification (deprecated)
            termination_type = properties.get("termination_type") or properties.get("classification", "Black Box Archive")
            node = TerminationNode(
                id=node_id,
                name=name,
                output=[],  # Termination nodes have no outputs
                termination_type=termination_type
            )
            termination_nodes.append(node)
            all_nodes.append(node)

    return PipelineConfig(
        nodes=all_nodes,
        capture_nodes=capture_nodes,
        file_nodes=file_nodes,
        process_nodes=process_nodes,
        pairing_nodes=pairing_nodes,
        branching_nodes=branching_nodes,
        termination_nodes=termination_nodes
    )
