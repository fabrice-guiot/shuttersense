"""
Build PipelineConfig from JSON node/edge definitions.

Shared by job_executor and CLI commands to convert server-format
pipeline JSON into the PipelineConfig dataclass used by the validator.

Issue #108 - Remove CLI Direct Usage (Config Caching)
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("shuttersense.agent.pipeline_config_builder")

# Import from repository root
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from utils.pipeline_processor import (
    PipelineConfig,
    CaptureNode,
    FileNode,
    ProcessNode,
    PairingNode,
    BranchingNode,
    TerminationNode,
)


def build_pipeline_config(
    nodes_json: List[Dict[str, Any]],
    edges_json: List[Dict[str, Any]],
) -> PipelineConfig:
    """
    Build a PipelineConfig from JSON node and edge definitions.

    Converts the database/API format (nodes_json, edges_json) into the
    PipelineConfig dataclass expected by pipeline_processor validation.

    Args:
        nodes_json: List of node definitions from server
        edges_json: List of edge definitions from server

    Returns:
        Fully populated PipelineConfig with categorized node lists
    """
    # Build output map from edges
    output_map: Dict[str, list] = {}
    for edge in edges_json:
        from_id = edge.get("from") or edge.get("source")
        to_id = edge.get("to") or edge.get("target")
        if from_id and to_id:
            if from_id not in output_map:
                output_map[from_id] = []
            output_map[from_id].append(to_id)

    # Parse nodes
    nodes = []
    for node_dict in nodes_json:
        node_id = node_dict.get("id")
        node_type = node_dict.get("type", "").lower()
        if not node_id or not node_type:
            logger.warning("Skipping node with missing id or type: %s", node_dict)
            continue
        properties = node_dict.get("properties", {})
        name = properties.get("name", node_dict.get("name", ""))
        output = output_map.get(node_id, [])

        match node_type:
            case "capture":
                nodes.append(CaptureNode(id=node_id, name=name, output=output))
            case "file":
                extension = properties.get("extension", "")
                nodes.append(FileNode(id=node_id, name=name, output=output, extension=extension))
            case "process":
                method_ids = properties.get("method_ids", properties.get("methodIds", []))
                if not isinstance(method_ids, list):
                    method_ids = [method_ids] if method_ids else []
                nodes.append(ProcessNode(id=node_id, name=name, output=output, method_ids=method_ids))
            case "pairing":
                pairing_type = properties.get("pairing_type", properties.get("pairingType", ""))
                input_count = properties.get("input_count", properties.get("inputCount", 2))
                nodes.append(PairingNode(
                    id=node_id, name=name, output=output,
                    pairing_type=pairing_type, input_count=input_count
                ))
            case "branching":
                condition = properties.get("condition_description", properties.get("conditionDescription", ""))
                nodes.append(BranchingNode(
                    id=node_id, name=name, output=output,
                    condition_description=condition
                ))
            case "termination":
                term_type = properties.get("termination_type", properties.get("terminationType", ""))
                nodes.append(TerminationNode(
                    id=node_id, name=name, output=output,
                    termination_type=term_type
                ))
            case _:
                logger.warning("Unsupported node type '%s' for node '%s', skipping", node_type, node_id)

    # Create PipelineConfig and categorize nodes
    pipeline_config = PipelineConfig(nodes=nodes)
    for node in nodes:
        if isinstance(node, CaptureNode):
            pipeline_config.capture_nodes.append(node)
        elif isinstance(node, FileNode):
            pipeline_config.file_nodes.append(node)
        elif isinstance(node, ProcessNode):
            pipeline_config.process_nodes.append(node)
        elif isinstance(node, PairingNode):
            pipeline_config.pairing_nodes.append(node)
        elif isinstance(node, BranchingNode):
            pipeline_config.branching_nodes.append(node)
        elif isinstance(node, TerminationNode):
            pipeline_config.termination_nodes.append(node)

    return pipeline_config
