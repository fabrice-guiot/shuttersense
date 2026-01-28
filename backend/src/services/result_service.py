"""
Result service for managing analysis results.

Provides CRUD operations and statistics for analysis results:
- List results with filtering and pagination
- Get result details
- Delete results
- Download HTML reports
- Aggregate statistics for KPIs

Design:
- Efficient queries with eager loading for collection names
- Support for complex filtering (date range, tool, status)
- Pagination with configurable limits
- Statistics aggregation for dashboard KPIs
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any, Tuple

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, asc

from backend.src.models import AnalysisResult, Collection, Pipeline, ResultStatus
from backend.src.models.connector import Connector
from backend.src.schemas.results import (
    SortField, SortOrder, AnalysisResultSummary, AnalysisResultResponse,
    ResultStatsResponse, ResultListResponse
)
from backend.src.services.exceptions import NotFoundError
from backend.src.services.guid import GuidService
from backend.src.utils.logging_config import get_logger


logger = get_logger("services")

# Maximum items to include in API responses for large arrays
RESULT_ITEMS_LIMIT = 20


def sanitize_results(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove internal IDs from results for API presentation.

    Internal IDs (like pipeline_id) are stored in the database for join queries
    but should not be exposed in the API response. The corresponding GUIDs are
    available at the top level of the response.

    Args:
        results: Tool-specific results dictionary

    Returns:
        Results with internal IDs removed
    """
    if not results:
        return results

    result_copy = dict(results)

    # Fields containing internal IDs that should not be exposed in API
    internal_id_fields = ['pipeline_id', 'collection_id', 'connector_id']

    # Remove from top level
    for field in internal_id_fields:
        result_copy.pop(field, None)

    # Also check nested 'results' object (pipeline_validation stores data there)
    if 'results' in result_copy and isinstance(result_copy['results'], dict):
        nested_results = dict(result_copy['results'])
        for field in internal_id_fields:
            nested_results.pop(field, None)
        result_copy['results'] = nested_results

    return result_copy


def truncate_results(results: Dict[str, Any], limit: int = RESULT_ITEMS_LIMIT) -> Dict[str, Any]:
    """
    Truncate large arrays in results to prevent API response bloat.

    For tool results containing large arrays (e.g., paths in pipeline_validation),
    this function limits the array size and adds truncation metadata.

    Args:
        results: Tool-specific results dictionary
        limit: Maximum items to return for large arrays

    Returns:
        Results with truncated arrays and added metadata:
        - _truncated: Dict mapping array field names to their total counts
        - Arrays are limited to `limit` items

    Example:
        Input: {"paths": [1,2,3,...,1000], "total_paths": 1000}
        Output: {"paths": [1,2,...,20], "total_paths": 1000, "_truncated": {"paths": 1000}}
    """
    if not results:
        return results

    truncated = {}
    result_copy = dict(results)

    # Fields that can contain large arrays
    large_array_fields = ['paths', 'files', 'issues', 'orphans', 'groups', 'patterns']

    for field in large_array_fields:
        if field in result_copy and isinstance(result_copy[field], list):
            total = len(result_copy[field])
            if total > limit:
                result_copy[field] = result_copy[field][:limit]
                truncated[field] = total
                logger.debug(f"Truncated {field} from {total} to {limit} items")

    if truncated:
        result_copy['_truncated'] = truncated

    return result_copy


