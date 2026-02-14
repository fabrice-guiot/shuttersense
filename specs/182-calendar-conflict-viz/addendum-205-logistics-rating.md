# Addendum: Improve Logistics Rating Scoring (Issue #205)

**Date:** 2026-02-14
**Parent Feature:** #182 — Calendar Conflict Visualization & Event Picker
**Issue:** #205 — Improve Logistics rating for Events

## Context

The `logistics_ease` scoring dimension currently uses a simplistic binary model: each logistics field (`ticket_required`, `timeoff_required`, `travel_required`) is checked only for True/False/None. A "not required" field earns a proportional share of 100; a "required" field earns 0 regardless of its procurement status. This means an event where the user has purchased tickets, booked travel, and gotten time-off approved scores identically to one where nothing has been done — both score 0 if all three are required.

The new model replaces this with a cumulative bonus system that rewards logistical commitment: once money is spent on tickets or travel is booked, the score should reflect that investment and incentivize attending the event.

## Change: Replace Logistics Ease Formula

### New Scoring Matrix

| Property | Not Required | Initial Status | Intermediate | Final |
|----------|-------------|---------------|-------------|-------|
| **Ticket** | +25 | 0 (`not_purchased`) | +25 (`purchased`) | +50 (`ready`) |
| **PTO** | +25 | 0 (`planned`) | +10 (`booked`) | +25 (`approved`) |
| **Travel** | +25 | 0 (`planned`) | +25 (`booked`) | N/A |

- Intermediate and Final columns are **cumulative milestones** (e.g., ticket `ready` = +25 for purchased + +25 for ready = 50)
- **None/unknown** fields contribute 0 (unchanged from current behavior)
- **Maximum score: 100** = Ticket (50) + PTO (25) + Travel (25)

### Key Behavioral Changes

- **All not required** drops from 100 to **75** (25+25+25). This is intentional.
- **Ticket required + ready** (50) now scores higher than **ticket not required** (25), rewarding investment.
- **All required + fully resolved** achieves the maximum score of **100**, which was previously only achievable when nothing was required.

### Example Scenarios

| Scenario | Score | Breakdown |
|----------|-------|-----------|
| All None (unknown) | 0 | 0+0+0 |
| All not required | 75 | 25+25+25 |
| All required, initial status | 0 | 0+0+0 |
| All required, intermediate | 60 | 25+10+25 |
| All required, final status | 100 | 50+25+25 |
| Ticket ready, rest not required | 100 | 50+25+25 |
| Ticket purchased, PTO booked, travel booked | 60 | 25+10+25 |

## Files Modified

| File | Change |
|------|--------|
| `backend/src/services/conflict_service.py` | Replace `_score_logistics_ease()` with cumulative matrix scoring |
| `backend/src/schemas/conflict.py` | Update `logistics_ease` field description |
| `frontend/src/contracts/api/conflict-api.ts` | Update `logistics_ease` comment |
| `backend/tests/unit/test_conflict_service.py` | Replace 4 logistics tests with 10 new tests; update composite test |
| `backend/tests/integration/test_conflict_endpoints.py` | Fix assertion 100→75 |

## Not Changed

- **Event model** — no new fields or migrations
- **`_score_readiness`** — distinct purpose (binary readiness check), unchanged
- **Frontend display components** — render numeric scores, formula-agnostic
- **Scoring weights config** — same dimension name and weight key
- **Domain labels** — "Logistics" label unchanged
