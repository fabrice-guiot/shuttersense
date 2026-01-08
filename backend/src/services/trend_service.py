"""
Trend service for analyzing historical analysis results.

Provides trend data extraction and aggregation for:
- PhotoStats: Orphaned files over time
- Photo Pairing: Camera usage over time
- Pipeline Validation: Consistency ratios over time

Design:
- JSONB metric extraction from stored results
- Date range filtering with configurable limits
- Collection-grouped data for comparison charts
- Trend direction calculation for summaries
"""

from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_

from backend.src.models import AnalysisResult, Collection, Pipeline, ResultStatus
from backend.src.schemas.trends import (
    PhotoStatsTrendPoint,
    CollectionTrendData,
    PhotoStatsAggregatedPoint,
    PhotoStatsTrendResponse,
    PhotoPairingTrendPoint,
    PhotoPairingCollectionTrend,
    PhotoPairingAggregatedPoint,
    PhotoPairingTrendResponse,
    PipelineValidationTrendPoint,
    PipelineValidationCollectionTrend,
    PipelineValidationAggregatedPoint,
    PipelineValidationTrendResponse,
    DisplayGraphTrendPoint,
    DisplayGraphTrendResponse,
    TrendDirection,
    DataPointCounts,
    TrendSummaryResponse,
)
from backend.src.utils.logging_config import get_logger


logger = get_logger("services")


# Minimum data points needed to calculate trend direction
MIN_TREND_POINTS = 3


def _deduplicate_results_by_day(
    results: List[Any],
    key_func: callable
) -> Dict[str, Any]:
    """
    Deduplicate results by keeping only the LAST result per day for each unique key.

    This ensures that if the same tool was run multiple times on the same
    collection/pipeline on the same day, only the last execution is used.

    Args:
        results: List of AnalysisResult objects (should be ordered by completed_at)
        key_func: Function that takes a result and returns a tuple of (date_key, dedup_key)
                  where date_key is YYYY-MM-DD and dedup_key identifies the unique combination

    Returns:
        Dict mapping (date_key, dedup_key) to the result object
    """
    deduplicated: Dict[Tuple[str, Any], Any] = {}

    for result in results:
        date_key, dedup_key = key_func(result)
        # Later results overwrite earlier ones (keeping the LAST per day)
        deduplicated[(date_key, dedup_key)] = result

    return deduplicated


