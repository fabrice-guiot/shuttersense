import React from 'react'
import { X, ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import type { PipelineNode, PipelineEdge } from '@/contracts/api/pipelines-api'
import { NODE_TYPE_DEFINITIONS } from '@/contracts/api/pipelines-api'

interface RegexExtractionResult {
  isValid: boolean
  group1: string | null
  group2: string | null
  groupCount: number
  error: string | null
}

function extractRegexGroups(sample: string, pattern: string): RegexExtractionResult {
  if (!sample || !pattern) {
    return { isValid: false, group1: null, group2: null, groupCount: 0, error: null }
  }
  try {
    const regex = new RegExp(pattern)
    const groupMatches = pattern.match(/\((?!\?)/g)
    const groupCount = groupMatches ? groupMatches.length : 0
    if (groupCount !== 2) {
      return { isValid: false, group1: null, group2: null, groupCount, error: `Need 2 capture groups (found ${groupCount})` }
    }
    const match = regex.exec(sample)
    if (!match) {
      return { isValid: false, group1: null, group2: null, groupCount, error: 'No match' }
    }
    return { isValid: true, group1: match[1] || null, group2: match[2] || null, groupCount, error: null }
  } catch {
    return { isValid: false, group1: null, group2: null, groupCount: 0, error: 'Invalid regex' }
  }
}

interface PropertyPanelProps {
  node: PipelineNode | null
  edge: PipelineEdge | null
  nodes?: PipelineNode[]
  mode: 'view' | 'edit'
  onUpdateProperties?: (nodeId: string, properties: Record<string, unknown>) => void
  onUpdateNodeId?: (oldId: string, newId: string) => void
  onDeleteNode?: (nodeId: string) => void
  onDeleteEdge?: (edgeId: string) => void
  onClose: () => void
}

export function PropertyPanel({ node, edge, nodes, mode, onClose }: PropertyPanelProps) {
  if (!node && !edge) return null

  return (
    <div className="w-80 border-l bg-card flex flex-col h-full" data-testid="property-panel">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <h3 className="text-sm font-semibold">
          {node ? 'Node Properties' : 'Edge Info'}
        </h3>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {node && <NodeProperties node={node} mode={mode} />}
        {edge && <EdgeProperties edge={edge} nodes={nodes} />}
      </div>
    </div>
  )
}

function NodeProperties({ node, mode }: { node: PipelineNode; mode: 'view' | 'edit' }) {
  const typeDef = NODE_TYPE_DEFINITIONS.find((d) => d.type === node.type)

  return (
    <>
      {/* ID and Type */}
      <div className="space-y-2">
        <div>
          <span className="text-xs text-muted-foreground">ID</span>
          <p className="font-mono text-sm">{node.id}</p>
        </div>
        <div>
          <span className="text-xs text-muted-foreground">Type</span>
          <div className="flex items-center gap-2">
            <Badge variant="outline">{typeDef?.label || node.type}</Badge>
          </div>
        </div>
        {typeDef && (
          <p className="text-xs text-muted-foreground">{typeDef.description}</p>
        )}
      </div>

      {/* Properties */}
      {typeDef && typeDef.properties.length > 0 && (
        <div className="space-y-3 pt-2 border-t">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Properties
          </span>
          {typeDef.properties.map((prop) => {
            const value = node.properties[prop.key]
            if (mode === 'view' && (value === undefined || value === '' || (Array.isArray(value) && value.length === 0))) {
              return null
            }

            let displayValue: React.ReactNode
            if (node.type === 'capture' && prop.key === 'camera_id_group') {
              const sample = String(node.properties.sample_filename || '')
              const pattern = String(node.properties.filename_regex || '')
              const extraction = extractRegexGroups(sample, pattern)
              const groupNum = String(value)
              const extracted = groupNum === '1' ? extraction.group1 : extraction.group2
              displayValue = extraction.isValid && extracted ? (
                <span>
                  <span className="font-mono">{extracted}</span>
                  <span className="text-muted-foreground ml-1">(Group {groupNum})</span>
                </span>
              ) : (
                <span>Group {groupNum}</span>
              )
            } else if (prop.type === 'boolean') {
              displayValue = value ? 'Yes' : 'No'
            } else if (Array.isArray(value)) {
              displayValue = value.join(', ')
            } else {
              displayValue = String(value ?? '')
            }

            return (
              <div key={prop.key}>
                <span className="text-xs text-muted-foreground">{prop.label}</span>
                <p className="text-sm font-medium">{displayValue}</p>
              </div>
            )
          })}
        </div>
      )}
    </>
  )
}

function EdgeProperties({ edge, nodes }: { edge: PipelineEdge; nodes?: PipelineNode[] }) {
  const fromNode = nodes?.find((n) => n.id === edge.from)
  const toNode = nodes?.find((n) => n.id === edge.to)
  const fromTypeDef = fromNode ? NODE_TYPE_DEFINITIONS.find((d) => d.type === fromNode.type) : null
  const toTypeDef = toNode ? NODE_TYPE_DEFINITIONS.find((d) => d.type === toNode.type) : null

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <div className="text-center">
          <span className="font-mono text-sm">{edge.from}</span>
          {fromTypeDef && (
            <Badge variant="outline" className="ml-1 text-xs">{fromTypeDef.label}</Badge>
          )}
        </div>
        <ArrowRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
        <div className="text-center">
          <span className="font-mono text-sm">{edge.to}</span>
          {toTypeDef && (
            <Badge variant="outline" className="ml-1 text-xs">{toTypeDef.label}</Badge>
          )}
        </div>
      </div>
    </div>
  )
}

export default PropertyPanel
