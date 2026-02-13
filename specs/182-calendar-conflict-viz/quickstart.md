# Quickstart: Calendar Conflict Visualization & Event Picker

**Feature Branch**: `182-calendar-conflict-viz`
**Created**: 2026-02-13

## Prerequisites

- Python 3.11+ with virtual environment (`venv/`)
- PostgreSQL running (or SQLite for tests)
- Node.js 18+ for frontend
- Existing ShutterSense backend and frontend running

## Implementation Order (Phased)

### Phase 1: Foundation — Backend Services & Settings

**Goal**: Conflict detection, scoring, and settings — no UI changes yet.

1. **`backend/src/services/geo_utils.py`** — Haversine distance function
   - Pure Python, no dependencies
   - Input: two (lat, lon) pairs → output: distance in miles

2. **`backend/src/services/conflict_service.py`** — Core service
   - `ConflictService(db: Session)`
   - Methods: `detect_conflicts()`, `score_event()`, `get_conflict_rules()`, `get_scoring_weights()`
   - Depends on: `EventService.list()`, `geo_utils.haversine_miles()`, `ConfigService`

3. **`backend/src/schemas/conflict.py`** — Pydantic schemas
   - Request/response schemas matching `contracts/conflict-api.yaml`

4. **`backend/src/services/seed_data_service.py`** — Extend seeding
   - Add `seed_conflict_rules(team_id, user_id)` and `seed_scoring_weights(team_id, user_id)`
   - Update `seed_team_defaults()` to call both new methods

5. **`backend/src/services/config_service.py`** — Register categories
   - Add `"conflict_rules"` and `"scoring_weights"` to `VALID_CATEGORIES`

6. **`backend/src/api/events.py`** — New endpoints
   - `GET /events/conflicts` — Conflict detection
   - `GET /events/{guid}/score` — Event scoring
   - IMPORTANT: Register these before `/{guid}` catch-all route

7. **`backend/src/api/config.py`** — Config endpoints
   - `GET /config/conflict_rules` and `PUT /config/conflict_rules`
   - `GET /config/scoring_weights` and `PUT /config/scoring_weights`
   - IMPORTANT: Register before `/{category}` catch-all route

8. **Alembic migration** — Seed defaults for existing teams
   - Follow migration `050` pattern (iterate teams, insert if missing)

9. **Tests**: `test_geo_utils.py`, `test_conflict_service.py`, `test_seed_conflict.py`

**Settings UI** (frontend, Phase 1):
- `ConflictRulesSection.tsx` — Numeric inputs for 5 conflict rules
- `ScoringWeightsSection.tsx` — Numeric inputs with proportional bars for 5 weights
- Add both sections to SettingsPage Configuration tab

### Phase 2: Calendar Indicators & Resolution

**Goal**: Conflict badges on calendar + resolution panel in day detail.

1. **`frontend/src/contracts/api/conflict-api.ts`** — TypeScript types
2. **`frontend/src/services/conflicts.ts`** — API client functions
3. **`frontend/src/hooks/useConflicts.ts`** — Fetch conflicts for visible date range
4. **`frontend/src/hooks/useResolveConflict.ts`** — Mutation hook
5. **`frontend/src/components/events/ConflictBadge.tsx`** — Amber badge component
6. **`frontend/src/components/events/ConflictResolutionPanel.tsx`** — Conflict group cards
7. **Modify `EventCalendar.tsx`** — Add conflict indicators to calendar cells
8. **Modify `EventCard.tsx`** — Add conflict badge to event cards
9. **Modify `EventsPage.tsx`** — Add Conflicts tab to day detail dialog
10. **`backend/src/api/events.py`** — `POST /events/conflicts/resolve` endpoint

### Phase 3: Radar Chart Comparison

**Goal**: Multi-dimensional event comparison via radar charts.

1. **`frontend/src/hooks/useEventScore.ts`** — Fetch scores for single event
2. **`frontend/src/components/events/EventRadarChart.tsx`** — Recharts RadarChart wrapper
3. **`frontend/src/components/events/RadarComparisonDialog.tsx`** — Overlaid radar + breakdown table
4. **Integrate** "Compare" button in ConflictResolutionPanel

### Phase 4: Unified Date Range Picker

**Goal**: Shared date range picker for all non-calendar list views + infinite scroll.