class TrendService:
    """
    Service for analyzing historical analysis results.

    Extracts trend data from stored JSONB results to show metrics
    changing over time. Supports date filtering and collection comparison.

    Usage:
        >>> service = TrendService(db_session)
        >>> photostats_trends = service.get_photostats_trends([1, 2])
        >>> summary = service.get_trend_summary(collection_id=1)
    """

    def __init__(self, db: Session):
        """
        Initialize trend service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def _parse_collection_ids(self, collection_ids_str: Optional[str]) -> Optional[List[int]]:
        """
        Parse comma-separated collection IDs string.

        Args:
            collection_ids_str: Comma-separated IDs like "1,2,3"

        Returns:
            List of integer IDs or None if empty/invalid
        """
        if not collection_ids_str:
            return None

        try:
            ids = [int(id.strip()) for id in collection_ids_str.split(",") if id.strip()]
            return ids if ids else None
        except ValueError:
            logger.warning(f"Invalid collection_ids format: {collection_ids_str}")
            return None

    def _build_base_query(
        self,
        tool: str,
        collection_ids: Optional[List[int]] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        pipeline_id: Optional[int] = None,
        pipeline_version: Optional[int] = None,
        limit: int = 50
    ):
        """
        Build base query for trend data with common filters.

        Args:
            tool: Tool type filter
            collection_ids: Optional list of collection IDs to filter
            from_date: Optional start date
            to_date: Optional end date
            pipeline_id: Optional pipeline ID (for pipeline_validation)
            pipeline_version: Optional pipeline version (for pipeline_validation)
            limit: Maximum results per collection

        Returns:
            SQLAlchemy query object
        """
        query = self.db.query(AnalysisResult).filter(
            AnalysisResult.tool == tool,
            AnalysisResult.status == ResultStatus.COMPLETED,
            AnalysisResult.collection_id.isnot(None)  # Exclude display-graph results
        )

        if collection_ids:
            query = query.filter(AnalysisResult.collection_id.in_(collection_ids))

        if from_date:
            query = query.filter(
                AnalysisResult.completed_at >= datetime.combine(from_date, datetime.min.time())
            )

        if to_date:
            query = query.filter(
                AnalysisResult.completed_at <= datetime.combine(to_date, datetime.max.time())
            )

        if pipeline_id:
            query = query.filter(AnalysisResult.pipeline_id == pipeline_id)

        if pipeline_version:
            query = query.filter(AnalysisResult.pipeline_version == pipeline_version)

        query = query.order_by(desc(AnalysisResult.completed_at))

        return query

    def get_photostats_trends(
        self,
        collection_ids: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 50
    ) -> PhotoStatsTrendResponse:
        """
        Get PhotoStats trend data.

        Supports two modes:
        - aggregated (default): When no filter or >5 collections - aggregates across all collections
        - comparison: When 1-5 specific collections selected - shows per-collection series

        Deduplication: Keeps only the LAST result per Collection + Day.

        Args:
            collection_ids: Comma-separated collection IDs (1-5 for comparison mode)
            from_date: Filter from date (inclusive)
            to_date: Filter to date (inclusive)
            limit: Maximum data points

        Returns:
            PhotoStats trend data (aggregated or per-collection)
        """
        parsed_ids = self._parse_collection_ids(collection_ids)

        # Determine mode: comparison (1-5 collections) or aggregated (>5 or no filter)
        comparison_mode = parsed_ids is not None and 1 <= len(parsed_ids) <= 5

        query = self._build_base_query(
            tool="photostats",
            collection_ids=parsed_ids,
            from_date=from_date,
            to_date=to_date,
            limit=limit * 10  # Fetch more to allow for deduplication
        )

        # Order by completed_at ASC so later results overwrite earlier
        query = query.order_by(AnalysisResult.completed_at)
        results = query.all()

        # Deduplicate: keep only LAST result per Collection + Day
        def photostats_key(result):
            date_key = result.completed_at.strftime('%Y-%m-%d')
            dedup_key = result.collection_id
            return (date_key, dedup_key)

        deduplicated = _deduplicate_results_by_day(results, photostats_key)

        if comparison_mode:
            # COMPARISON MODE: Group by collection (existing logic)
            collections_data: Dict[int, List[AnalysisResult]] = {}
            for (date_key, collection_id), result in deduplicated.items():
                if collection_id not in collections_data:
                    collections_data[collection_id] = []
                collections_data[collection_id].append(result)

            # Get collection names
            collection_names = {}
            if collections_data:
                collections = self.db.query(Collection).filter(
                    Collection.id.in_(collections_data.keys())
                ).all()
                collection_names = {c.id: c.name for c in collections}

            collection_trends = []
            for collection_id, result_list in collections_data.items():
                if collection_id not in collection_names:
                    continue

                result_list.sort(key=lambda r: r.completed_at)
                result_list = result_list[-limit:]

                data_points = []
                for result in result_list:
                    results_json = result.results_json or {}
                    orphaned_images = results_json.get("orphaned_images", [])
                    orphaned_xmp = results_json.get("orphaned_xmp", [])

                    data_points.append(PhotoStatsTrendPoint(
                        date=result.completed_at,
                        result_id=result.id,
                        orphaned_images_count=len(orphaned_images) if isinstance(orphaned_images, list) else orphaned_images,
                        orphaned_xmp_count=len(orphaned_xmp) if isinstance(orphaned_xmp, list) else orphaned_xmp,
                        total_files=results_json.get("total_files", 0),
                        total_size=results_json.get("total_size", 0)
                    ))

                collection_trends.append(CollectionTrendData(
                    collection_id=collection_id,
                    collection_name=collection_names[collection_id],
                    data_points=data_points
                ))

            return PhotoStatsTrendResponse(mode="comparison", collections=collection_trends)

        else:
            # AGGREGATED MODE: Sum across all collections per day
            aggregated_by_date: Dict[str, Dict[str, Any]] = {}

            for (date_key, collection_id), result in deduplicated.items():
                results_json = result.results_json or {}
                orphaned_images = results_json.get("orphaned_images", [])
                orphaned_xmp = results_json.get("orphaned_xmp", [])

                orphaned_images_count = len(orphaned_images) if isinstance(orphaned_images, list) else orphaned_images
                orphaned_xmp_count = len(orphaned_xmp) if isinstance(orphaned_xmp, list) else orphaned_xmp

                if date_key not in aggregated_by_date:
                    aggregated_by_date[date_key] = {
                        'orphaned_images': 0,
                        'orphaned_metadata': 0,
                        'collections_included': 0
                    }

                agg = aggregated_by_date[date_key]
                agg['orphaned_images'] += orphaned_images_count
                agg['orphaned_metadata'] += orphaned_xmp_count
                agg['collections_included'] += 1

            # Build data points (sorted by date, limited)
            sorted_dates = sorted(aggregated_by_date.keys())[-limit:]
            data_points = []

            for date_key in sorted_dates:
                agg = aggregated_by_date[date_key]
                data_points.append(PhotoStatsAggregatedPoint(
                    date=datetime.strptime(date_key, '%Y-%m-%d'),
                    orphaned_images=agg['orphaned_images'],
                    orphaned_metadata=agg['orphaned_metadata'],
                    collections_included=agg['collections_included']
                ))

            return PhotoStatsTrendResponse(mode="aggregated", data_points=data_points)

    def get_photo_pairing_trends(
        self,
        collection_ids: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 50
    ) -> PhotoPairingTrendResponse:
        """
        Get Photo Pairing trend data.

        Supports two modes:
        - aggregated (default): When no filter or >5 collections - aggregates across all collections
        - comparison: When 1-5 specific collections selected - shows per-collection series

        Note: Camera usage is NOT aggregated (differs per collection).

        Deduplication: Keeps only the LAST result per Collection + Day.

        Args:
            collection_ids: Comma-separated collection IDs (1-5 for comparison mode)
            from_date: Filter from date (inclusive)
            to_date: Filter to date (inclusive)
            limit: Maximum data points

        Returns:
            Photo Pairing trend data (aggregated or per-collection)
        """
        parsed_ids = self._parse_collection_ids(collection_ids)

        # Determine mode: comparison (1-5 collections) or aggregated (>5 or no filter)
        comparison_mode = parsed_ids is not None and 1 <= len(parsed_ids) <= 5

        query = self._build_base_query(
            tool="photo_pairing",
            collection_ids=parsed_ids,
            from_date=from_date,
            to_date=to_date,
            limit=limit * 10  # Fetch more to allow for deduplication
        )

        # Order by completed_at ASC so later results overwrite earlier
        query = query.order_by(AnalysisResult.completed_at)
        results = query.all()

        # Deduplicate: keep only LAST result per Collection + Day
        def photo_pairing_key(result):
            date_key = result.completed_at.strftime('%Y-%m-%d')
            dedup_key = result.collection_id
            return (date_key, dedup_key)

        deduplicated = _deduplicate_results_by_day(results, photo_pairing_key)

        if comparison_mode:
            # COMPARISON MODE: Group by collection (existing logic)
            collections_data: Dict[int, List[AnalysisResult]] = {}
            for (date_key, collection_id), result in deduplicated.items():
                if collection_id not in collections_data:
                    collections_data[collection_id] = []
                collections_data[collection_id].append(result)

            # Get collection names
            collection_names = {}
            if collections_data:
                collections = self.db.query(Collection).filter(
                    Collection.id.in_(collections_data.keys())
                ).all()
                collection_names = {c.id: c.name for c in collections}

            collection_trends = []
            for collection_id, result_list in collections_data.items():
                if collection_id not in collection_names:
                    continue

                result_list.sort(key=lambda r: r.completed_at)
                result_list = result_list[-limit:]

                all_cameras: set = set()
                data_points = []

                for result in result_list:
                    results_json = result.results_json or {}
                    raw_camera_usage = results_json.get("camera_usage", {})
                    all_cameras.update(raw_camera_usage.keys())

                    # Transform camera_usage to simple counts
                    camera_usage: Dict[str, int] = {}
                    for camera_id, value in raw_camera_usage.items():
                        if isinstance(value, dict):
                            camera_usage[camera_id] = value.get("image_count", 0)
                        else:
                            camera_usage[camera_id] = int(value) if value else 0

                    data_points.append(PhotoPairingTrendPoint(
                        date=result.completed_at,
                        result_id=result.id,
                        group_count=results_json.get("group_count", 0),
                        image_count=results_json.get("image_count", 0),
                        camera_usage=camera_usage
                    ))

                collection_trends.append(PhotoPairingCollectionTrend(
                    collection_id=collection_id,
                    collection_name=collection_names[collection_id],
                    cameras=sorted(list(all_cameras)),
                    data_points=data_points
                ))

            return PhotoPairingTrendResponse(mode="comparison", collections=collection_trends)

        else:
            # AGGREGATED MODE: Sum group_count and image_count across all collections per day
            aggregated_by_date: Dict[str, Dict[str, Any]] = {}

            for (date_key, collection_id), result in deduplicated.items():
                results_json = result.results_json or {}

                if date_key not in aggregated_by_date:
                    aggregated_by_date[date_key] = {
                        'group_count': 0,
                        'image_count': 0,
                        'collections_included': 0
                    }

                agg = aggregated_by_date[date_key]
                agg['group_count'] += results_json.get("group_count", 0)
                agg['image_count'] += results_json.get("image_count", 0)
                agg['collections_included'] += 1

            # Build data points (sorted by date, limited)
            sorted_dates = sorted(aggregated_by_date.keys())[-limit:]
            data_points = []

            for date_key in sorted_dates:
                agg = aggregated_by_date[date_key]
                data_points.append(PhotoPairingAggregatedPoint(
                    date=datetime.strptime(date_key, '%Y-%m-%d'),
                    group_count=agg['group_count'],
                    image_count=agg['image_count'],
                    collections_included=agg['collections_included']
                ))

            return PhotoPairingTrendResponse(mode="aggregated", data_points=data_points)

    def get_pipeline_validation_trends(
        self,
        collection_ids: Optional[str] = None,
        pipeline_id: Optional[int] = None,
        pipeline_version: Optional[int] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 50
    ) -> PipelineValidationTrendResponse:
        """
        Get Pipeline Validation trend data.

        Supports two modes:
        - aggregated (default): When no filter or >5 collections - aggregates across all collections
        - comparison: When 1-5 specific collections selected - shows per-collection series

        Aggregated mode series:
        - Overall Consistency % (recalculated from summed counts)
        - Black Box Archive Consistency %
        - Browsable Archive Consistency %
        - Overall Inconsistent %

        Deduplication: Keeps only the LAST result per Collection + Pipeline + Version + Day.

        Args:
            collection_ids: Comma-separated collection IDs (1-5 for comparison mode)
            pipeline_id: Filter by specific pipeline
            pipeline_version: Filter by specific pipeline version
            from_date: Filter from date (inclusive)
            to_date: Filter to date (inclusive)
            limit: Maximum data points

        Returns:
            Pipeline Validation trend data (aggregated or per-collection)
        """
        parsed_ids = self._parse_collection_ids(collection_ids)

        # Determine mode: comparison (1-5 collections) or aggregated (>5 or no filter)
        comparison_mode = parsed_ids is not None and 1 <= len(parsed_ids) <= 5

        query = self._build_base_query(
            tool="pipeline_validation",
            collection_ids=parsed_ids,
            from_date=from_date,
            to_date=to_date,
            pipeline_id=pipeline_id,
            pipeline_version=pipeline_version,
            limit=limit * 10  # Fetch more to allow for deduplication
        )

        # Order by completed_at ASC so later results overwrite earlier
        query = query.order_by(AnalysisResult.completed_at)
        results = query.all()

        # Deduplicate: keep only LAST result per Collection + Pipeline + Version + Day
        def pipeline_validation_key(result):
            date_key = result.completed_at.strftime('%Y-%m-%d')
            dedup_key = (result.collection_id, result.pipeline_id, result.pipeline_version)
            return (date_key, dedup_key)

        deduplicated = _deduplicate_results_by_day(results, pipeline_validation_key)

        if comparison_mode:
            # COMPARISON MODE: Group by collection (existing logic)
            collections_data: Dict[int, List[AnalysisResult]] = {}
            for (date_key, (collection_id, _, _)), result in deduplicated.items():
                if collection_id not in collections_data:
                    collections_data[collection_id] = []
                collections_data[collection_id].append(result)

            # Get collection names
            collection_names = {}
            if collections_data:
                collections = self.db.query(Collection).filter(
                    Collection.id.in_(collections_data.keys())
                ).all()
                collection_names = {c.id: c.name for c in collections}

            # Get pipeline names
            pipeline_ids_set = set()
            for result_list in collections_data.values():
                for result in result_list:
                    if result.pipeline_id:
                        pipeline_ids_set.add(result.pipeline_id)

            pipeline_names = {}
            if pipeline_ids_set:
                pipelines = self.db.query(Pipeline).filter(
                    Pipeline.id.in_(pipeline_ids_set)
                ).all()
                pipeline_names = {p.id: p.name for p in pipelines}

            collection_trends = []
            for collection_id, result_list in collections_data.items():
                if collection_id not in collection_names:
                    continue

                result_list.sort(key=lambda r: r.completed_at)
                result_list = result_list[-limit:]

                data_points = []
                for result in result_list:
                    results_json = result.results_json or {}
                    consistency_counts = results_json.get("consistency_counts", {})
                    consistent = consistency_counts.get("CONSISTENT", 0)
                    partial = consistency_counts.get("PARTIAL", 0)
                    inconsistent = consistency_counts.get("INCONSISTENT", 0)

                    total = consistent + partial + inconsistent
                    consistent_ratio = (consistent / total * 100) if total > 0 else 0.0
                    partial_ratio = (partial / total * 100) if total > 0 else 0.0
                    inconsistent_ratio = (inconsistent / total * 100) if total > 0 else 0.0

                    data_points.append(PipelineValidationTrendPoint(
                        date=result.completed_at,
                        result_id=result.id,
                        pipeline_id=result.pipeline_id,
                        pipeline_name=pipeline_names.get(result.pipeline_id),
                        consistent_count=consistent,
                        partial_count=partial,
                        inconsistent_count=inconsistent,
                        consistent_ratio=round(consistent_ratio, 1),
                        partial_ratio=round(partial_ratio, 1),
                        inconsistent_ratio=round(inconsistent_ratio, 1)
                    ))

                collection_trends.append(PipelineValidationCollectionTrend(
                    collection_id=collection_id,
                    collection_name=collection_names[collection_id],
                    data_points=data_points
                ))

            return PipelineValidationTrendResponse(mode="comparison", collections=collection_trends)

        else:
            # AGGREGATED MODE: Sum counts across collections, recalculate percentages
            aggregated_by_date: Dict[str, Dict[str, Any]] = {}

            for (date_key, (collection_id, _, _)), result in deduplicated.items():
                results_json = result.results_json or {}

                if date_key not in aggregated_by_date:
                    aggregated_by_date[date_key] = {
                        # Overall counts
                        'consistent': 0,
                        'partial': 0,
                        'inconsistent': 0,
                        # Per-termination counts
                        'black_box_consistent': 0,
                        'black_box_total': 0,
                        'browsable_consistent': 0,
                        'browsable_total': 0,
                        'collections_included': 0
                    }

                agg = aggregated_by_date[date_key]

                # Overall consistency counts
                consistency_counts = results_json.get("consistency_counts", {})
                agg['consistent'] += consistency_counts.get("CONSISTENT", 0)
                agg['partial'] += consistency_counts.get("PARTIAL", 0)
                agg['inconsistent'] += consistency_counts.get("INCONSISTENT", 0)

                # Per-termination counts (from by_termination field)
                by_termination = results_json.get("by_termination", {})

                # Black Box Archive
                black_box = by_termination.get("Black Box Archive", {})
                bb_consistent = black_box.get("CONSISTENT", 0)
                bb_partial = black_box.get("PARTIAL", 0)
                bb_inconsistent = black_box.get("INCONSISTENT", 0)
                agg['black_box_consistent'] += bb_consistent
                agg['black_box_total'] += bb_consistent + bb_partial + bb_inconsistent

                # Browsable Archive
                browsable = by_termination.get("Browsable Archive", {})
                br_consistent = browsable.get("CONSISTENT", 0)
                br_partial = browsable.get("PARTIAL", 0)
                br_inconsistent = browsable.get("INCONSISTENT", 0)
                agg['browsable_consistent'] += br_consistent
                agg['browsable_total'] += br_consistent + br_partial + br_inconsistent

                agg['collections_included'] += 1

            # Build data points with recalculated percentages
            sorted_dates = sorted(aggregated_by_date.keys())[-limit:]
            data_points = []

            for date_key in sorted_dates:
                agg = aggregated_by_date[date_key]

                total_images = agg['consistent'] + agg['partial'] + agg['inconsistent']

                # Calculate percentages from summed counts
                overall_consistency_pct = (agg['consistent'] / total_images * 100) if total_images > 0 else 0.0
                overall_inconsistent_pct = (agg['inconsistent'] / total_images * 100) if total_images > 0 else 0.0

                black_box_consistency_pct = (
                    agg['black_box_consistent'] / agg['black_box_total'] * 100
                ) if agg['black_box_total'] > 0 else 0.0

                browsable_consistency_pct = (
                    agg['browsable_consistent'] / agg['browsable_total'] * 100
                ) if agg['browsable_total'] > 0 else 0.0

                data_points.append(PipelineValidationAggregatedPoint(
                    date=datetime.strptime(date_key, '%Y-%m-%d'),
                    overall_consistency_pct=round(overall_consistency_pct, 1),
                    overall_inconsistent_pct=round(overall_inconsistent_pct, 1),
                    black_box_consistency_pct=round(black_box_consistency_pct, 1),
                    browsable_consistency_pct=round(browsable_consistency_pct, 1),
                    total_images=total_images,
                    consistent_count=agg['consistent'],
                    inconsistent_count=agg['inconsistent'],
                    collections_included=agg['collections_included']
                ))

            return PipelineValidationTrendResponse(mode="aggregated", data_points=data_points)

    def get_display_graph_trends(
        self,
        pipeline_ids: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 50
    ) -> DisplayGraphTrendResponse:
        """
        Get display-graph trend data aggregated across all pipelines.

        Display-graph results have collection_id = NULL and track pipeline
        path enumeration metrics over time.

        Deduplication: Keeps only the LAST result per Pipeline + Version + Day.
        Aggregation: Sums metrics across all pipelines for each day.

        Args:
            pipeline_ids: Comma-separated pipeline IDs (optional filter)
            from_date: Filter from date (inclusive)
            to_date: Filter to date (inclusive)
            limit: Maximum data points

        Returns:
            Aggregated display-graph trend data
        """
        from backend.src.schemas.trends import PipelineIncluded

        # Parse pipeline IDs
        parsed_ids = None
        if pipeline_ids:
            try:
                parsed_ids = [int(pid.strip()) for pid in pipeline_ids.split(',') if pid.strip()]
            except ValueError:
                logger.warning(f"Invalid pipeline_ids format: {pipeline_ids}")
                parsed_ids = None

        # Build base query for display-graph results (collection_id IS NULL)
        query = self.db.query(AnalysisResult).filter(
            AnalysisResult.tool == "pipeline_validation",
            AnalysisResult.status == ResultStatus.COMPLETED,
            AnalysisResult.collection_id.is_(None),  # Display-graph has no collection
            AnalysisResult.pipeline_id.isnot(None)
        )

        if parsed_ids:
            query = query.filter(AnalysisResult.pipeline_id.in_(parsed_ids))

        if from_date:
            query = query.filter(
                AnalysisResult.completed_at >= datetime.combine(from_date, datetime.min.time())
            )

        if to_date:
            query = query.filter(
                AnalysisResult.completed_at <= datetime.combine(to_date, datetime.max.time())
            )

        # Order by completed_at ASC so later results overwrite earlier
        query = query.order_by(AnalysisResult.completed_at)
        results = query.all()

        # Deduplicate: keep only LAST result per Pipeline + Version + Day
        def display_graph_key(result):
            date_key = result.completed_at.strftime('%Y-%m-%d')
            # Dedup by pipeline + version (no collection for display-graph)
            dedup_key = (result.pipeline_id, result.pipeline_version)
            return (date_key, dedup_key)

        deduplicated = _deduplicate_results_by_day(results, display_graph_key)

        # Track pipeline info for response
        pipeline_result_counts: Dict[int, int] = {}

        # Aggregate deduplicated results by date
        aggregated_by_date: Dict[str, Dict[str, int]] = {}

        for (date_key, (pipeline_id, _)), result in deduplicated.items():
            pipeline_result_counts[pipeline_id] = pipeline_result_counts.get(pipeline_id, 0) + 1

            results_json = result.results_json or {}

            if date_key not in aggregated_by_date:
                aggregated_by_date[date_key] = {
                    'total_paths': 0,
                    'valid_paths': 0,
                    'black_box_archive_paths': 0,
                    'browsable_archive_paths': 0
                }

            agg = aggregated_by_date[date_key]
            agg['total_paths'] += results_json.get('total_paths', 0)
            agg['valid_paths'] += results_json.get('non_truncated_paths', 0)

            # Extract termination type counts
            by_term = results_json.get('non_truncated_by_termination', {})
            agg['black_box_archive_paths'] += by_term.get('Black Box Archive', 0)
            agg['browsable_archive_paths'] += by_term.get('Browsable Archive', 0)

        # Get pipeline names
        pipeline_names = {}
        if pipeline_result_counts:
            pipelines = self.db.query(Pipeline).filter(
                Pipeline.id.in_(pipeline_result_counts.keys())
            ).all()
            pipeline_names = {p.id: p.name for p in pipelines}

        # Build data points (sorted by date, limited)
        sorted_dates = sorted(aggregated_by_date.keys())[-limit:]
        data_points = []

        for date_key in sorted_dates:
            agg = aggregated_by_date[date_key]
            data_points.append(DisplayGraphTrendPoint(
                date=datetime.strptime(date_key, '%Y-%m-%d'),
                total_paths=agg['total_paths'],
                valid_paths=agg['valid_paths'],
                black_box_archive_paths=agg['black_box_archive_paths'],
                browsable_archive_paths=agg['browsable_archive_paths']
            ))

        # Build pipelines included list
        pipelines_included = [
            PipelineIncluded(
                pipeline_id=pid,
                pipeline_name=pipeline_names.get(pid, f"Pipeline {pid}"),
                result_count=count
            )
            for pid, count in pipeline_result_counts.items()
        ]

        return DisplayGraphTrendResponse(
            data_points=data_points,
            pipelines_included=pipelines_included
        )

    def _calculate_trend_direction(
        self,
        values: List[float],
        higher_is_better: bool = False
    ) -> TrendDirection:
        """
        Calculate trend direction from a series of values.

        Uses simple linear regression slope to determine if trend is
        improving, degrading, or stable.

        Args:
            values: List of metric values (oldest first)
            higher_is_better: Whether higher values indicate improvement

        Returns:
            Trend direction enum value
        """
        if len(values) < MIN_TREND_POINTS:
            return TrendDirection.INSUFFICIENT_DATA

        # Calculate simple linear regression slope
        n = len(values)
        x_sum = sum(range(n))
        y_sum = sum(values)
        xy_sum = sum(i * v for i, v in enumerate(values))
        x2_sum = sum(i * i for i in range(n))

        # Slope formula: (n*Σxy - Σx*Σy) / (n*Σx² - (Σx)²)
        denominator = n * x2_sum - x_sum * x_sum
        if denominator == 0:
            return TrendDirection.STABLE

        slope = (n * xy_sum - x_sum * y_sum) / denominator

        # Determine direction based on slope and whether higher is better
        threshold = 0.05 * (max(values) - min(values)) if max(values) != min(values) else 0.01

        if abs(slope) < threshold:
            return TrendDirection.STABLE

        is_increasing = slope > 0

        if higher_is_better:
            return TrendDirection.IMPROVING if is_increasing else TrendDirection.DEGRADING
        else:
            return TrendDirection.DEGRADING if is_increasing else TrendDirection.IMPROVING

    def get_trend_summary(
        self,
        collection_id: Optional[int] = None
    ) -> TrendSummaryResponse:
        """
        Get trend summary for dashboard overview.

        Provides quick indicators of trend direction for orphaned files
        and consistency metrics.

        Args:
            collection_id: Optional collection ID filter

        Returns:
            Trend summary with direction indicators and latest timestamps
        """
        # Base query filter
        base_filter = [AnalysisResult.status == ResultStatus.COMPLETED]
        if collection_id:
            base_filter.append(AnalysisResult.collection_id == collection_id)
        else:
            # Exclude display-graph results for aggregate view
            base_filter.append(AnalysisResult.collection_id.isnot(None))

        # Get data point counts
        photostats_count = self.db.query(func.count(AnalysisResult.id)).filter(
            and_(*base_filter, AnalysisResult.tool == "photostats")
        ).scalar() or 0

        photo_pairing_count = self.db.query(func.count(AnalysisResult.id)).filter(
            and_(*base_filter, AnalysisResult.tool == "photo_pairing")
        ).scalar() or 0

        pipeline_validation_count = self.db.query(func.count(AnalysisResult.id)).filter(
            and_(*base_filter, AnalysisResult.tool == "pipeline_validation")
        ).scalar() or 0

        # Get latest timestamps
        last_photostats = self.db.query(func.max(AnalysisResult.completed_at)).filter(
            and_(*base_filter, AnalysisResult.tool == "photostats")
        ).scalar()

        last_photo_pairing = self.db.query(func.max(AnalysisResult.completed_at)).filter(
            and_(*base_filter, AnalysisResult.tool == "photo_pairing")
        ).scalar()

        last_pipeline_validation = self.db.query(func.max(AnalysisResult.completed_at)).filter(
            and_(*base_filter, AnalysisResult.tool == "pipeline_validation")
        ).scalar()

        # Calculate orphaned trend (from PhotoStats) using AGGREGATED data
        # Same logic as get_photostats_trends aggregated mode:
        # 1. Deduplicate per Collection + Day
        # 2. Aggregate across all collections per day
        # 3. Calculate trend from daily aggregated totals
        orphaned_trend = TrendDirection.INSUFFICIENT_DATA
        if photostats_count >= MIN_TREND_POINTS:
            photostats_results = self.db.query(AnalysisResult).filter(
                and_(*base_filter, AnalysisResult.tool == "photostats")
            ).order_by(AnalysisResult.completed_at).all()

            # Deduplicate: keep only LAST result per Collection + Day
            deduplicated: Dict[Tuple[str, int], AnalysisResult] = {}
            for result in photostats_results:
                date_key = result.completed_at.strftime('%Y-%m-%d')
                dedup_key = (date_key, result.collection_id)
                deduplicated[dedup_key] = result  # Later results overwrite earlier

            # Aggregate across collections per day
            aggregated_by_date: Dict[str, int] = {}
            for (date_key, _), result in deduplicated.items():
                results_json = result.results_json or {}
                orphaned_images = results_json.get("orphaned_images", [])
                orphaned_xmp = results_json.get("orphaned_xmp", [])
                total_orphaned = (
                    (len(orphaned_images) if isinstance(orphaned_images, list) else orphaned_images) +
                    (len(orphaned_xmp) if isinstance(orphaned_xmp, list) else orphaned_xmp)
                )
                aggregated_by_date[date_key] = aggregated_by_date.get(date_key, 0) + total_orphaned

            # Sort by date and extract values
            sorted_dates = sorted(aggregated_by_date.keys())
            orphaned_values = [aggregated_by_date[d] for d in sorted_dates]

            if len(orphaned_values) >= MIN_TREND_POINTS:
                orphaned_trend = self._calculate_trend_direction(
                    orphaned_values,
                    higher_is_better=False  # Lower orphaned count is better
                )

        # Calculate consistency trend (from Pipeline Validation) using AGGREGATED data
        # Same logic as get_pipeline_validation_trends aggregated mode:
        # 1. Deduplicate per Collection + Pipeline + Version + Day
        # 2. Aggregate counts across all collections per day
        # 3. Recalculate percentage from aggregated counts
        # 4. Calculate trend from daily percentages
        consistency_trend = TrendDirection.INSUFFICIENT_DATA
        if pipeline_validation_count >= MIN_TREND_POINTS:
            pipeline_results = self.db.query(AnalysisResult).filter(
                and_(*base_filter, AnalysisResult.tool == "pipeline_validation")
            ).order_by(AnalysisResult.completed_at).all()

            # Deduplicate: keep only LAST result per Collection + Pipeline + Version + Day
            deduplicated: Dict[Tuple[str, Tuple[int, Any, Any]], AnalysisResult] = {}
            for result in pipeline_results:
                date_key = result.completed_at.strftime('%Y-%m-%d')
                dedup_key = (date_key, (result.collection_id, result.pipeline_id, result.pipeline_version))
                deduplicated[dedup_key] = result

            # Aggregate counts across collections per day
            aggregated_by_date: Dict[str, Dict[str, int]] = {}
            for (date_key, _), result in deduplicated.items():
                results_json = result.results_json or {}
                consistency_counts = results_json.get("consistency_counts", {})

                if date_key not in aggregated_by_date:
                    aggregated_by_date[date_key] = {'consistent': 0, 'total': 0}

                agg = aggregated_by_date[date_key]
                agg['consistent'] += consistency_counts.get("CONSISTENT", 0)
                agg['total'] += sum(consistency_counts.values())

            # Calculate percentages from aggregated counts
            sorted_dates = sorted(aggregated_by_date.keys())
            consistency_values = []
            for date_key in sorted_dates:
                agg = aggregated_by_date[date_key]
                ratio = (agg['consistent'] / agg['total'] * 100) if agg['total'] > 0 else 0
                consistency_values.append(ratio)

            if len(consistency_values) >= MIN_TREND_POINTS:
                consistency_trend = self._calculate_trend_direction(
                    consistency_values,
                    higher_is_better=True  # Higher consistency is better
                )

        return TrendSummaryResponse(
            collection_id=collection_id,
            orphaned_trend=orphaned_trend,
            consistency_trend=consistency_trend,
            last_photostats=last_photostats,
            last_photo_pairing=last_photo_pairing,
            last_pipeline_validation=last_pipeline_validation,
            data_points_available=DataPointCounts(
                photostats=photostats_count,
                photo_pairing=photo_pairing_count,
                pipeline_validation=pipeline_validation_count
            )
        )
