import type { EdgeTypes } from '@xyflow/react'
import PipelineEdge from './PipelineEdge'
import AnalyticsEdge from './AnalyticsEdge'

export { PipelineEdge, AnalyticsEdge }

export const edgeTypes: EdgeTypes = {
  pipelineEdge: PipelineEdge,
  analyticsEdge: AnalyticsEdge,
}