1. **`frontend/src/hooks/useDateRange.ts`** — Date range state management + URL sync
2. **`frontend/src/components/events/DateRangePicker.tsx`** — Shared picker component
   - Rolling presets: Next 30 / 60 / 90 days
   - Calendar-month presets: Next 1 / 2 / 3 / 6 months (1st-through-end-of-month)
   - Custom range: user picks start/end dates
   - No "All" option
3. **Modify `EventsPage.tsx`** — Wire DateRangePicker into all preset list views
4. **Modify `useEvents()` hook** — Accept start_date/end_date params from date range picker
5. **Add infinite scroll** to EventList component (replaces unbounded list rendering)

### Phase 5: Timeline Planner

**Goal**: Scrollable timeline view with score visualization.

1. **`frontend/src/components/events/DimensionMicroBar.tsx`** — Linearized radar segments
2. **`frontend/src/components/events/TimelineEventMarker.tsx`** — Event row with score bar
3. **`frontend/src/components/events/TimelinePlanner.tsx`** — Full timeline with filters
4. **Modify `EventsPage.tsx`** — Add Planner view mode (uses DateRangePicker from Phase 4)

### Phase 6: KPI & Polish

**Goal**: Header stats, notifications, accessibility.

1. **Update KPI stats** for Planner view via `useHeaderStats()`
2. **Notification trigger** on conflict creation (backend event hook)
3. **Keyboard navigation** for timeline
4. **Virtual scrolling** for large timelines (if needed)

## Key Patterns to Follow

### Backend Service Pattern
```python
# Follow EventService pattern
class ConflictService:
    def __init__(self, db: Session):
        self.db = db
        self.event_service = EventService(db)
        self.config_service = ConfigService(db)
```

### Frontend Hook Pattern
```typescript
// Follow useEvents() pattern
export function useConflicts(startDate: string, endDate: string) {
  const [data, setData] = useState<ConflictDetectionResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // ...
}
```

### Config Category Pattern
```python
# In config_service.py — add to VALID_CATEGORIES
VALID_CATEGORIES = {
    "extensions", "cameras", "processing_methods",
    "event_statuses", "collection_ttl",
    "conflict_rules", "scoring_weights",  # NEW
}
```

### Seeding Pattern
```python
# In seed_data_service.py — follow seed_collection_ttl() pattern
def seed_conflict_rules(self, team_id: int, user_id: Optional[int] = None) -> int:
    created_count = 0
    for key, data in DEFAULT_CONFLICT_RULES.items():
        existing = self.db.query(Configuration).filter(
            Configuration.team_id == team_id,
            Configuration.category == "conflict_rules",
            Configuration.key == key,
        ).first()
        if existing:
            continue
        config = Configuration(
            team_id=team_id, category="conflict_rules", key=key,
            value_json=data, source=ConfigSource.DATABASE,
            created_by_user_id=user_id, updated_by_user_id=user_id,
        )
        self.db.add(config)
        created_count += 1
    return created_count  # Does NOT commit
```

## Testing

```bash
# Run all conflict-related backend unit tests
venv/bin/python -m pytest backend/tests/unit/test_conflict_service.py -v
venv/bin/python -m pytest backend/tests/unit/test_geo_utils.py -v
venv/bin/python -m pytest backend/tests/unit/test_seed_conflict.py -v

# Run all conflict-related backend integration tests
venv/bin/python -m pytest backend/tests/integration/test_conflict_endpoints.py -v
venv/bin/python -m pytest backend/tests/integration/test_conflict_config_api.py -v

# Frontend type checking
cd frontend && npx tsc --noEmit

# Frontend component tests
cd frontend && npx vitest run --reporter=verbose
```

## Gotchas

1. **Route ordering in FastAPI**: `/events/conflicts` MUST be registered before `/events/{guid}` — FastAPI matches routes in order, and `{guid}` is a catch-all.
2. **Config category validation**: The `VALID_CATEGORIES` set in `config_service.py` must include the new categories, otherwise `create()` will reject them.
3. **Seeding commits**: `seed_conflict_rules()` and `seed_scoring_weights()` must NOT commit — `seed_team_defaults()` commits once at the end.
4. **Nullable logistics fields**: `travel_required`, `ticket_required`, `timeoff_required` are nullable booleans. Treat `None` as "not required" for scoring purposes.
5. **Soft-deleted events**: Exclude soft-deleted events (`deleted_at IS NOT NULL`) from conflict detection. `EventService.list()` already handles this via `include_deleted=False`.
6. **Deadline entries**: Exclude events where `is_deadline=True` from conflict detection — these are synthetic entries for workflow tracking.
