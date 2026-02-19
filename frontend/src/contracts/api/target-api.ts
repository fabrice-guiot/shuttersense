/**
 * Target API Contracts (Issue #110)
 *
 * Shared TypeScript types for the polymorphic target pattern
 * used by Job and AnalysisResult entities.
 */

export type TargetEntityType = 'collection' | 'connector' | 'pipeline' | 'camera'

export interface TargetEntityInfo {
  entity_type: TargetEntityType
  entity_guid: string
  entity_name: string | null
}

export interface ContextEntityRef {
  guid: string
  name: string | null
}

export interface PipelineContextRef extends ContextEntityRef {
  version: number | null
}

export interface ResultContext {
  pipeline?: PipelineContextRef | null
  connector?: ContextEntityRef | null
}
