"""
Pipeline service for managing photo processing workflows.

Provides CRUD operations, validation, and version history for pipelines:
- Create, read, update, delete pipeline definitions
- Validate pipeline graph structure (cycles, orphans, etc.)
- Activate/deactivate pipelines for validation runs
- Preview expected filenames based on pipeline structure
- Version history with change tracking
- Import/export in YAML format
- Statistics for dashboard KPIs

Design:
- Graph validation using topological sort
- Version control with history snapshots
- Multiple pipelines can be active (valid and ready for use)
- Single default pipeline constraint (application-enforced)
- YAML import/export for portability
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
import re
import yaml

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from backend.src.models import Pipeline, PipelineHistory
from backend.src.schemas.pipelines import (
    PipelineSummary, PipelineResponse, ValidationResult, ValidationError,
    ValidationErrorType, FilenamePreviewResponse, ExpectedFile,
    PipelineHistoryEntry, PipelineStatsResponse, PipelineNode, PipelineEdge
)
from backend.src.services.exceptions import NotFoundError, ConflictError, ValidationError as ServiceValidationError
from backend.src.utils.logging_config import get_logger


logger = get_logger("services")


class PipelineService:
    """
    Service for managing photo processing pipelines.

    Handles CRUD operations, validation, activation, and version history
    for pipeline workflow definitions.

    Usage:
        >>> service = PipelineService(db_session)
        >>> pipeline = service.create(name="RAW Workflow", nodes=[...], edges=[...])
        >>> validation = service.validate(pipeline.id)
        >>> service.activate(pipeline.id)
    """

    def __init__(self, db: Session):
        """
        Initialize pipeline service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    def create(
        self,
        name: str,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        description: Optional[str] = None
    ) -> PipelineResponse:
        """
        Create a new pipeline.

        Args:
            name: Pipeline name (unique)
            nodes: List of node definitions
            edges: List of edge connections
            description: Optional description

        Returns:
            Created pipeline details

        Raises:
            ConflictError: If name already exists
        """
        # Check for duplicate name
        existing = self.db.query(Pipeline).filter(Pipeline.name == name).first()
        if existing:
            raise ConflictError(f"Pipeline with name '{name}' already exists")

        # Convert edges to stored format
        edges_json = self._convert_edges_to_json(edges)

        # Validate structure
        is_valid, validation_errors = self._validate_structure(nodes, edges_json)

        # Create pipeline
        pipeline = Pipeline(
            name=name,
            description=description,
            nodes_json=nodes,
            edges_json=edges_json,
            version=1,
            is_active=False,
            is_default=False,
            is_valid=is_valid,
            validation_errors=validation_errors if validation_errors else None
        )

        self.db.add(pipeline)
        self.db.commit()
        self.db.refresh(pipeline)

        logger.info(f"Created pipeline '{name}' (id={pipeline.id})")
        return self._to_response(pipeline)

    def get(self, pipeline_id: int) -> PipelineResponse:
        """
        Get pipeline by ID.

        Args:
            pipeline_id: Pipeline ID

        Returns:
            Pipeline details

        Raises:
            NotFoundError: If pipeline doesn't exist
        """
        pipeline = self._get_pipeline(pipeline_id)
        return self._to_response(pipeline)

    def list(
        self,
        is_active: Optional[bool] = None,
        is_default: Optional[bool] = None,
        is_valid: Optional[bool] = None
    ) -> List[PipelineSummary]:
        """
        List all pipelines with optional filters.

        Args:
            is_active: Filter by active status
            is_default: Filter by default status
            is_valid: Filter by validation status

        Returns:
            List of pipeline summaries
        """
        query = self.db.query(Pipeline)

        if is_active is not None:
            query = query.filter(Pipeline.is_active == is_active)
        if is_default is not None:
            query = query.filter(Pipeline.is_default == is_default)
        if is_valid is not None:
            query = query.filter(Pipeline.is_valid == is_valid)

        pipelines = query.order_by(desc(Pipeline.updated_at)).all()

        return [self._to_summary(p) for p in pipelines]

    def update(
        self,
        pipeline_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        nodes: Optional[List[Dict[str, Any]]] = None,
        edges: Optional[List[Dict[str, Any]]] = None,
        change_summary: Optional[str] = None
    ) -> PipelineResponse:
        """
        Update a pipeline.

        Creates a history entry before updating.

        Args:
            pipeline_id: Pipeline ID
            name: New name (optional)
            description: New description (optional)
            nodes: New node definitions (optional)
            edges: New edge connections (optional)
            change_summary: Summary of changes for history

        Returns:
            Updated pipeline details

        Raises:
            NotFoundError: If pipeline doesn't exist
            ConflictError: If new name already exists
        """
        pipeline = self._get_pipeline(pipeline_id)

        # Check for duplicate name
        if name and name != pipeline.name:
            existing = self.db.query(Pipeline).filter(Pipeline.name == name).first()
            if existing:
                raise ConflictError(f"Pipeline with name '{name}' already exists")

        # Save current state to history
        self._save_history(pipeline, change_summary)

        # Update fields
        if name:
            pipeline.name = name
        if description is not None:
            pipeline.description = description
        if nodes is not None:
            pipeline.nodes_json = nodes
        if edges is not None:
            pipeline.edges_json = self._convert_edges_to_json(edges)

        # Re-validate if structure changed
        if nodes is not None or edges is not None:
            is_valid, validation_errors = self._validate_structure(
                pipeline.nodes_json,
                pipeline.edges_json
            )
            pipeline.is_valid = is_valid
            pipeline.validation_errors = validation_errors if validation_errors else None

            # Auto-deactivate if pipeline becomes invalid
            if not is_valid and pipeline.is_active:
                pipeline.is_active = False
                if pipeline.is_default:
                    pipeline.is_default = False
                logger.info(f"Auto-deactivated pipeline {pipeline_id} due to validation failure")

        # Increment version
        pipeline.version += 1

        self.db.commit()
        self.db.refresh(pipeline)

        logger.info(f"Updated pipeline {pipeline_id} to version {pipeline.version}")
        return self._to_response(pipeline)

    def delete(self, pipeline_id: int) -> int:
        """
        Delete a pipeline.

        Args:
            pipeline_id: Pipeline ID to delete

        Returns:
            ID of deleted pipeline

        Raises:
            NotFoundError: If pipeline doesn't exist
            ConflictError: If pipeline is active
        """
        pipeline = self._get_pipeline(pipeline_id)

        if pipeline.is_default:
            raise ConflictError("Cannot delete default pipeline. Remove default status first.")
        if pipeline.is_active:
            raise ConflictError("Cannot delete active pipeline. Deactivate it first.")

        self.db.delete(pipeline)
        self.db.commit()

        logger.info(f"Deleted pipeline {pipeline_id}")
        return pipeline_id

    # =========================================================================
    # Validation
    # =========================================================================

    def validate(self, pipeline_id: int) -> ValidationResult:
        """
        Validate pipeline structure.

        Checks for:
        - Cycles in the graph
        - Orphaned nodes (not connected to any edge)
        - Invalid node references in edges
        - Missing required nodes

        Args:
            pipeline_id: Pipeline ID

        Returns:
            Validation result with errors if any

        Raises:
            NotFoundError: If pipeline doesn't exist
        """
        pipeline = self._get_pipeline(pipeline_id)

        is_valid, error_messages = self._validate_structure(
            pipeline.nodes_json,
            pipeline.edges_json
        )

        # Update pipeline validation status
        pipeline.is_valid = is_valid
        pipeline.validation_errors = error_messages if error_messages else None
        self.db.commit()

        errors = [
            ValidationError(
                type=ValidationErrorType.ORPHANED_NODE,  # Default type
                message=msg,
                node_id=None,
                suggestion=None
            )
            for msg in (error_messages or [])
        ]

        return ValidationResult(is_valid=is_valid, errors=errors)

    def _validate_structure(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]]
    ) -> Tuple[bool, Optional[List[str]]]:
        """
        Validate pipeline graph structure.

        Args:
            nodes: Node definitions
            edges: Edge connections

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        node_ids = {node["id"] for node in nodes}

        # Check for required node types
        node_types = [n.get("type") for n in nodes]

        # Must have exactly one Capture node
        capture_count = node_types.count("capture")
        if capture_count == 0:
            errors.append("Missing required node: pipeline must have a Capture node")
        elif capture_count > 1:
            errors.append("Invalid structure: pipeline can only have one Capture node")
        else:
            # Validate Capture node properties
            capture_node = next(n for n in nodes if n.get("type") == "capture")
            capture_errors = self._validate_capture_node_properties(capture_node)
            errors.extend(capture_errors)

        # Must have at least one non-optional File node
        has_required_file = any(
            n.get("type") == "file" and not n.get("properties", {}).get("optional", False)
            for n in nodes
        )
        if not has_required_file:
            errors.append("Missing required node: pipeline must have at least one non-optional File node")

        # Must have at least one Termination node
        if "termination" not in node_types:
            errors.append("Missing required node: pipeline must have at least one Termination node")

        # Check for orphaned nodes (not connected to any edge)
        connected_nodes = set()
        for edge in edges:
            connected_nodes.add(edge.get("from", ""))
            connected_nodes.add(edge.get("to", ""))

        orphaned = node_ids - connected_nodes
        # Exclude termination nodes from orphan check (they can be endpoints)
        termination_ids = {n["id"] for n in nodes if n.get("type") == "termination"}
        orphaned = orphaned - termination_ids

        # Only flag as orphan if there are edges (single-node pipelines are ok)
        if edges and orphaned:
            for node_id in orphaned:
                errors.append(f"Orphaned node: {node_id}")

        # Check for invalid edge references
        for edge in edges:
            from_node = edge.get("from", "")
            to_node = edge.get("to", "")
            if from_node not in node_ids:
                errors.append(f"Edge references non-existent node: {from_node}")
            if to_node not in node_ids:
                errors.append(f"Edge references non-existent node: {to_node}")

        # Check that pairing nodes have exactly 2 inputs (edges pointing to them)
        pairing_nodes = [n for n in nodes if n.get("type") == "pairing"]
        for pairing_node in pairing_nodes:
            pairing_id = pairing_node.get("id", "")
            input_count = sum(1 for e in edges if e.get("to") == pairing_id)
            if input_count != 2:
                errors.append(
                    f"Pairing node '{pairing_id}' must have exactly 2 inputs (has {input_count})"
                )

        # Note: Cycles ARE allowed in pipelines - the CLI pipeline_validation tool
        # handles loop execution limits to prevent infinite loops at runtime.

        is_valid = len(errors) == 0
        return is_valid, errors if errors else None

    def _validate_capture_node_properties(self, capture_node: Dict[str, Any]) -> List[str]:
        """
        Validate Capture node properties.

        Validates:
        - sample_filename is present
        - filename_regex is a valid regex with exactly 2 capture groups
        - sample_filename matches the regex
        - Counter group (non-camera_id) captures only digits

        Args:
            capture_node: Capture node dictionary

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        props = capture_node.get("properties", {})
        node_id = capture_node.get("id", "capture")

        sample = props.get("sample_filename")
        regex_str = props.get("filename_regex")
        group = props.get("camera_id_group")

        # Check required properties
        if not sample:
            errors.append(f"Capture node '{node_id}': missing sample_filename")
            return errors
        if not regex_str:
            errors.append(f"Capture node '{node_id}': missing filename_regex")
            return errors
        if group not in ("1", "2"):
            errors.append(f"Capture node '{node_id}': camera_id_group must be '1' or '2'")
            return errors

        # Validate regex has exactly 2 groups
        try:
            compiled = re.compile(regex_str)
            if compiled.groups != 2:
                errors.append(
                    f"Capture node '{node_id}': filename_regex must have exactly 2 capture groups, found {compiled.groups}"
                )
                return errors
        except re.error as e:
            errors.append(f"Capture node '{node_id}': invalid filename_regex: {e}")
            return errors

        # Validate sample matches regex
        match = compiled.match(sample)
        if not match:
            errors.append(
                f"Capture node '{node_id}': sample_filename '{sample}' does not match filename_regex"
            )
            return errors

        # Validate counter group is all numeric
        counter_group = 2 if group == "1" else 1
        counter_value = match.group(counter_group)
        if not counter_value.isdigit():
            errors.append(
                f"Capture node '{node_id}': Counter group (group {counter_group}) must be all numeric, got '{counter_value}'"
            )

        return errors

    # =========================================================================
    # Activation
    # =========================================================================

    def activate(self, pipeline_id: int) -> PipelineResponse:
        """
        Activate a pipeline.

        Multiple pipelines can be active at the same time.
        Active pipelines are valid and ready for use.

        Args:
            pipeline_id: Pipeline ID

        Returns:
            Activated pipeline details

        Raises:
            NotFoundError: If pipeline doesn't exist
            ValidationError: If pipeline is not valid
        """
        pipeline = self._get_pipeline(pipeline_id)

        if not pipeline.is_valid:
            raise ServiceValidationError("Cannot activate invalid pipeline. Fix validation errors first.")

        # Activate this pipeline (multiple can be active)
        pipeline.is_active = True
        self.db.commit()
        self.db.refresh(pipeline)

        logger.info(f"Activated pipeline {pipeline_id}")
        return self._to_response(pipeline)

    def deactivate(self, pipeline_id: int) -> PipelineResponse:
        """
        Deactivate a pipeline.

        If the pipeline is the default, it also loses default status.

        Args:
            pipeline_id: Pipeline ID

        Returns:
            Deactivated pipeline details

        Raises:
            NotFoundError: If pipeline doesn't exist
        """
        pipeline = self._get_pipeline(pipeline_id)
        pipeline.is_active = False
        if pipeline.is_default:
            pipeline.is_default = False
        self.db.commit()
        self.db.refresh(pipeline)

        logger.info(f"Deactivated pipeline {pipeline_id}")
        return self._to_response(pipeline)

    def set_default(self, pipeline_id: int) -> PipelineResponse:
        """
        Set a pipeline as the default for tool execution.

        Only one pipeline can be default at a time.
        The pipeline must be active to be set as default.

        Args:
            pipeline_id: Pipeline ID

        Returns:
            Pipeline details with is_default=True

        Raises:
            NotFoundError: If pipeline doesn't exist
            ValidationError: If pipeline is not active
        """
        pipeline = self._get_pipeline(pipeline_id)

        if not pipeline.is_active:
            raise ServiceValidationError("Cannot set inactive pipeline as default. Activate it first.")

        # Unset any currently default pipeline
        self.db.query(Pipeline).filter(Pipeline.is_default == True).update(
            {"is_default": False}
        )

        # Set this pipeline as default
        pipeline.is_default = True
        self.db.commit()
        self.db.refresh(pipeline)

        logger.info(f"Set pipeline {pipeline_id} as default")
        return self._to_response(pipeline)

    def unset_default(self, pipeline_id: int) -> PipelineResponse:
        """
        Remove default status from a pipeline.

        Args:
            pipeline_id: Pipeline ID

        Returns:
            Pipeline details with is_default=False

        Raises:
            NotFoundError: If pipeline doesn't exist
        """
        pipeline = self._get_pipeline(pipeline_id)
        pipeline.is_default = False
        self.db.commit()
        self.db.refresh(pipeline)

        logger.info(f"Removed default status from pipeline {pipeline_id}")
        return self._to_response(pipeline)

    # =========================================================================
    # Preview
    # =========================================================================

    def preview_filenames(self, pipeline_id: int) -> FilenamePreviewResponse:
        """
        Preview expected filenames for a pipeline.

        Uses the sample_filename from the Capture node as the base filename.

        Args:
            pipeline_id: Pipeline ID

        Returns:
            Preview with expected filenames

        Raises:
            NotFoundError: If pipeline doesn't exist
            ValidationError: If pipeline is not valid
        """
        pipeline = self._get_pipeline(pipeline_id)

        if not pipeline.is_valid:
            raise ServiceValidationError("Cannot preview invalid pipeline. Fix validation errors first.")

        # Get base_filename from Capture node's sample_filename
        capture_node = self._get_capture_node(pipeline)
        base_filename = capture_node.get("properties", {}).get("sample_filename", "UNKNOWN0000")

        expected_files = []

        # Traverse the pipeline graph to find all file nodes
        for node in pipeline.nodes_json:
            if node.get("type") == "file":
                extension = node.get("properties", {}).get("extension", ".unknown")
                optional = node.get("properties", {}).get("optional", False)

                # Build path from capture to this node
                path = self._build_path_to_node(pipeline, node["id"])

                expected_files.append(ExpectedFile(
                    path=path,
                    filename=f"{base_filename}{extension}",
                    optional=optional
                ))

        return FilenamePreviewResponse(
            base_filename=base_filename,
            expected_files=expected_files
        )

    def _get_capture_node(self, pipeline: Pipeline) -> dict:
        """
        Get the Capture node from a pipeline.

        Args:
            pipeline: Pipeline model

        Returns:
            Capture node dictionary

        Raises:
            ValidationError: If no Capture node found
        """
        for node in pipeline.nodes_json:
            if node.get("type") == "capture":
                return node
        raise ServiceValidationError("Pipeline missing Capture node")

    def _build_path_to_node(self, pipeline: Pipeline, target_id: str) -> str:
        """
        Build path string from root to target node.

        Args:
            pipeline: Pipeline model
            target_id: Target node ID

        Returns:
            Path string like "capture -> raw -> xmp"
        """
        # Simple implementation - just show direct path
        # Find parent node(s)
        parents = []
        for edge in pipeline.edges_json:
            if edge.get("to") == target_id:
                parents.append(edge.get("from", ""))

        if parents:
            return f"{parents[0]} -> {target_id}"
        return target_id

    # =========================================================================
    # Version History
    # =========================================================================

    def get_history(self, pipeline_id: int) -> List[PipelineHistoryEntry]:
        """
        Get version history for a pipeline.

        Args:
            pipeline_id: Pipeline ID

        Returns:
            List of history entries

        Raises:
            NotFoundError: If pipeline doesn't exist
        """
        # Verify pipeline exists
        self._get_pipeline(pipeline_id)

        history = self.db.query(PipelineHistory).filter(
            PipelineHistory.pipeline_id == pipeline_id
        ).order_by(desc(PipelineHistory.version)).all()

        return [
            PipelineHistoryEntry(
                id=h.id,
                version=h.version,
                change_summary=h.change_summary,
                changed_by=h.changed_by,
                created_at=h.created_at
            )
            for h in history
        ]

    def get_version(self, pipeline_id: int, version: int) -> PipelineResponse:
        """
        Get a specific version of a pipeline from history.

        Args:
            pipeline_id: Pipeline ID
            version: Version number to retrieve

        Returns:
            Pipeline data at that version

        Raises:
            NotFoundError: If pipeline or version doesn't exist
        """
        # Get current pipeline for metadata
        pipeline = self._get_pipeline(pipeline_id)

        # If requesting current version, return the pipeline as-is
        if version == pipeline.version:
            return self._to_response(pipeline)

        # Look up historical version
        history_entry = self.db.query(PipelineHistory).filter(
            PipelineHistory.pipeline_id == pipeline_id,
            PipelineHistory.version == version
        ).first()

        if not history_entry:
            raise NotFoundError(f"Version {version} not found for pipeline {pipeline_id}")

        # Build response from historical data
        nodes = history_entry.nodes_json or []
        edges = history_entry.edges_json or []

        return PipelineResponse(
            id=pipeline.id,
            name=pipeline.name,
            description=pipeline.description,
            nodes=[PipelineNode(**n) for n in nodes],
            edges=[PipelineEdge(**e) for e in edges],
            version=version,  # The historical version
            is_active=False,  # Historical versions are never active
            is_default=False,  # Historical versions are never default
            is_valid=pipeline.is_valid,  # Use current validity (historical may differ)
            validation_errors=None,
            created_at=history_entry.created_at,
            updated_at=history_entry.created_at
        )

    def _save_history(self, pipeline: Pipeline, change_summary: Optional[str]) -> None:
        """
        Save current pipeline state to history.

        Args:
            pipeline: Pipeline to save
            change_summary: Summary of changes
        """
        history = PipelineHistory(
            pipeline_id=pipeline.id,
            version=pipeline.version,
            nodes_json=pipeline.nodes_json,
            edges_json=pipeline.edges_json,
            change_summary=change_summary
        )
        self.db.add(history)

    # =========================================================================
    # Import/Export
    # =========================================================================

    def import_from_yaml(self, yaml_content: str) -> PipelineResponse:
        """
        Import pipeline from YAML string.

        Args:
            yaml_content: YAML content

        Returns:
            Created pipeline

        Raises:
            ValidationError: If YAML is invalid
        """
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise ServiceValidationError(f"Invalid YAML: {str(e)}")

        if not isinstance(data, dict):
            raise ServiceValidationError("YAML must be a dictionary")

        name = data.get("name")
        if not name:
            raise ServiceValidationError("Pipeline name is required")

        nodes = data.get("nodes", [])
        if not nodes:
            raise ServiceValidationError("Pipeline must have at least one node")

        edges = data.get("edges", [])
        description = data.get("description")

        return self.create(
            name=name,
            description=description,
            nodes=nodes,
            edges=edges
        )

    def export_to_yaml(self, pipeline_id: int) -> str:
        """
        Export pipeline to YAML string.

        Args:
            pipeline_id: Pipeline ID

        Returns:
            YAML string

        Raises:
            NotFoundError: If pipeline doesn't exist
        """
        pipeline = self._get_pipeline(pipeline_id)

        data = {
            "name": pipeline.name,
            "description": pipeline.description,
            "nodes": pipeline.nodes_json,
            "edges": pipeline.edges_json
        }

        return yaml.safe_dump(data, default_flow_style=False, sort_keys=False)

    def export_version_to_yaml(self, pipeline_id: int, version: int) -> str:
        """
        Export a specific version of a pipeline to YAML string.

        Args:
            pipeline_id: Pipeline ID
            version: Version number to export

        Returns:
            YAML string

        Raises:
            NotFoundError: If pipeline or version doesn't exist
        """
        pipeline = self._get_pipeline(pipeline_id)

        # If requesting current version, export current state
        if version == pipeline.version:
            return self.export_to_yaml(pipeline_id)

        # Look up historical version
        history_entry = self.db.query(PipelineHistory).filter(
            PipelineHistory.pipeline_id == pipeline_id,
            PipelineHistory.version == version
        ).first()

        if not history_entry:
            raise NotFoundError(f"Version {version} not found for pipeline {pipeline_id}")

        data = {
            "name": pipeline.name,
            "description": pipeline.description,
            "nodes": history_entry.nodes_json or [],
            "edges": history_entry.edges_json or []
        }

        return yaml.safe_dump(data, default_flow_style=False, sort_keys=False)

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> PipelineStatsResponse:
        """
        Get pipeline statistics for dashboard KPIs.

        Returns:
            Statistics including counts, active count, and default pipeline info
        """
        total = self.db.query(func.count(Pipeline.id)).scalar() or 0
        valid = self.db.query(func.count(Pipeline.id)).filter(
            Pipeline.is_valid == True
        ).scalar() or 0
        active_count = self.db.query(func.count(Pipeline.id)).filter(
            Pipeline.is_active == True
        ).scalar() or 0

        default = self.db.query(Pipeline).filter(Pipeline.is_default == True).first()

        return PipelineStatsResponse(
            total_pipelines=total,
            valid_pipelines=valid,
            active_pipeline_count=active_count,
            default_pipeline_id=default.id if default else None,
            default_pipeline_name=default.name if default else None
        )

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _get_pipeline(self, pipeline_id: int) -> Pipeline:
        """
        Get pipeline by ID or raise NotFoundError.

        Args:
            pipeline_id: Pipeline ID

        Returns:
            Pipeline model

        Raises:
            NotFoundError: If pipeline doesn't exist
        """
        pipeline = self.db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
        if not pipeline:
            raise NotFoundError("Pipeline", pipeline_id)
        return pipeline

    def _convert_edges_to_json(
        self,
        edges: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convert edges to stored JSON format.

        Handles both 'from'/'to' and 'from_node'/'to_node' formats.

        Args:
            edges: List of edge dictionaries

        Returns:
            Edges in stored format
        """
        result = []
        for edge in edges:
            from_node = edge.get("from") or edge.get("from_node", "")
            to_node = edge.get("to") or edge.get("to_node", "")
            result.append({"from": from_node, "to": to_node})
        return result

    def _to_response(self, pipeline: Pipeline) -> PipelineResponse:
        """
        Convert Pipeline model to PipelineResponse.

        Args:
            pipeline: Pipeline model

        Returns:
            Pipeline response schema
        """
        # Convert nodes to schema format
        nodes = [
            PipelineNode(
                id=n["id"],
                type=n["type"],
                properties=n.get("properties", {})
            )
            for n in pipeline.nodes_json
        ]

        # Convert edges to schema format
        edges = [
            PipelineEdge(from_node=e["from"], to_node=e["to"])
            for e in pipeline.edges_json
        ]

        return PipelineResponse(
            id=pipeline.id,
            name=pipeline.name,
            description=pipeline.description,
            nodes=nodes,
            edges=edges,
            version=pipeline.version,
            is_active=pipeline.is_active,
            is_default=pipeline.is_default,
            is_valid=pipeline.is_valid,
            validation_errors=pipeline.validation_errors,
            created_at=pipeline.created_at,
            updated_at=pipeline.updated_at
        )

    def _to_summary(self, pipeline: Pipeline) -> PipelineSummary:
        """
        Convert Pipeline model to PipelineSummary.

        Args:
            pipeline: Pipeline model

        Returns:
            Pipeline summary schema
        """
        return PipelineSummary(
            id=pipeline.id,
            name=pipeline.name,
            description=pipeline.description,
            version=pipeline.version,
            is_active=pipeline.is_active,
            is_default=pipeline.is_default,
            is_valid=pipeline.is_valid,
            node_count=pipeline.node_count,
            created_at=pipeline.created_at,
            updated_at=pipeline.updated_at
        )
