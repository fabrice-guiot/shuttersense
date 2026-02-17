import { useState } from 'react'
import { X, ArrowRight, Trash2, AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { PipelineNode, PipelineEdge } from '@/contracts/api/pipelines-api'
import { NODE_TYPE_DEFINITIONS } from '@/contracts/api/pipelines-api'
import { cn } from '@/lib/utils'

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

export function PropertyPanel({
  node,
  edge,
  nodes,
  mode,
  onUpdateProperties,
  onUpdateNodeId,
  onDeleteNode,
  onDeleteEdge,
  onClose,
}: PropertyPanelProps) {
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
        {node && (
          <NodeProperties
            node={node}
            mode={mode}
            onUpdateProperties={onUpdateProperties}
            onUpdateNodeId={onUpdateNodeId}
          />
        )}
        {edge && <EdgeProperties edge={edge} nodes={nodes} />}
      </div>

      {/* Delete button (edit mode) */}
      {mode === 'edit' && (
        <div className="px-4 py-3 border-t">
          {node && onDeleteNode && (
            <Button
              variant="destructive"
              size="sm"
              className="w-full"
              onClick={() => onDeleteNode(node.id)}
            >
              <Trash2 className="h-3.5 w-3.5 mr-1.5" />
              Delete Node
            </Button>
          )}
          {edge && onDeleteEdge && (
            <Button
              variant="destructive"
              size="sm"
              className="w-full"
              onClick={() => onDeleteEdge(`${edge.from}-${edge.to}`)}
            >
              <Trash2 className="h-3.5 w-3.5 mr-1.5" />
              Delete Edge
            </Button>
          )}
        </div>
      )}
    </div>
  )
}

