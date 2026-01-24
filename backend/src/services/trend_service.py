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


def _generate_complete_date_range(
    data_dates: List[str],
    from_date: Optional[date] = None,
    to_date: Optional[date] = None
) -> List[str]:
    """
    Generate a complete list of dates for the timeline.

    The date range is determined by:
    - If from_date is specified: start from from_date (even if no data exists)
    - If from_date is None ("all time"): start from the earliest data date
    - If to_date is specified: end at to_date
    - If to_date is None: end at today

    This ensures the timeline shows all days in the selected range,
    even those without data points.

    Args:
        data_dates: List of date strings (YYYY-MM-DD format) that have data
        from_date: Optional start date filter (if None, uses earliest data date)
        to_date: Optional end date filter (if None, uses today)

    Returns:
        List of date strings for complete date range
    """
    today = date.today()

    # Determine start date
    if from_date:
        # Explicit filter: always use it
        start_date = from_date
    elif data_dates:
        # "All time" mode: use earliest data date
        parsed_dates = [datetime.strptime(d, '%Y-%m-%d').date() for d in data_dates]
        start_date = min(parsed_dates)
    else:
        # No data and no filter: return empty
        return []

    # Determine end date
    end_date = to_date if to_date else today

    # Generate all dates in range
    all_dates = []
    current = start_date
    while current <= end_date:
        all_dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)

    return all_dates


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
        team_id: int,
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
            team_id: Team ID for tenant isolation
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
            # Include both COMPLETED and NO_CHANGE results (Issue #92: Storage Optimization)
            AnalysisResult.status.in_([ResultStatus.COMPLETED, ResultStatus.NO_CHANGE]),
            AnalysisResult.collection_id.isnot(None),  # Exclude display-graph results
            AnalysisResult.team_id == team_id
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

    def _get_seed_values(
        self,
        tool: str,
        team_id: int,
        collection_ids: List[int],
        before_date: date,
        pipeline_id: Optional[int] = None,
        pipeline_version: Optional[int] = None
    ) -> Dict[int, Dict[str, Any]]:
        """
        Get the latest result for each collection before the window starts.

        This provides the "seed state" for fill-forward logic (Issue #105).
        Collections without any results before the window will not be in the returned dict.

        Args:
            tool: Tool type (photostats, photo_pairing, pipeline_validation)
            team_id: Team ID for tenant isolation
            collection_ids: List of collection IDs to seed
            before_date: Date before which to find the latest result
            pipeline_id: Optional pipeline ID filter (for pipeline_validation)
            pipeline_version: Optional pipeline version filter (for pipeline_validation)

        Returns:
            Dict mapping collection_id -> extracted metric values
        """
        if not collection_ids:
            return {}

        # Query the latest result per collection before the window
        # Using subquery to get max completed_at per collection
        from sqlalchemy import distinct
        from sqlalchemy.orm import aliased

        # Build base filters for the subquery
        subquery_filters = [
            AnalysisResult.tool == tool,
            AnalysisResult.team_id == team_id,
            AnalysisResult.collection_id.in_(collection_ids),
            AnalysisResult.status.in_([ResultStatus.COMPLETED, ResultStatus.NO_CHANGE]),
            AnalysisResult.completed_at < datetime.combine(before_date, datetime.min.time())
        ]

        # Add pipeline filtering for pipeline_validation tool
        if tool == "pipeline_validation":
            if pipeline_id is not None:
                subquery_filters.append(AnalysisResult.pipeline_id == pipeline_id)
            if pipeline_version is not None:
                subquery_filters.append(AnalysisResult.pipeline_version == pipeline_version)

        # Find the max completed_at per collection before the window
        subquery = self.db.query(
            AnalysisResult.collection_id,
            func.max(AnalysisResult.completed_at).label('max_completed')
        ).filter(
            *subquery_filters
        ).group_by(AnalysisResult.collection_id).subquery()

        # Build filters for the main query (same as subquery for consistency)
        main_filters = [
            AnalysisResult.tool == tool,
            AnalysisResult.team_id == team_id
        ]
        if tool == "pipeline_validation":
            if pipeline_id is not None:
                main_filters.append(AnalysisResult.pipeline_id == pipeline_id)
            if pipeline_version is not None:
                main_filters.append(AnalysisResult.pipeline_version == pipeline_version)

        # Join to get the actual result rows
        results = self.db.query(AnalysisResult).join(
            subquery,
            and_(
                AnalysisResult.collection_id == subquery.c.collection_id,
                AnalysisResult.completed_at == subquery.c.max_completed
            )
        ).filter(
            *main_filters
        ).all()

        seed_values: Dict[int, Dict[str, Any]] = {}

        for result in results:
            results_json = result.results_json or {}

            if tool == "photostats":
                orphaned_images = results_json.get("orphaned_images", [])
                orphaned_xmp = results_json.get("orphaned_xmp", [])
                seed_values[result.collection_id] = {
                    'orphaned_images': len(orphaned_images) if isinstance(orphaned_images, list) else orphaned_images,
                    'orphaned_xmp': len(orphaned_xmp) if isinstance(orphaned_xmp, list) else orphaned_xmp,
                    'no_change_copy': result.no_change_copy or False
                }
            elif tool == "photo_pairing":
                seed_values[result.collection_id] = {
                    'group_count': results_json.get("group_count", 0),
                    'image_count': results_json.get("image_count", 0),
                    'no_change_copy': result.no_change_copy or False
                }
            elif tool == "pipeline_validation":
                counts = results_json.get("consistency_counts", {})
                by_termination = results_json.get("by_termination", {})
                black_box = by_termination.get("Black Box Archive", {})
                browsable = by_termination.get("Browsable Archive", {})
                seed_values[result.collection_id] = {
                    'consistent_count': counts.get("CONSISTENT", 0),
                    'partial_count': counts.get("PARTIAL", 0),
                    'inconsistent_count': counts.get("INCONSISTENT", 0),
                    'black_box_consistent': black_box.get("CONSISTENT", 0),
                    'black_box_partial': black_box.get("PARTIAL", 0),
                    'black_box_inconsistent': black_box.get("INCONSISTENT", 0),
                    'browsable_consistent': browsable.get("CONSISTENT", 0),
                    'browsable_partial': browsable.get("PARTIAL", 0),
                    'browsable_inconsistent': browsable.get("INCONSISTENT", 0),
                    'no_change_copy': result.no_change_copy or False
                }

        logger.debug(f"Seed values for {tool}: {len(seed_values)} collections seeded before {before_date}")
        return seed_values

    def _get_display_graph_seed_values(
        self,
        team_id: int,
        pipeline_version_pairs: List[Tuple[int, int]],
        before_date: date,
        pipeline_ids: Optional[List[int]] = None
    ) -> Dict[Tuple[int, int], Dict[str, Any]]:
        """
        Get the latest display-graph result for each pipeline+version before the window starts.

        This provides the "seed state" for fill-forward logic in display-graph mode (Issue #105).
        Unlike collection-based seeds, this keys by (pipeline_id, version).

        Args:
            team_id: Team ID for tenant isolation
            pipeline_version_pairs: List of (pipeline_id, version) tuples to seed
            before_date: Date before which to find the latest result
            pipeline_ids: Optional list of pipeline IDs to filter by

        Returns:
            Dict mapping (pipeline_id, version) -> extracted metric values
        """
        if not pipeline_version_pairs:
            return {}

        # Build filter for all pipeline+version pairs
        pair_conditions = [
            and_(
                AnalysisResult.pipeline_id == pid,
                AnalysisResult.pipeline_version == ver
            )
            for pid, ver in pipeline_version_pairs
        ]

        # Build base filters
        base_filters = [
            AnalysisResult.tool == "pipeline_validation",
            AnalysisResult.team_id == team_id,
            AnalysisResult.collection_id.is_(None),  # Display-graph only
            AnalysisResult.status.in_([ResultStatus.COMPLETED, ResultStatus.NO_CHANGE]),
            AnalysisResult.completed_at < datetime.combine(before_date, datetime.min.time()),
            or_(*pair_conditions)
        ]

        # Add pipeline_ids filter if specified
        if pipeline_ids:
            base_filters.append(AnalysisResult.pipeline_id.in_(pipeline_ids))

        # Query all results before the window for these pipeline+version pairs
        results = self.db.query(AnalysisResult).filter(
            *base_filters
        ).order_by(AnalysisResult.completed_at).all()

        # Keep only the latest result per pipeline+version
        seed_values: Dict[Tuple[int, int], Dict[str, Any]] = {}
        for result in results:
            key = (result.pipeline_id, result.pipeline_version)
            results_json = result.results_json or {}
            by_term = results_json.get('non_truncated_by_termination', {})

            # Later results overwrite earlier (we ordered by completed_at ASC)
            seed_values[key] = {
                'total_paths': results_json.get('total_paths', 0),
                'valid_paths': results_json.get('non_truncated_paths', 0),
                'black_box_archive_paths': by_term.get('Black Box Archive', 0),
                'browsable_archive_paths': by_term.get('Browsable Archive', 0)
            }

        logger.debug(f"Display-graph seed values: {len(seed_values)} pipeline+version pairs seeded before {before_date}")
        return seed_values

    def get_photostats_trends(
        self,
        team_id: int,
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
            team_id: Team ID for tenant isolation
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
            team_id=team_id,
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
                        total_size=results_json.get("total_size", 0),
                        no_change_copy=result.no_change_copy or False
                    ))

                collection_trends.append(CollectionTrendData(
                    collection_id=collection_id,
                    collection_name=collection_names[collection_id],
                    data_points=data_points
                ))

            return PhotoStatsTrendResponse(mode="comparison", collections=collection_trends)

        else:
            # AGGREGATED MODE: Sum across all collections per day with fill-forward (Issue #105)

            # Step 1: Extract per-collection metrics for each day from deduplicated results
            per_collection_by_date: Dict[str, Dict[int, Dict[str, Any]]] = {}
            all_collection_ids_in_window: set = set()

            for (date_key, collection_id), result in deduplicated.items():
                results_json = result.results_json or {}
                orphaned_images = results_json.get("orphaned_images", [])
                orphaned_xmp = results_json.get("orphaned_xmp", [])

                orphaned_images_count = len(orphaned_images) if isinstance(orphaned_images, list) else orphaned_images
                orphaned_xmp_count = len(orphaned_xmp) if isinstance(orphaned_xmp, list) else orphaned_xmp

                if date_key not in per_collection_by_date:
                    per_collection_by_date[date_key] = {}

                per_collection_by_date[date_key][collection_id] = {
                    'orphaned_images': orphaned_images_count,
                    'orphaned_xmp': orphaned_xmp_count,
                    'no_change_copy': result.no_change_copy or False
                }
                all_collection_ids_in_window.add(collection_id)

            # Step 2: Build complete date range
            all_dates = _generate_complete_date_range(
                list(per_collection_by_date.keys()),
                from_date=from_date,
                to_date=to_date
            )

            if not all_dates:
                return PhotoStatsTrendResponse(mode="aggregated", data_points=[])

            # Step 3: Get seed values (latest result before window for each collection)
            # Include collections with results in window AND collections with results before window
            window_start = datetime.strptime(all_dates[0], '%Y-%m-%d').date()

            # Find collection IDs that have any photostats results for this team
            # If collection_ids filter was provided, only consider those collections
            relevant_collection_filters = [
                AnalysisResult.tool == "photostats",
                AnalysisResult.team_id == team_id,
                AnalysisResult.status.in_([ResultStatus.COMPLETED, ResultStatus.NO_CHANGE]),
                AnalysisResult.collection_id.isnot(None)
            ]
            # Apply collection filter if provided (aggregated mode with >5 collections)
            if parsed_ids:
                relevant_collection_filters.append(AnalysisResult.collection_id.in_(parsed_ids))

            all_relevant_collection_ids = self.db.query(
                AnalysisResult.collection_id
            ).filter(
                *relevant_collection_filters
            ).distinct().all()
            all_relevant_collection_ids = {r[0] for r in all_relevant_collection_ids}

            seed_values = self._get_seed_values(
                tool="photostats",
                team_id=team_id,
                collection_ids=list(all_relevant_collection_ids),
                before_date=window_start
            )

            # Step 4: Fill-forward aggregation
            # Track last known value for each collection (start with seeds)
            last_known: Dict[int, Dict[str, Any]] = dict(seed_values)

            # Only apply limit when no date range is specified ("all time" mode)
            if from_date is None and to_date is None:
                sorted_dates = all_dates[-limit:] if len(all_dates) > limit else all_dates
            else:
                sorted_dates = all_dates

            data_points = []
            prev_was_all_no_change = False

            for date_key in sorted_dates:
                daily_agg = {
                    'orphaned_images': 0,
                    'orphaned_metadata': 0,
                    'collections_included': 0,
                    'no_change_count': 0,
                    'calculated_count': 0,
                    'has_completed': False
                }

                # Get collections that have results for this day
                day_results = per_collection_by_date.get(date_key, {})

                # Determine which collections to include:
                # - Collections that have actual results on this day
                # - Collections that have been seen before (in window or as seed)
                collections_to_include = set(day_results.keys()) | set(last_known.keys())

                for collection_id in collections_to_include:
                    if collection_id in day_results:
                        # Actual result for this day
                        metrics = day_results[collection_id]
                        daily_agg['orphaned_images'] += metrics['orphaned_images']
                        daily_agg['orphaned_metadata'] += metrics['orphaned_xmp']
                        daily_agg['collections_included'] += 1
                        if metrics['no_change_copy']:
                            daily_agg['no_change_count'] += 1
                        else:
                            daily_agg['has_completed'] = True
                        # Update last known
                        last_known[collection_id] = metrics
                    elif collection_id in last_known:
                        # Fill forward from last known value
                        metrics = last_known[collection_id]
                        daily_agg['orphaned_images'] += metrics['orphaned_images']
                        daily_agg['orphaned_metadata'] += metrics['orphaned_xmp']
                        daily_agg['collections_included'] += 1
                        daily_agg['calculated_count'] += 1
                        # NO_CHANGE status carries forward
                        if metrics.get('no_change_copy', False):
                            daily_agg['no_change_count'] += 1

                # Build data point
                if daily_agg['collections_included'] > 0:
                    has_transition = prev_was_all_no_change and daily_agg['has_completed']
                    data_points.append(PhotoStatsAggregatedPoint(
                        date=datetime.strptime(date_key, '%Y-%m-%d').date(),
                        orphaned_images=daily_agg['orphaned_images'],
                        orphaned_metadata=daily_agg['orphaned_metadata'],
                        collections_included=daily_agg['collections_included'],
                        no_change_count=daily_agg['no_change_count'],
                        has_transition=has_transition,
                        calculated_count=daily_agg['calculated_count']
                    ))
                    prev_was_all_no_change = not daily_agg['has_completed'] and daily_agg['no_change_count'] > 0
                else:
                    # No data for this date (no results and no seeds)
                    data_points.append(PhotoStatsAggregatedPoint(
                        date=datetime.strptime(date_key, '%Y-%m-%d').date(),
                        orphaned_images=None,
                        orphaned_metadata=None,
                        collections_included=0,
                        no_change_count=0,
                        has_transition=False,
                        calculated_count=0
                    ))

            # Log fill-forward summary (Issue #105)
            total_calculated = sum(p.calculated_count for p in data_points)
            if total_calculated > 0:
                logger.debug(
                    f"PhotoStats aggregation: {len(data_points)} data points, "
                    f"{total_calculated} fill-forward values used"
                )

            return PhotoStatsTrendResponse(mode="aggregated", data_points=data_points)

    def get_photo_pairing_trends(
        self,
        team_id: int,
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
            team_id: Team ID for tenant isolation
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
            team_id=team_id,
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
                        camera_usage=camera_usage,
                        no_change_copy=result.no_change_copy or False
                    ))

                collection_trends.append(PhotoPairingCollectionTrend(
                    collection_id=collection_id,
                    collection_name=collection_names[collection_id],
                    cameras=sorted(list(all_cameras)),
                    data_points=data_points
                ))

            return PhotoPairingTrendResponse(mode="comparison", collections=collection_trends)

        else:
            # AGGREGATED MODE: Sum across all collections per day with fill-forward (Issue #105)

            # Step 1: Extract per-collection metrics for each day from deduplicated results
            per_collection_by_date: Dict[str, Dict[int, Dict[str, Any]]] = {}
            all_collection_ids_in_window: set = set()

            for (date_key, collection_id), result in deduplicated.items():
                results_json = result.results_json or {}

                if date_key not in per_collection_by_date:
                    per_collection_by_date[date_key] = {}

                per_collection_by_date[date_key][collection_id] = {
                    'group_count': results_json.get("group_count", 0),
                    'image_count': results_json.get("image_count", 0),
                    'no_change_copy': result.no_change_copy or False
                }
                all_collection_ids_in_window.add(collection_id)

            # Step 2: Build complete date range
            all_dates = _generate_complete_date_range(
                list(per_collection_by_date.keys()),
                from_date=from_date,
                to_date=to_date
            )

            if not all_dates:
                return PhotoPairingTrendResponse(mode="aggregated", data_points=[])

            # Step 3: Get seed values (latest result before window for each collection)
            window_start = datetime.strptime(all_dates[0], '%Y-%m-%d').date()

            # Find collection IDs that have any photo_pairing results for this team
            # If collection_ids filter was provided, only consider those collections
            relevant_collection_filters = [
                AnalysisResult.tool == "photo_pairing",
                AnalysisResult.team_id == team_id,
                AnalysisResult.status.in_([ResultStatus.COMPLETED, ResultStatus.NO_CHANGE]),
                AnalysisResult.collection_id.isnot(None)
            ]
            # Apply collection filter if provided (aggregated mode with >5 collections)
            if parsed_ids:
                relevant_collection_filters.append(AnalysisResult.collection_id.in_(parsed_ids))

            all_relevant_collection_ids = self.db.query(
                AnalysisResult.collection_id
            ).filter(
                *relevant_collection_filters
            ).distinct().all()
            all_relevant_collection_ids = {r[0] for r in all_relevant_collection_ids}

            seed_values = self._get_seed_values(
                tool="photo_pairing",
                team_id=team_id,
                collection_ids=list(all_relevant_collection_ids),
                before_date=window_start
            )

            # Step 4: Fill-forward aggregation
            last_known: Dict[int, Dict[str, Any]] = dict(seed_values)

            # Only apply limit when no date range is specified ("all time" mode)
            if from_date is None and to_date is None:
                sorted_dates = all_dates[-limit:] if len(all_dates) > limit else all_dates
            else:
                sorted_dates = all_dates

            data_points = []
            prev_was_all_no_change = False

            for date_key in sorted_dates:
                daily_agg = {
                    'group_count': 0,
                    'image_count': 0,
                    'collections_included': 0,
                    'no_change_count': 0,
                    'calculated_count': 0,
                    'has_completed': False
                }

                day_results = per_collection_by_date.get(date_key, {})
                collections_to_include = set(day_results.keys()) | set(last_known.keys())

                for collection_id in collections_to_include:
                    if collection_id in day_results:
                        # Actual result for this day
                        metrics = day_results[collection_id]
                        daily_agg['group_count'] += metrics['group_count']
                        daily_agg['image_count'] += metrics['image_count']
                        daily_agg['collections_included'] += 1
                        if metrics['no_change_copy']:
                            daily_agg['no_change_count'] += 1
                        else:
                            daily_agg['has_completed'] = True
                        last_known[collection_id] = metrics
                    elif collection_id in last_known:
                        # Fill forward from last known value
                        metrics = last_known[collection_id]
                        daily_agg['group_count'] += metrics['group_count']
                        daily_agg['image_count'] += metrics['image_count']
                        daily_agg['collections_included'] += 1
                        daily_agg['calculated_count'] += 1
                        if metrics.get('no_change_copy', False):
                            daily_agg['no_change_count'] += 1

                # Build data point
                if daily_agg['collections_included'] > 0:
                    has_transition = prev_was_all_no_change and daily_agg['has_completed']
                    data_points.append(PhotoPairingAggregatedPoint(
                        date=datetime.strptime(date_key, '%Y-%m-%d').date(),
                        group_count=daily_agg['group_count'],
                        image_count=daily_agg['image_count'],
                        collections_included=daily_agg['collections_included'],
                        no_change_count=daily_agg['no_change_count'],
                        has_transition=has_transition,
                        calculated_count=daily_agg['calculated_count']
                    ))
                    prev_was_all_no_change = not daily_agg['has_completed'] and daily_agg['no_change_count'] > 0
                else:
                    # No data for this date (no results and no seeds)
                    data_points.append(PhotoPairingAggregatedPoint(
                        date=datetime.strptime(date_key, '%Y-%m-%d').date(),
                        group_count=None,
                        image_count=None,
                        collections_included=0,
                        no_change_count=0,
                        has_transition=False,
                        calculated_count=0
                    ))

            # Log fill-forward summary (Issue #105)
            total_calculated = sum(p.calculated_count for p in data_points)
            if total_calculated > 0:
                logger.debug(
                    f"PhotoPairing aggregation: {len(data_points)} data points, "
                    f"{total_calculated} fill-forward values used"
                )

            return PhotoPairingTrendResponse(mode="aggregated", data_points=data_points)

    def get_pipeline_validation_trends(
        self,
        team_id: int,
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
            team_id: Team ID for tenant isolation
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
            team_id=team_id,
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
                        inconsistent_ratio=round(inconsistent_ratio, 1),
                        no_change_copy=result.no_change_copy or False
                    ))

                collection_trends.append(PipelineValidationCollectionTrend(
                    collection_id=collection_id,
                    collection_name=collection_names[collection_id],
                    data_points=data_points
                ))

            return PipelineValidationTrendResponse(mode="comparison", collections=collection_trends)

        else:
            # AGGREGATED MODE: Sum counts across collections with fill-forward (Issue #105)

            # Step 1: Extract per-collection metrics for each day from deduplicated results
            per_collection_by_date: Dict[str, Dict[int, Dict[str, Any]]] = {}
            all_collection_ids_in_window: set = set()

            for (date_key, (collection_id, _, _)), result in deduplicated.items():
                results_json = result.results_json or {}
                consistency_counts = results_json.get("consistency_counts", {})
                by_termination = results_json.get("by_termination", {})

                # Extract all metrics we need to fill-forward
                black_box = by_termination.get("Black Box Archive", {})
                browsable = by_termination.get("Browsable Archive", {})

                if date_key not in per_collection_by_date:
                    per_collection_by_date[date_key] = {}

                # Use same key names as _get_seed_values for consistent fill-forward
                per_collection_by_date[date_key][collection_id] = {
                    'consistent_count': consistency_counts.get("CONSISTENT", 0),
                    'partial_count': consistency_counts.get("PARTIAL", 0),
                    'inconsistent_count': consistency_counts.get("INCONSISTENT", 0),
                    'black_box_consistent': black_box.get("CONSISTENT", 0),
                    'black_box_partial': black_box.get("PARTIAL", 0),
                    'black_box_inconsistent': black_box.get("INCONSISTENT", 0),
                    'browsable_consistent': browsable.get("CONSISTENT", 0),
                    'browsable_partial': browsable.get("PARTIAL", 0),
                    'browsable_inconsistent': browsable.get("INCONSISTENT", 0),
                    'no_change_copy': result.no_change_copy or False
                }
                all_collection_ids_in_window.add(collection_id)

            # Step 2: Build complete date range
            all_dates = _generate_complete_date_range(
                list(per_collection_by_date.keys()),
                from_date=from_date,
                to_date=to_date
            )

            if not all_dates:
                return PipelineValidationTrendResponse(mode="aggregated", data_points=[])

            # Step 3: Get seed values (latest result before window for each collection)
            window_start = datetime.strptime(all_dates[0], '%Y-%m-%d').date()

            # Find collection IDs that have any pipeline_validation results for this team
            # Filter by pipeline_id/pipeline_version if specified, and by collection_ids if provided
            relevant_collection_filters = [
                AnalysisResult.tool == "pipeline_validation",
                AnalysisResult.team_id == team_id,
                AnalysisResult.status.in_([ResultStatus.COMPLETED, ResultStatus.NO_CHANGE]),
                AnalysisResult.collection_id.isnot(None)
            ]
            # Apply collection filter if provided (aggregated mode with >5 collections)
            if parsed_ids:
                relevant_collection_filters.append(AnalysisResult.collection_id.in_(parsed_ids))
            if pipeline_id is not None:
                relevant_collection_filters.append(AnalysisResult.pipeline_id == pipeline_id)
            if pipeline_version is not None:
                relevant_collection_filters.append(AnalysisResult.pipeline_version == pipeline_version)

            all_relevant_collection_ids = self.db.query(
                AnalysisResult.collection_id
            ).filter(
                *relevant_collection_filters
            ).distinct().all()
            all_relevant_collection_ids = {r[0] for r in all_relevant_collection_ids}

            seed_values = self._get_seed_values(
                tool="pipeline_validation",
                team_id=team_id,
                collection_ids=list(all_relevant_collection_ids),
                before_date=window_start,
                pipeline_id=pipeline_id,
                pipeline_version=pipeline_version
            )

            # Step 4: Fill-forward aggregation
            last_known: Dict[int, Dict[str, Any]] = dict(seed_values)

            # Only apply limit when no date range is specified ("all time" mode)
            if from_date is None and to_date is None:
                sorted_dates = all_dates[-limit:] if len(all_dates) > limit else all_dates
            else:
                sorted_dates = all_dates

            data_points = []
            prev_was_all_no_change = False

            for date_key in sorted_dates:
                daily_agg = {
                    'consistent': 0,
                    'partial': 0,
                    'inconsistent': 0,
                    'black_box_consistent': 0,
                    'black_box_total': 0,
                    'browsable_consistent': 0,
                    'browsable_total': 0,
                    'collections_included': 0,
                    'no_change_count': 0,
                    'calculated_count': 0,
                    'has_completed': False
                }

                day_results = per_collection_by_date.get(date_key, {})
                collections_to_include = set(day_results.keys()) | set(last_known.keys())

                for collection_id in collections_to_include:
                    if collection_id in day_results:
                        # Actual result for this day
                        metrics = day_results[collection_id]
                        daily_agg['consistent'] += metrics['consistent_count']
                        daily_agg['partial'] += metrics['partial_count']
                        daily_agg['inconsistent'] += metrics['inconsistent_count']
                        daily_agg['black_box_consistent'] += metrics.get('black_box_consistent', 0)
                        daily_agg['black_box_total'] += (
                            metrics.get('black_box_consistent', 0) +
                            metrics.get('black_box_partial', 0) +
                            metrics.get('black_box_inconsistent', 0)
                        )
                        daily_agg['browsable_consistent'] += metrics.get('browsable_consistent', 0)
                        daily_agg['browsable_total'] += (
                            metrics.get('browsable_consistent', 0) +
                            metrics.get('browsable_partial', 0) +
                            metrics.get('browsable_inconsistent', 0)
                        )
                        daily_agg['collections_included'] += 1
                        if metrics['no_change_copy']:
                            daily_agg['no_change_count'] += 1
                        else:
                            daily_agg['has_completed'] = True
                        last_known[collection_id] = metrics
                    elif collection_id in last_known:
                        # Fill forward from last known value (includes by_termination data)
                        metrics = last_known[collection_id]
                        daily_agg['consistent'] += metrics['consistent_count']
                        daily_agg['partial'] += metrics['partial_count']
                        daily_agg['inconsistent'] += metrics['inconsistent_count']
                        daily_agg['black_box_consistent'] += metrics.get('black_box_consistent', 0)
                        daily_agg['black_box_total'] += (
                            metrics.get('black_box_consistent', 0) +
                            metrics.get('black_box_partial', 0) +
                            metrics.get('black_box_inconsistent', 0)
                        )
                        daily_agg['browsable_consistent'] += metrics.get('browsable_consistent', 0)
                        daily_agg['browsable_total'] += (
                            metrics.get('browsable_consistent', 0) +
                            metrics.get('browsable_partial', 0) +
                            metrics.get('browsable_inconsistent', 0)
                        )
                        daily_agg['collections_included'] += 1
                        daily_agg['calculated_count'] += 1
                        if metrics.get('no_change_copy', False):
                            daily_agg['no_change_count'] += 1

                # Build data point
                if daily_agg['collections_included'] > 0:
                    total_images = daily_agg['consistent'] + daily_agg['partial'] + daily_agg['inconsistent']

                    overall_consistency_pct = (daily_agg['consistent'] / total_images * 100) if total_images > 0 else 0.0
                    overall_inconsistent_pct = (daily_agg['inconsistent'] / total_images * 100) if total_images > 0 else 0.0

                    black_box_consistency_pct = (
                        daily_agg['black_box_consistent'] / daily_agg['black_box_total'] * 100
                    ) if daily_agg['black_box_total'] > 0 else 0.0

                    browsable_consistency_pct = (
                        daily_agg['browsable_consistent'] / daily_agg['browsable_total'] * 100
                    ) if daily_agg['browsable_total'] > 0 else 0.0

                    has_transition = prev_was_all_no_change and daily_agg['has_completed']
                    data_points.append(PipelineValidationAggregatedPoint(
                        date=datetime.strptime(date_key, '%Y-%m-%d').date(),
                        overall_consistency_pct=round(overall_consistency_pct, 1),
                        overall_inconsistent_pct=round(overall_inconsistent_pct, 1),
                        black_box_consistency_pct=round(black_box_consistency_pct, 1),
                        browsable_consistency_pct=round(browsable_consistency_pct, 1),
                        total_images=total_images,
                        consistent_count=daily_agg['consistent'],
                        inconsistent_count=daily_agg['inconsistent'],
                        collections_included=daily_agg['collections_included'],
                        no_change_count=daily_agg['no_change_count'],
                        has_transition=has_transition,
                        calculated_count=daily_agg['calculated_count']
                    ))
                    prev_was_all_no_change = not daily_agg['has_completed'] and daily_agg['no_change_count'] > 0
                else:
                    # No data for this date (no results and no seeds)
                    data_points.append(PipelineValidationAggregatedPoint(
                        date=datetime.strptime(date_key, '%Y-%m-%d').date(),
                        overall_consistency_pct=None,
                        overall_inconsistent_pct=None,
                        black_box_consistency_pct=None,
                        browsable_consistency_pct=None,
                        total_images=None,
                        consistent_count=None,
                        inconsistent_count=None,
                        collections_included=0,
                        no_change_count=0,
                        has_transition=False,
                        calculated_count=0
                    ))

            # Log fill-forward summary (Issue #105)
            total_calculated = sum(p.calculated_count for p in data_points)
            if total_calculated > 0:
                logger.debug(
                    f"PipelineValidation aggregation: {len(data_points)} data points, "
                    f"{total_calculated} fill-forward values used"
                )

            return PipelineValidationTrendResponse(mode="aggregated", data_points=data_points)

    def get_display_graph_trends(
        self,
        team_id: int,
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
            team_id: Team ID for tenant isolation
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
            AnalysisResult.pipeline_id.isnot(None),
            AnalysisResult.team_id == team_id
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

        # AGGREGATED MODE with fill-forward by pipeline+version (Issue #105)

        # Step 1: Extract per-pipeline+version metrics for each day from deduplicated results
        # Key is (pipeline_id, version), value is metrics dict
        per_pipeline_by_date: Dict[str, Dict[Tuple[int, int], Dict[str, Any]]] = {}
        all_pipeline_versions_in_window: set = set()
        pipeline_result_counts: Dict[int, int] = {}

        for (date_key, (pipeline_id, version)), result in deduplicated.items():
            results_json = result.results_json or {}
            by_term = results_json.get('non_truncated_by_termination', {})

            if date_key not in per_pipeline_by_date:
                per_pipeline_by_date[date_key] = {}

            per_pipeline_by_date[date_key][(pipeline_id, version)] = {
                'total_paths': results_json.get('total_paths', 0),
                'valid_paths': results_json.get('non_truncated_paths', 0),
                'black_box_archive_paths': by_term.get('Black Box Archive', 0),
                'browsable_archive_paths': by_term.get('Browsable Archive', 0)
            }
            all_pipeline_versions_in_window.add((pipeline_id, version))
            pipeline_result_counts[pipeline_id] = pipeline_result_counts.get(pipeline_id, 0) + 1

        # Step 2: Build complete date range
        all_dates = _generate_complete_date_range(
            list(per_pipeline_by_date.keys()),
            from_date=from_date,
            to_date=to_date
        )

        if not all_dates:
            return DisplayGraphTrendResponse(data_points=[], pipelines_included=[])

        # Step 3: Get seed values (latest result before window for each pipeline+version)
        window_start = datetime.strptime(all_dates[0], '%Y-%m-%d').date()

        # Find ALL pipeline+version pairs that have any display-graph results for this team
        # Filter by parsed_ids if specified
        relevant_pairs_filters = [
            AnalysisResult.tool == "pipeline_validation",
            AnalysisResult.team_id == team_id,
            AnalysisResult.collection_id.is_(None),
            AnalysisResult.status == ResultStatus.COMPLETED,
            AnalysisResult.pipeline_id.isnot(None)
        ]
        if parsed_ids:
            relevant_pairs_filters.append(AnalysisResult.pipeline_id.in_(parsed_ids))

        all_relevant_pairs_query = self.db.query(
            AnalysisResult.pipeline_id,
            AnalysisResult.pipeline_version
        ).filter(
            *relevant_pairs_filters
        ).distinct().all()
        all_relevant_pairs = [(r[0], r[1]) for r in all_relevant_pairs_query]

        seed_values = self._get_display_graph_seed_values(
            team_id=team_id,
            pipeline_version_pairs=all_relevant_pairs,
            before_date=window_start,
            pipeline_ids=parsed_ids
        )

        # Step 4: Fill-forward aggregation by pipeline+version
        last_known: Dict[Tuple[int, int], Dict[str, Any]] = dict(seed_values)

        # Only apply limit when no date range is specified ("all time" mode)
        if from_date is None and to_date is None:
            sorted_dates = all_dates[-limit:] if len(all_dates) > limit else all_dates
        else:
            sorted_dates = all_dates

        data_points = []

        for date_key in sorted_dates:
            daily_agg = {
                'total_paths': 0,
                'valid_paths': 0,
                'black_box_archive_paths': 0,
                'browsable_archive_paths': 0
            }

            day_results = per_pipeline_by_date.get(date_key, {})
            pipelines_to_include = set(day_results.keys()) | set(last_known.keys())

            for pipeline_key in pipelines_to_include:
                if pipeline_key in day_results:
                    # Actual result for this day
                    metrics = day_results[pipeline_key]
                    daily_agg['total_paths'] += metrics['total_paths']
                    daily_agg['valid_paths'] += metrics['valid_paths']
                    daily_agg['black_box_archive_paths'] += metrics['black_box_archive_paths']
                    daily_agg['browsable_archive_paths'] += metrics['browsable_archive_paths']
                    last_known[pipeline_key] = metrics
                elif pipeline_key in last_known:
                    # Fill forward from last known value
                    metrics = last_known[pipeline_key]
                    daily_agg['total_paths'] += metrics['total_paths']
                    daily_agg['valid_paths'] += metrics['valid_paths']
                    daily_agg['black_box_archive_paths'] += metrics['black_box_archive_paths']
                    daily_agg['browsable_archive_paths'] += metrics['browsable_archive_paths']

            # Build data point
            if daily_agg['total_paths'] > 0 or len(pipelines_to_include) > 0:
                data_points.append(DisplayGraphTrendPoint(
                    date=datetime.strptime(date_key, '%Y-%m-%d').date(),
                    total_paths=daily_agg['total_paths'],
                    valid_paths=daily_agg['valid_paths'],
                    black_box_archive_paths=daily_agg['black_box_archive_paths'],
                    browsable_archive_paths=daily_agg['browsable_archive_paths']
                ))
            else:
                # No data for this date (no results and no seeds)
                data_points.append(DisplayGraphTrendPoint(
                    date=datetime.strptime(date_key, '%Y-%m-%d').date(),
                    total_paths=None,
                    valid_paths=None,
                    black_box_archive_paths=None,
                    browsable_archive_paths=None
                ))

        # Get pipeline names
        pipeline_names = {}
        if pipeline_result_counts:
            pipelines = self.db.query(Pipeline).filter(
                Pipeline.id.in_(pipeline_result_counts.keys())
            ).all()
            pipeline_names = {p.id: p.name for p in pipelines}

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

    def _calculate_stable_periods(
        self,
        team_id: int,
        collection_id: Optional[int],
        base_filter: list
    ) -> "StablePeriodInfo":
        """
        Calculate stable period information (consecutive NO_CHANGE results).

        For each tool, determines:
        - Whether the latest result is a NO_CHANGE copy
        - How many days the current stable period has lasted

        Args:
            team_id: Team ID for tenant isolation
            collection_id: Optional collection ID filter
            base_filter: Pre-constructed filter list

        Returns:
            StablePeriodInfo with stable period data per tool
        """
        from backend.src.schemas.trends import StablePeriodInfo

        def get_stable_info(tool: str) -> tuple:
            """Get stable period info for a specific tool."""
            # Get latest result for this tool
            latest = self.db.query(AnalysisResult).filter(
                and_(*base_filter, AnalysisResult.tool == tool)
            ).order_by(AnalysisResult.completed_at.desc()).first()

            if not latest:
                return (False, 0)

            is_stable = latest.no_change_copy or False

            if not is_stable:
                return (False, 0)

            # Count consecutive NO_CHANGE results going back
            # Get all results for this tool, ordered by date desc
            results = self.db.query(AnalysisResult).filter(
                and_(*base_filter, AnalysisResult.tool == tool)
            ).order_by(AnalysisResult.completed_at.desc()).limit(100).all()

            # Count consecutive NO_CHANGE results
            stable_days = 0
            first_stable_date = None
            for result in results:
                if result.no_change_copy:
                    if first_stable_date is None:
                        first_stable_date = result.completed_at
                else:
                    # Found a non-NO_CHANGE result, stop counting
                    break

            if first_stable_date:
                # Calculate days since first stable result
                # Handle both timezone-aware and naive datetimes
                if first_stable_date.tzinfo is not None:
                    now = datetime.now(first_stable_date.tzinfo)
                else:
                    now = datetime.utcnow()
                delta = now - first_stable_date
                # Ensure non-negative (could be negative if clock skew or future timestamp)
                stable_days = max(0, delta.days)

            return (is_stable, stable_days)

        photostats_stable, photostats_days = get_stable_info("photostats")
        photo_pairing_stable, photo_pairing_days = get_stable_info("photo_pairing")
        pipeline_validation_stable, pipeline_validation_days = get_stable_info("pipeline_validation")

        return StablePeriodInfo(
            photostats_stable=photostats_stable,
            photostats_stable_days=photostats_days,
            photo_pairing_stable=photo_pairing_stable,
            photo_pairing_stable_days=photo_pairing_days,
            pipeline_validation_stable=pipeline_validation_stable,
            pipeline_validation_stable_days=pipeline_validation_days
        )

    def get_trend_summary(
        self,
        team_id: int,
        collection_guid: Optional[str] = None
    ) -> TrendSummaryResponse:
        """
        Get trend summary for dashboard overview.

        Provides quick indicators of trend direction for orphaned files
        and consistency metrics.

        Args:
            team_id: Team ID for tenant isolation
            collection_guid: Optional collection GUID filter (col_xxx format)

        Returns:
            Trend summary with direction indicators and latest timestamps
        """
        # Resolve collection GUID to internal ID if provided
        collection_id: Optional[int] = None
        if collection_guid:
            try:
                collection_uuid = Collection.parse_guid(collection_guid)
                collection = self.db.query(Collection).filter(
                    Collection.uuid == collection_uuid,
                    Collection.team_id == team_id
                ).first()
                if collection:
                    collection_id = collection.id
            except ValueError:
                pass  # Invalid GUID format, treat as no filter

        # Base query filter
        base_filter = [
            AnalysisResult.status.in_([ResultStatus.COMPLETED, ResultStatus.NO_CHANGE]),
            AnalysisResult.team_id == team_id
        ]
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

        # Calculate stable period info (consecutive NO_CHANGE results)
        stable_periods = self._calculate_stable_periods(
            team_id=team_id,
            collection_id=collection_id,
            base_filter=base_filter
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
            ),
            stable_periods=stable_periods
        )
