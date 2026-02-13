/**
 * Conflict Detection & Event Scoring API Contracts
 *
 * Defines TypeScript interfaces for conflict detection, event scoring,
 * conflict resolution, and related configuration endpoints.
 * Issue #182 - Calendar Conflict Visualization & Event Picker
 */

// ============================================================================
// Enums
// ============================================================================

export type ConflictType = 'time_overlap' | 'distance' | 'travel_buffer'
export type ConflictGroupStatus = 'unresolved' | 'partially_resolved' | 'resolved'

// ============================================================================
// Scoring
// ============================================================================

export interface EventScores {
  venue_quality: number        // 0–100: Location rating * 20 (null → 50)
  organizer_reputation: number // 0–100: Organizer rating * 20 (null → 50)
  performer_lineup: number     // 0–100: Confirmed performers / ceiling * 100
  logistics_ease: number       // 0–100: Each not-required item → +33.3
  readiness: number            // 0–100: Each resolved required item → proportional share
  composite: number            // 0–100: Weighted average of all dimensions
}

export interface EventScoreResponse {
  guid: string                 // Event GUID (evt_xxx)
  title: string
  event_date: string           // ISO date (YYYY-MM-DD)
  scores: EventScores
}

// ============================================================================
// Conflict Groups
// ============================================================================

export interface CategoryInfo {
  guid: string
  name: string
  icon: string | null
  color: string | null
}

export interface LocationInfo {
  guid: string
  name: string
  city: string | null
  country: string | null
}

export interface OrganizerInfo {
  guid: string
  name: string
}

export interface ScoredEvent {
  guid: string
  title: string
  event_date: string           // ISO date (YYYY-MM-DD)
  start_time: string | null    // HH:MM or HH:MM:SS (24-hour)
  end_time: string | null      // HH:MM or HH:MM:SS (24-hour)
  is_all_day: boolean
  category: CategoryInfo | null
  location: LocationInfo | null
  organizer: OrganizerInfo | null
  performer_count: number
  travel_required: boolean | null
  attendance: string           // 'planned' | 'attended' | 'skipped'
  scores: EventScores
}

export interface ConflictEdge {
  event_a_guid: string
  event_b_guid: string
  conflict_type: ConflictType
  detail: string               // Human-readable conflict description
}

export interface ConflictGroup {
  group_id: string             // Ephemeral identifier (e.g., cg_1)
  status: ConflictGroupStatus
  events: ScoredEvent[]
  edges: ConflictEdge[]
}

export interface ConflictSummary {
  total_groups: number
  unresolved: number
  partially_resolved: number
  resolved: number
}

export interface ConflictDetectionResponse {
  conflict_groups: ConflictGroup[]
  scored_events: ScoredEvent[]
  summary: ConflictSummary
}

// ============================================================================
// Conflict Resolution
// ============================================================================

export interface ConflictDecision {
  event_guid: string
  attendance: 'planned' | 'skipped'
}

export interface ConflictResolveRequest {
  group_id: string             // Ephemeral group identifier (for tracking)
  decisions: ConflictDecision[]
}

export interface ConflictResolveResponse {
  success: boolean
  updated_count: number
  message?: string
}

// ============================================================================
// Configuration — Conflict Rules
// ============================================================================

export interface ConflictRulesResponse {
  distance_threshold_miles: number
  consecutive_window_days: number
  travel_buffer_days: number
  colocation_radius_miles: number
  performer_ceiling: number
}

export interface ConflictRulesUpdateRequest {
  distance_threshold_miles?: number
  consecutive_window_days?: number
  travel_buffer_days?: number
  colocation_radius_miles?: number
  performer_ceiling?: number
}

// ============================================================================
// Configuration — Scoring Weights
// ============================================================================

export interface ScoringWeightsResponse {
  weight_venue_quality: number
  weight_organizer_reputation: number
  weight_performer_lineup: number
  weight_logistics_ease: number
  weight_readiness: number
}

export interface ScoringWeightsUpdateRequest {
  weight_venue_quality?: number
  weight_organizer_reputation?: number
  weight_performer_lineup?: number
  weight_logistics_ease?: number
  weight_readiness?: number
}