function NodeProperties({
  node,
  mode,
  onUpdateProperties,
  onUpdateNodeId,
}: {
  node: PipelineNode
  mode: 'view' | 'edit'
  onUpdateProperties?: (nodeId: string, properties: Record<string, unknown>) => void
  onUpdateNodeId?: (oldId: string, newId: string) => void
}) {
  const typeDef = NODE_TYPE_DEFINITIONS.find((d) => d.type === node.type)
  const [editingId, setEditingId] = useState(node.id)

  const handlePropertyChange = (key: string, value: unknown) => {
    onUpdateProperties?.(node.id, { ...node.properties, [key]: value })
  }

  const handleIdBlur = () => {
    const trimmed = editingId.trim()
    if (trimmed && trimmed !== node.id) {
      onUpdateNodeId?.(node.id, trimmed)
    } else {
      setEditingId(node.id)
    }
  }

  // View mode
  if (mode === 'view') {
    return (
      <>
        <div className="space-y-2">
          <div>
            <span className="text-xs text-muted-foreground">ID</span>
            <p className="font-mono text-sm">{node.id}</p>
          </div>
          {typeof node.properties.name === 'string' && node.properties.name && (
            <div>
              <span className="text-xs text-muted-foreground">Name</span>
              <p className="text-sm">{node.properties.name}</p>
            </div>
          )}
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

        {typeDef && typeDef.properties.length > 0 && (
          <div className="space-y-3 pt-2 border-t">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Properties
            </span>
            {typeDef.properties.map((prop) => {
              const value = node.properties[prop.key]
              if (value === undefined || value === '' || (Array.isArray(value) && value.length === 0)) {
                return null
              }
              return (
                <div key={prop.key}>
                  <span className="text-xs text-muted-foreground">{prop.label}</span>
                  <p className="text-sm font-medium">
                    <PropertyDisplayValue node={node} propKey={prop.key} value={value} propType={prop.type} />
                  </p>
                </div>
              )
            })}
          </div>
        )}
      </>
    )
  }

  // Edit mode
  return (
    <>
      {/* Node ID */}
      <div className="space-y-1">
        <Label className="text-xs">Node ID</Label>
        <Input
          value={editingId}
          onChange={(e) => setEditingId(e.target.value)}
          onBlur={handleIdBlur}
          onKeyDown={(e) => e.key === 'Enter' && handleIdBlur()}
          className="h-8 text-sm font-mono"
        />
      </div>

      {/* Display Name */}
      <div className="space-y-1">
        <Label className="text-xs">Display Name</Label>
        <Input
          value={typeof node.properties.name === 'string' ? node.properties.name : ''}
          onChange={(e) => handlePropertyChange('name', e.target.value || undefined)}
          placeholder={node.id}
          className="h-8 text-sm"
        />
        <p className="text-[11px] text-muted-foreground">Optional label shown on graph (uses Node ID if empty)</p>
      </div>

      {/* Type badge */}
      <div>
        <span className="text-xs text-muted-foreground">Type</span>
        <div className="flex items-center gap-2 mt-1">
          <Badge variant="outline">{typeDef?.label || node.type}</Badge>
        </div>
      </div>

      {typeDef && (
        <p className="text-xs text-muted-foreground">{typeDef.description}</p>
      )}

      {/* Editable Properties */}
      {typeDef && typeDef.properties.length > 0 && (
        <div className="space-y-3 pt-2 border-t">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Properties
          </span>
          {typeDef.properties.map((prop) => (
            <div key={prop.key} className="space-y-1">
              {prop.type === 'boolean' ? (
                <div className="flex items-center gap-2 pt-1">
                  <Checkbox
                    id={`prop-${prop.key}`}
                    checked={Boolean(node.properties[prop.key])}
                    onCheckedChange={(checked) => handlePropertyChange(prop.key, checked)}
                  />
                  <Label htmlFor={`prop-${prop.key}`} className="text-xs font-normal">
                    {prop.label}
                  </Label>
                </div>
              ) : (
                <>
                  <div className="flex items-center gap-2">
                    <Label className="text-xs">{prop.label}</Label>
                    {prop.required && (
                      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                        Required
                      </span>
                    )}
                  </div>
                  <PropertyEditor
                    node={node}
                    propKey={prop.key}
                    propType={prop.type}
                    options={prop.options}
                    value={node.properties[prop.key]}
                    onChange={(v) => handlePropertyChange(prop.key, v)}
                  />
                </>
              )}
              {prop.hint && (
                <p className="text-[11px] text-muted-foreground">{prop.hint}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  )
}

function PropertyEditor({
  node,
  propKey,
  propType,
  options,
  value,
  onChange,
}: {
  node: PipelineNode
  propKey: string
  propType: string
  options?: string[]
  value: unknown
  onChange: (value: unknown) => void
}) {
  // Special: camera_id_group on Capture node
  if (node.type === 'capture' && propKey === 'camera_id_group') {
    const sample = String(node.properties.sample_filename || '')
    const pattern = String(node.properties.filename_regex || '')
    const extraction = extractRegexGroups(sample, pattern)

    return (
      <div className="space-y-1.5">
        {extraction.error && (
          <p className="text-[11px] text-destructive flex items-center gap-1">
            <AlertTriangle className="h-3 w-3" />
            {extraction.error}
          </p>
        )}
        <Select
          value={String(value || '')}
          onValueChange={onChange}
          disabled={!extraction.isValid}
        >
          <SelectTrigger className={cn('h-8 text-sm', !extraction.isValid && 'opacity-50')}>
            <SelectValue placeholder={extraction.isValid ? 'Select Camera ID group...' : 'Fix pattern first...'} />
          </SelectTrigger>
          <SelectContent>
            {extraction.isValid ? (
              <>
                <SelectItem value="1">
                  <span className="font-mono">{extraction.group1}</span>
                  <span className="text-muted-foreground ml-2">(Group 1)</span>
                </SelectItem>
                <SelectItem value="2">
                  <span className="font-mono">{extraction.group2}</span>
                  <span className="text-muted-foreground ml-2">(Group 2)</span>
                </SelectItem>
              </>
            ) : (
              <>
                <SelectItem value="1" disabled>1</SelectItem>
                <SelectItem value="2" disabled>2</SelectItem>
              </>
            )}
          </SelectContent>
        </Select>
      </div>
    )
  }

  if (propType === 'select' && options) {
    return (
      <Select value={String(value || '')} onValueChange={onChange}>
        <SelectTrigger className="h-8 text-sm">
          <SelectValue placeholder="Select..." />
        </SelectTrigger>
        <SelectContent>
          {options.map((opt) => (
            <SelectItem key={opt} value={opt}>{opt}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    )
  }

  if (propType === 'array') {
    return (
      <Input
        value={Array.isArray(value) ? (value as string[]).join(', ') : String(value || '')}
        onChange={(e) => onChange(e.target.value)}
        onBlur={(e) => onChange(e.target.value.split(',').map((s) => s.trim()).filter(Boolean))}
        placeholder="Comma-separated values"
        className="h-8 text-sm"
      />
    )
  }

  return (
    <Input
      type={propType === 'number' ? 'number' : 'text'}
      value={String(value || '')}
      onChange={(e) => onChange(propType === 'number' ? Number(e.target.value) : e.target.value)}
      className="h-8 text-sm"
    />
  )
}

function PropertyDisplayValue({
  node,
  propKey,
  value,
  propType,
}: {
  node: PipelineNode
  propKey: string
  value: unknown
  propType: string
}) {
  if (node.type === 'capture' && propKey === 'camera_id_group') {
    const sample = String(node.properties.sample_filename || '')
    const pattern = String(node.properties.filename_regex || '')
    const extraction = extractRegexGroups(sample, pattern)
    const groupNum = String(value)
    const extracted = groupNum === '1' ? extraction.group1 : extraction.group2
    if (extraction.isValid && extracted) {
      return (
        <>
          <span className="font-mono">{extracted}</span>
          <span className="text-muted-foreground ml-1">(Group {groupNum})</span>
        </>
      )
    }
    return <>Group {groupNum}</>
  }

  if (propType === 'boolean') return <>{value ? 'Yes' : 'No'}</>
  if (Array.isArray(value)) return <>{value.join(', ')}</>
  return <>{String(value ?? '')}</>
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