class ResultService:
    """
    Service for managing analysis results.

    Handles CRUD operations and statistics aggregation for
    analysis results stored by tool executions.

    Usage:
        >>> service = ResultService(db_session)
        >>> results, total = service.list_results(collection_id=1)
        >>> result = service.get_result(result_id=1)
        >>> stats = service.get_stats()
    """

    def __init__(self, db: Session):
        """
        Initialize result service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def list_results(
        self,
        team_id: int,
        collection_guid: Optional[str] = None,
        tool: Optional[str] = None,
        status: Optional[ResultStatus] = None,
        no_change_copy: Optional[bool] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: SortField = SortField.CREATED_AT,
        sort_order: SortOrder = SortOrder.DESC
    ) -> Tuple[List[AnalysisResultSummary], int]:
        """
        List analysis results with filtering and pagination.

        Args:
            team_id: Team ID for tenant isolation
            collection_guid: Filter by collection GUID (col_xxx)
            tool: Filter by tool type
            status: Filter by result status
            no_change_copy: Filter by no_change_copy flag (True=copies, False=originals)
            from_date: Filter from date (inclusive)
            to_date: Filter to date (inclusive)
            limit: Maximum results to return (1-100)
            offset: Number of results to skip
            sort_by: Field to sort by
            sort_order: Sort direction

        Returns:
            Tuple of (result summaries, total count)
        """
        # Build base query with optional collection join (LEFT JOIN for display_graph results)
        query = self.db.query(AnalysisResult).outerjoin(
            Collection, AnalysisResult.collection_id == Collection.id
        ).filter(AnalysisResult.team_id == team_id)

        # Apply filters
        if collection_guid:
            # Resolve collection GUID to internal ID
            collection_uuid = GuidService.parse_identifier(collection_guid, expected_prefix="col")
            collection = self.db.query(Collection).filter(Collection.uuid == collection_uuid).first()
            if collection:
                query = query.filter(AnalysisResult.collection_id == collection.id)
            else:
                # Collection not found - return empty results
                return [], 0
        if tool:
            query = query.filter(AnalysisResult.tool == tool)
        if status:
            query = query.filter(AnalysisResult.status == status)
        if no_change_copy is not None:
            if no_change_copy:
                query = query.filter(AnalysisResult.no_change_copy == True)
            else:
                # Include both False and NULL as "original" results
                query = query.filter(
                    (AnalysisResult.no_change_copy == False) |
                    (AnalysisResult.no_change_copy.is_(None))
                )
        if from_date:
            query = query.filter(AnalysisResult.created_at >= datetime.combine(from_date, datetime.min.time()))
        if to_date:
            query = query.filter(AnalysisResult.created_at <= datetime.combine(to_date, datetime.max.time()))

        # Get total count before pagination
        total = query.count()

        # Apply sorting
        sort_column = {
            SortField.CREATED_AT: AnalysisResult.created_at,
            SortField.DURATION_SECONDS: AnalysisResult.duration_seconds,
            SortField.FILES_SCANNED: AnalysisResult.files_scanned,
        }.get(sort_by, AnalysisResult.created_at)

        if sort_order == SortOrder.DESC:
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        # Apply pagination
        results = query.offset(offset).limit(limit).all()

        # Convert to summaries with collection, pipeline, and connector names
        summaries = []
        for result in results:
            collection = self.db.query(Collection).filter(
                Collection.id == result.collection_id
            ).first()

            # Get pipeline info if applicable
            pipeline = None
            if result.pipeline_id:
                pipeline = self.db.query(Pipeline).filter(
                    Pipeline.id == result.pipeline_id
                ).first()

            # Get connector info for inventory tools (Issue #107)
            # Filter by team_id for tenant isolation
            connector = None
            if result.connector_id:
                connector = self.db.query(Connector).filter(
                    Connector.id == result.connector_id,
                    Connector.team_id == team_id
                ).first()

            summaries.append(AnalysisResultSummary(
                guid=result.guid,
                collection_guid=collection.guid if collection else None,
                collection_name=collection.name if collection else None,
                tool=result.tool,
                pipeline_guid=pipeline.guid if pipeline else None,
                pipeline_version=result.pipeline_version,
                pipeline_name=pipeline.name if pipeline else None,
                # Connector fields for inventory tools (Issue #107)
                connector_guid=connector.guid if connector else None,
                connector_name=connector.name if connector else None,
                status=result.status.value if result.status else "UNKNOWN",
                started_at=result.started_at,
                completed_at=result.completed_at,
                duration_seconds=result.duration_seconds,
                files_scanned=result.files_scanned,
                issues_found=result.issues_found,
                has_report=result.has_report,
                # Storage Optimization Fields (Issue #92)
                input_state_hash=result.input_state_hash,
                no_change_copy=result.no_change_copy,
            ))

        return summaries, total

    def get_result_by_guid(self, guid: str, team_id: Optional[int] = None) -> Optional[AnalysisResult]:
        """
        Get result by GUID.

        Args:
            guid: Result GUID (e.g., "res_01hgw...")
            team_id: Optional team ID for tenant isolation

        Returns:
            AnalysisResult instance or None if not found

        Raises:
            ValueError: If GUID format is invalid or prefix doesn't match "res"

        Example:
            >>> result = service.get_result_by_guid("res_01hgw2bbg...", team_id=1)
        """
        uuid_value = GuidService.parse_identifier(guid, expected_prefix="res")
        query = self.db.query(AnalysisResult).filter(AnalysisResult.uuid == uuid_value)
        if team_id is not None:
            query = query.filter(AnalysisResult.team_id == team_id)
        return query.first()

    def get_result(self, result_id: int, team_id: Optional[int] = None) -> AnalysisResultResponse:
        """
        Get analysis result details.

        Args:
            result_id: Result ID
            team_id: Optional team ID for tenant isolation

        Returns:
            Full result details including tool-specific data

        Raises:
            NotFoundError: If result doesn't exist
        """
        query = self.db.query(AnalysisResult).filter(AnalysisResult.id == result_id)
        if team_id is not None:
            query = query.filter(AnalysisResult.team_id == team_id)
        result = query.first()

        if not result:
            raise NotFoundError("Result", result_id)

        # Get related collection
        collection = self.db.query(Collection).filter(
            Collection.id == result.collection_id
        ).first()

        # Get related pipeline if applicable
        pipeline = None
        if result.pipeline_id:
            pipeline = self.db.query(Pipeline).filter(
                Pipeline.id == result.pipeline_id
            ).first()

        # Get connector info for inventory tools (Issue #107)
        # Conditionally filter by team_id for tenant isolation
        connector = None
        if result.connector_id:
            connector_query = self.db.query(Connector).filter(
                Connector.id == result.connector_id
            )
            if team_id is not None:
                connector_query = connector_query.filter(Connector.team_id == team_id)
            connector = connector_query.first()

        # Process results: truncate large arrays and remove internal IDs
        processed_results = truncate_results(result.results_json or {})
        processed_results = sanitize_results(processed_results)

        # For NO_CHANGE results, check if source result exists (Issue #92)
        source_result_exists = None
        has_report = result.has_report  # Default from model property

        if result.no_change_copy and result.download_report_from:
            try:
                source_uuid = AnalysisResult.parse_guid(result.download_report_from)
                source_query = self.db.query(AnalysisResult).filter(
                    AnalysisResult.uuid == source_uuid
                )
                if team_id is not None:
                    source_query = source_query.filter(AnalysisResult.team_id == team_id)
                source_result = source_query.first()

                source_result_exists = source_result is not None
                # Update has_report: only true if source exists and has report
                has_report = source_result is not None and (
                    source_result.report_html is not None or
                    (source_result.no_change_copy and source_result.download_report_from)
                )
            except ValueError:
                source_result_exists = False
                has_report = False

        return AnalysisResultResponse(
            guid=result.guid,
            collection_guid=collection.guid if collection else None,
            collection_name=collection.name if collection else None,
            tool=result.tool,
            pipeline_guid=pipeline.guid if pipeline else None,
            pipeline_version=result.pipeline_version,
            pipeline_name=pipeline.name if pipeline else None,
            # Connector fields for inventory tools (Issue #107)
            connector_guid=connector.guid if connector else None,
            connector_name=connector.name if connector else None,
            status=result.status.value if result.status else "UNKNOWN",
            started_at=result.started_at,
            completed_at=result.completed_at,
            duration_seconds=result.duration_seconds,
            files_scanned=result.files_scanned,
            issues_found=result.issues_found,
            error_message=result.error_message,
            has_report=has_report,
            results=processed_results,
            created_at=result.created_at,
            # Storage Optimization Fields (Issue #92)
            input_state_hash=result.input_state_hash,
            no_change_copy=result.no_change_copy,
            download_report_from=result.download_report_from,
            source_result_exists=source_result_exists,
        )

    def delete_result(self, result_id: int, team_id: Optional[int] = None) -> str:
        """
        Delete an analysis result.

        Args:
            result_id: Result ID to delete
            team_id: Optional team ID for tenant isolation

        Returns:
            GUID of deleted result

        Raises:
            NotFoundError: If result doesn't exist
        """
        query = self.db.query(AnalysisResult).filter(AnalysisResult.id == result_id)
        if team_id is not None:
            query = query.filter(AnalysisResult.team_id == team_id)
        result = query.first()

        if not result:
            raise NotFoundError("Result", result_id)

        deleted_guid = result.guid
        self.db.delete(result)
        self.db.commit()

        logger.info(f"Deleted result {deleted_guid}")
        return deleted_guid

    def get_report(self, result_id: int, team_id: Optional[int] = None) -> Optional[str]:
        """
        Get HTML report for a result.

        For NO_CHANGE results (Issue #92), follows the download_report_from
        reference to get the report from the source result.

        Args:
            result_id: Result ID
            team_id: Optional team ID for tenant isolation

        Returns:
            HTML report content if available

        Raises:
            NotFoundError: If result doesn't exist, has no report, or source result deleted
        """
        query = self.db.query(AnalysisResult).filter(AnalysisResult.id == result_id)
        if team_id is not None:
            query = query.filter(AnalysisResult.team_id == team_id)
        result = query.first()

        if not result:
            raise NotFoundError("Result", result_id)

        # Direct report available
        if result.report_html:
            return result.report_html

        # For NO_CHANGE results, follow the download_report_from reference (Issue #92)
        if result.download_report_from:
            try:
                source_uuid = AnalysisResult.parse_guid(result.download_report_from)
                source_query = self.db.query(AnalysisResult).filter(
                    AnalysisResult.uuid == source_uuid
                )
                if team_id is not None:
                    source_query = source_query.filter(AnalysisResult.team_id == team_id)
                source_result = source_query.first()

                if source_result and source_result.report_html:
                    return source_result.report_html

                # Source result was deleted or has no report
                raise NotFoundError(
                    "Source report (referenced result has been deleted)",
                    result.download_report_from
                )
            except ValueError:
                # Invalid GUID format
                raise NotFoundError("Report for result", result_id)

        # No report and no reference
        raise NotFoundError("Report for result", result_id)

    def get_report_with_metadata(self, result_id: int, team_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get HTML report with metadata for filename generation.

        Returns both the HTML content and metadata needed to generate
        a consistent filename following CLI tool conventions:
        {tool}_report_{collection_name}_{collection_id}_{timestamp}.html

        For NO_CHANGE results (Issue #92), follows the download_report_from
        reference to get the report from the source result.

        Args:
            result_id: Result ID
            team_id: Optional team ID for tenant isolation

        Returns:
            Dictionary with 'html', 'tool', 'collection_name', 'collection_id',
            and 'timestamp' keys

        Raises:
            NotFoundError: If result doesn't exist or has no report
        """
        query = self.db.query(AnalysisResult).filter(AnalysisResult.id == result_id)
        if team_id is not None:
            query = query.filter(AnalysisResult.team_id == team_id)
        result = query.first()

        if not result:
            raise NotFoundError("Result", result_id)

        # For NO_CHANGE results, follow the download_report_from reference (Issue #92)
        report_html = result.report_html
        if not report_html and result.download_report_from:
            # Look up the source result by GUID
            try:
                source_uuid = AnalysisResult.parse_guid(result.download_report_from)
                source_query = self.db.query(AnalysisResult).filter(
                    AnalysisResult.uuid == source_uuid
                )
                if team_id is not None:
                    source_query = source_query.filter(AnalysisResult.team_id == team_id)
                source_result = source_query.first()

                if source_result and source_result.report_html:
                    report_html = source_result.report_html
            except ValueError:
                pass  # Invalid GUID format, fall through to NotFoundError

        if not report_html:
            raise NotFoundError("Report for result", result_id)

        # Get collection for name
        collection = self.db.query(Collection).filter(
            Collection.id == result.collection_id
        ).first()

        collection_name = collection.name if collection else "unknown"
        # Sanitize collection name for filename (replace spaces and special chars)
        safe_collection_name = "".join(
            c if c.isalnum() or c in "-_" else "_"
            for c in collection_name
        ).strip("_")

        # Use completed_at timestamp, fallback to created_at
        timestamp = result.completed_at or result.created_at
        timestamp_str = timestamp.strftime("%Y-%m-%d_%H-%M-%S") if timestamp else "unknown"

        return {
            "html": report_html,
            "tool": result.tool,
            "collection_name": safe_collection_name,
            "collection_id": result.collection_id,
            "timestamp": timestamp_str,
        }

    def get_stats(self, team_id: int) -> ResultStatsResponse:
        """
        Get aggregate statistics for results.

        Args:
            team_id: Team ID for tenant isolation

        Returns:
            Statistics including totals, counts by status, and by tool
        """
        # Total results
        total = self.db.query(func.count(AnalysisResult.id)).filter(
            AnalysisResult.team_id == team_id
        ).scalar() or 0

        # Count by status
        completed = self.db.query(func.count(AnalysisResult.id)).filter(
            AnalysisResult.team_id == team_id,
            AnalysisResult.status == ResultStatus.COMPLETED
        ).scalar() or 0

        failed = self.db.query(func.count(AnalysisResult.id)).filter(
            AnalysisResult.team_id == team_id,
            AnalysisResult.status == ResultStatus.FAILED
        ).scalar() or 0

        # Count by tool
        tool_counts = self.db.query(
            AnalysisResult.tool,
            func.count(AnalysisResult.id)
        ).filter(
            AnalysisResult.team_id == team_id
        ).group_by(AnalysisResult.tool).all()

        by_tool = {tool: count for tool, count in tool_counts}

        # Last run time
        last_result = self.db.query(AnalysisResult).filter(
            AnalysisResult.team_id == team_id
        ).order_by(
            desc(AnalysisResult.completed_at)
        ).first()

        return ResultStatsResponse(
            total_results=total,
            completed_count=completed,
            failed_count=failed,
            by_tool=by_tool,
            last_run=last_result.completed_at if last_result else None,
        )
