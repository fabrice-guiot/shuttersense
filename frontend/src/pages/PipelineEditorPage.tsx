/**
 * PipelineEditorPage component
 *
 * View and edit photo processing pipelines
 * - View mode: /pipelines/:id (read-only)
 * - Edit mode: /pipelines/:id/edit or /pipelines/new
 */

import React, { useEffect, useState, useCallback } from 'react'
import { useNavigate, useParams, useLocation } from 'react-router-dom'
import {
  GitBranch,
  Plus,
  Trash2,
  Save,
  ArrowLeft,
  AlertTriangle,
  Beaker,
  Pencil,
  CheckCircle,
  XCircle,
  Zap,
  ArrowRight,
  Lock,
  Download,
  History,
} from 'lucide-react'
import { MainLayout } from '@/components/layout/MainLayout'
import { usePipeline, usePipelines, usePipelineExport } from '@/hooks/usePipelines'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type {
  PipelineNode,
  PipelineEdge,
  NodeType,
  PipelineCreateRequest,
  PipelineUpdateRequest,
  ValidationResult,
} from '@/contracts/api/pipelines-api'
import { NODE_TYPE_DEFINITIONS } from '@/contracts/api/pipelines-api'
import { cn } from '@/lib/utils'

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Result of extracting regex groups from a sample filename.
 */
interface RegexExtractionResult {
  isValid: boolean
  group1: string | null
  group2: string | null
  groupCount: number
  error: string | null
}

/**
 * Extracts capture groups from a sample filename using a regex pattern.
 * Used to dynamically populate the Camera ID Group dropdown.
 *
 * @param sample - The sample filename (e.g., "AB3D0001")
 * @param pattern - The regex pattern with capture groups (e.g., "([A-Z0-9]{4})([0-9]{4})")
 * @returns Extraction result with group values or error information
 */
function extractRegexGroups(sample: string, pattern: string): RegexExtractionResult {
  // Handle empty inputs
  if (!sample || !pattern) {
    return {
      isValid: false,
      group1: null,
      group2: null,
      groupCount: 0,
      error: !sample ? 'Sample filename is required' : 'Filename pattern is required',
    }
  }

  try {
    const regex = new RegExp(pattern)

    // Count capture groups by checking the regex source
    // This counts opening parentheses that are not non-capturing (?:) or lookbehind/lookahead
    const groupMatches = pattern.match(/\((?!\?)/g)
    const groupCount = groupMatches ? groupMatches.length : 0

    if (groupCount !== 2) {
      return {
        isValid: false,
        group1: null,
        group2: null,
        groupCount,
        error: `Pattern must have exactly 2 capture groups (found ${groupCount})`,
      }
    }

    // Try to match the sample
    const match = regex.exec(sample)
    if (!match) {
      return {
        isValid: false,
        group1: null,
        group2: null,
        groupCount,
        error: 'Sample filename does not match the pattern',
      }
    }

    // Extract groups (match[0] is full match, match[1] and match[2] are groups)
    return {
      isValid: true,
      group1: match[1] || null,
      group2: match[2] || null,
      groupCount,
      error: null,
    }
  } catch (e) {
    return {
      isValid: false,
      group1: null,
      group2: null,
      groupCount: 0,
      error: `Invalid regex pattern: ${e instanceof Error ? e.message : 'Unknown error'}`,
    }
  }
}

// ============================================================================
// Node Viewer Component (Read-only)
// ============================================================================

interface NodeViewerProps {
  node: PipelineNode
  index: number
}

const NodeViewer: React.FC<NodeViewerProps> = ({ node, index }) => {
  const nodeTypeDef = NODE_TYPE_DEFINITIONS.find((d) => d.type === node.type)

  return (
    <Card>
      <CardContent className="pt-4">
        <div className="flex items-center gap-3 mb-3">
          <span className="text-sm font-medium text-muted-foreground">#{index + 1}</span>
          <Badge variant="outline">{nodeTypeDef?.label || node.type}</Badge>
          <span className="font-mono text-sm text-foreground">{node.id}</span>
          {node.properties.name && (
            <span className="text-sm text-muted-foreground">({String(node.properties.name)})</span>
          )}
        </div>

        {nodeTypeDef && (
          <p className="text-xs text-muted-foreground mb-3">{nodeTypeDef.description}</p>
        )}

        {/* Properties */}
        <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          {nodeTypeDef?.properties.filter((p) => p.key !== 'name').map((prop) => {
            const value = node.properties[prop.key]
            if (value === undefined || value === '' || (Array.isArray(value) && value.length === 0)) {
              return null
            }

            // Special display for camera_id_group in Capture nodes
            let displayValue: React.ReactNode
            if (node.type === 'capture' && prop.key === 'camera_id_group') {
              const sample = String(node.properties.sample_filename || '')
              const pattern = String(node.properties.filename_regex || '')
              const extraction = extractRegexGroups(sample, pattern)
              const groupNum = String(value)
              const extractedValue = groupNum === '1' ? extraction.group1 : extraction.group2

              displayValue = extraction.isValid && extractedValue ? (
                <span>
                  <span className="font-mono">{extractedValue}</span>
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
              displayValue = String(value)
            }

            return (
              <React.Fragment key={prop.key}>
                <div className="text-muted-foreground">{prop.label}:</div>
                <div className="font-medium">{displayValue}</div>
              </React.Fragment>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}

// ============================================================================
// Edge Viewer Component (Read-only)
// ============================================================================

interface EdgeViewerProps {
  edge: PipelineEdge
  index: number
}

const EdgeViewer: React.FC<EdgeViewerProps> = ({ edge, index }) => {
  return (
    <div className="flex items-center gap-3 py-2 px-3 bg-muted/50 rounded-md">
      <span className="text-xs text-muted-foreground">#{index + 1}</span>
      <span className="font-mono text-sm">{edge.from}</span>
      <ArrowRight className="h-4 w-4 text-muted-foreground" />
      <span className="font-mono text-sm">{edge.to}</span>
    </div>
  )
}

// ============================================================================
// Node Editor Component (Editable)
// ============================================================================

interface NodeEditorProps {
  node: PipelineNode
  index: number
  allNodes: PipelineNode[]
  availableTypes: NodeType[]
  isTypeLocked: boolean
  onChange: (index: number, node: PipelineNode) => void
  onDelete: (index: number) => void
  onTypeLock: (index: number) => void
}

const NodeEditor: React.FC<NodeEditorProps> = ({
  node,
  index,
  availableTypes,
  isTypeLocked,
  onChange,
  onDelete,
  onTypeLock,
}) => {
  const nodeTypeDef = NODE_TYPE_DEFINITIONS.find((d) => d.type === node.type)
  // Check if type is a valid node type (not empty string or undefined)
  const hasTypeSelected = Boolean(node.type) && NODE_TYPE_DEFINITIONS.some((d) => d.type === node.type)

  const handlePropertyChange = (key: string, value: unknown) => {
    onChange(index, {
      ...node,
      properties: { ...node.properties, [key]: value },
    })
  }

  const handleIdChange = (newId: string) => {
    onChange(index, { ...node, id: newId })
  }

  const handleTypeChange = (newType: NodeType) => {
    const newDef = NODE_TYPE_DEFINITIONS.find((d) => d.type === newType)
    const defaultProps: Record<string, unknown> = {}
    newDef?.properties.forEach((prop) => {
      if (prop.default !== undefined) {
        defaultProps[prop.key] = prop.default
      } else if (prop.type === 'boolean') {
        defaultProps[prop.key] = false
      } else if (prop.type === 'array') {
        defaultProps[prop.key] = []
      } else {
        defaultProps[prop.key] = ''
      }
    })
    onChange(index, { ...node, type: newType, properties: defaultProps })
    // Lock the type after selection
    onTypeLock(index)
  }

  const handleNameChange = (newName: string) => {
    onChange(index, {
      ...node,
      properties: { ...node.properties, name: newName },
    })
  }

  return (
    <Card>
      <CardContent className="pt-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-muted-foreground">#{index + 1}</span>
            {isTypeLocked && hasTypeSelected ? (
              // Locked: show badge instead of dropdown
              <Badge variant="outline" className="text-sm font-medium">
                {nodeTypeDef?.label || node.type}
              </Badge>
            ) : (
              // Unlocked: show dropdown for type selection
              <Select
                value={node.type || ''}
                onValueChange={(v) => handleTypeChange(v as NodeType)}
              >
                <SelectTrigger className="w-36">
                  <SelectValue placeholder="Select type..." />
                </SelectTrigger>
                <SelectContent>
                  {availableTypes.map((type) => {
                    const def = NODE_TYPE_DEFINITIONS.find((d) => d.type === type)
                    return (
                      <SelectItem key={type} value={type}>
                        {def?.label || type}
                      </SelectItem>
                    )
                  })}
                </SelectContent>
              </Select>
            )}
            {isTypeLocked && hasTypeSelected && (
              <Lock className="h-3 w-3 text-muted-foreground" />
            )}
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onDelete(index)}
            className="text-destructive hover:text-destructive hover:bg-destructive/10"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>

        {/* Show prompt to select type if not selected */}
        {!hasTypeSelected && (
          <div className="py-4 text-center text-muted-foreground">
            <p className="text-sm">Select a node type to configure its properties.</p>
          </div>
        )}

        {/* Only show properties after type is selected */}
        {hasTypeSelected && (
          <>
            {nodeTypeDef && (
              <p className="text-xs text-muted-foreground mb-3">{nodeTypeDef.description}</p>
            )}

            {/* Common node properties: ID and Name */}
            <div className="grid grid-cols-2 gap-3 mb-3 pb-3 border-b">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Label className="text-xs">ID</Label>
                  <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-destructive/15 text-destructive">
                    Required
                  </span>
                </div>
                <Input
                  value={node.id}
                  onChange={(e) => handleIdChange(e.target.value)}
                  placeholder="e.g., raw_file"
                  className="h-8 text-sm font-mono"
                />
                <p className="text-[11px] text-muted-foreground">
                  Technical identifier used in edges. Example: capture, raw_file, done
                </p>
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Label className="text-xs">Name</Label>
                  <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                    Optional
                  </span>
                </div>
                <Input
                  value={String(node.properties.name || '')}
                  onChange={(e) => handleNameChange(e.target.value)}
                  placeholder="e.g., RAW File"
                  className="h-8 text-sm"
                />
                <p className="text-[11px] text-muted-foreground">
                  Human-friendly label for display. Example: "Camera Capture", "RAW File"
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              {/* Filter out 'name' since it's shown as a common property above */}
              {nodeTypeDef?.properties.filter((p) => p.key !== 'name').map((prop) => (
            <div key={prop.key} className="space-y-1">
              {prop.type === 'boolean' ? (
                /* Checkboxes don't need Required/Optional badges - they're inherently optional */
                <>
                  <div className="flex items-center gap-2 pt-1">
                    <Checkbox
                      id={`${node.id}-${prop.key}`}
                      checked={Boolean(node.properties[prop.key])}
                      onCheckedChange={(checked) => handlePropertyChange(prop.key, checked)}
                    />
                    <Label htmlFor={`${node.id}-${prop.key}`} className="text-xs font-normal">
                      {prop.label}
                    </Label>
                  </div>
                  {prop.hint && (
                    <p className="text-[11px] text-muted-foreground">{prop.hint}</p>
                  )}
                </>
              ) : (
                /* Non-boolean fields show label with Required/Optional badge */
                <>
                  <div className="flex items-center gap-2">
                    <Label className="text-xs">{prop.label}</Label>
                    {prop.required ? (
                      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-destructive/15 text-destructive">
                        Required
                      </span>
                    ) : (
                      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                        Optional
                      </span>
                    )}
                  </div>
                  {prop.type === 'select' ? (
                    (() => {
                      // Special handling for camera_id_group in Capture nodes
                      if (node.type === 'capture' && prop.key === 'camera_id_group') {
                        const sample = String(node.properties.sample_filename || '')
                        const pattern = String(node.properties.filename_regex || '')
                        const extraction = extractRegexGroups(sample, pattern)

                        return (
                          <div className="space-y-2">
                            {extraction.error && (
                              <p className="text-[11px] text-destructive flex items-center gap-1">
                                <AlertTriangle className="h-3 w-3" />
                                {extraction.error}
                              </p>
                            )}
                            <Select
                              value={String(node.properties[prop.key] || '')}
                              onValueChange={(v) => handlePropertyChange(prop.key, v)}
                              disabled={!extraction.isValid}
                            >
                              <SelectTrigger className={cn(
                                "h-8 text-sm",
                                !extraction.isValid && "opacity-50"
                              )}>
                                <SelectValue placeholder={extraction.isValid ? "Select Camera ID group..." : "Fix pattern first..."} />
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

                      // Default select rendering for other properties
                      return (
                        <Select
                          value={String(node.properties[prop.key] || '')}
                          onValueChange={(v) => handlePropertyChange(prop.key, v)}
                        >
                          <SelectTrigger className="h-8 text-sm">
                            <SelectValue placeholder="Select..." />
                          </SelectTrigger>
                          <SelectContent>
                            {prop.options?.map((opt) => (
                              <SelectItem key={opt} value={opt}>
                                {opt}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )
                    })()
                  ) : prop.type === 'array' ? (
                    <Input
                      value={Array.isArray(node.properties[prop.key])
                        ? (node.properties[prop.key] as string[]).join(', ')
                        : String(node.properties[prop.key] || '')}
                      onChange={(e) =>
                        handlePropertyChange(
                          prop.key,
                          e.target.value
                        )
                      }
                      onBlur={(e) =>
                        handlePropertyChange(
                          prop.key,
                          e.target.value.split(',').map((s) => s.trim()).filter(Boolean)
                        )
                      }
                      placeholder="Comma-separated values"
                      className="h-8 text-sm"
                    />
                  ) : (
                    <Input
                      type={prop.type === 'number' ? 'number' : 'text'}
                      value={String(node.properties[prop.key] || '')}
                      onChange={(e) =>
                        handlePropertyChange(
                          prop.key,
                          prop.type === 'number' ? Number(e.target.value) : e.target.value
                        )
                      }
                      className="h-8 text-sm"
                    />
                  )}
                  {prop.hint && (
                    <p className="text-[11px] text-muted-foreground">{prop.hint}</p>
                  )}
                </>
              )}
            </div>
          ))}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}

// ============================================================================
// Edge Editor Component (Editable)
// ============================================================================

interface EdgeEditorProps {
  edge: PipelineEdge
  index: number
  nodes: PipelineNode[]
  onChange: (index: number, edge: PipelineEdge) => void
  onDelete: (index: number) => void
}

const EdgeEditor: React.FC<EdgeEditorProps> = ({ edge, index, nodes, onChange, onDelete }) => {
  // Filter nodes for "From" dropdown:
  // - Exclude termination nodes (they can only be destinations)
  const fromNodes = nodes.filter((n) => n.type !== 'termination' && n.id)

  // Filter nodes for "To" dropdown:
  // - Exclude capture nodes (they can only be sources)
  const toNodes = nodes.filter((n) => n.type !== 'capture' && n.id)

  return (
    <div className="flex items-center gap-2 py-2 px-3 bg-muted/50 rounded-md">
      <Select value={edge.from} onValueChange={(v) => onChange(index, { ...edge, from: v })}>
        <SelectTrigger className="flex-1 h-8">
          <SelectValue placeholder="From..." />
        </SelectTrigger>
        <SelectContent>
          {fromNodes.map((node) => (
            <SelectItem key={node.id} value={node.id}>
              <span className="font-mono">{node.id}</span>
              <span className="text-muted-foreground ml-2 text-xs">
                ({NODE_TYPE_DEFINITIONS.find((d) => d.type === node.type)?.label || node.type})
              </span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <span className="text-muted-foreground">→</span>
      <Select value={edge.to} onValueChange={(v) => onChange(index, { ...edge, to: v })}>
        <SelectTrigger className="flex-1 h-8">
          <SelectValue placeholder="To..." />
        </SelectTrigger>
        <SelectContent>
          {toNodes.map((node) => (
            <SelectItem key={node.id} value={node.id}>
              <span className="font-mono">{node.id}</span>
              <span className="text-muted-foreground ml-2 text-xs">
                ({NODE_TYPE_DEFINITIONS.find((d) => d.type === node.type)?.label || node.type})
              </span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Button
        variant="ghost"
        size="icon"
        onClick={() => onDelete(index)}
        className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
      >
        <Trash2 className="h-4 w-4" />
      </Button>
    </div>
  )
}

// ============================================================================
// Main Page Component
// ============================================================================

export const PipelineEditorPage: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { id } = useParams<{ id: string }>()

  // Determine mode from URL
  const isNew = id === 'new'
  const isEditMode = isNew || location.pathname.endsWith('/edit')
  const isViewMode = !isEditMode && id && id !== 'new'
  const pipelineId = !isNew && id ? Number(id) : null

  // Hooks
  const {
    pipeline,
    loading: loadingPipeline,
    currentVersion,
    latestVersion,
    history,
    loadVersion,
  } = usePipeline(pipelineId)
  const { createPipeline, updatePipeline, loading: saving } = usePipelines({ autoFetch: false })
  const { downloadYaml, downloading } = usePipelineExport()

  // Determine if viewing a historical version
  const isHistoricalVersion = currentVersion !== null && latestVersion !== null && currentVersion < latestVersion

  // Form state
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [nodes, setNodes] = useState<PipelineNode[]>([])
  const [edges, setEdges] = useState<PipelineEdge[]>([])
  const [changeSummary, setChangeSummary] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null)

  // Track which node indices have their types locked
  // New nodes start unlocked, loaded pipeline nodes start locked
  const [lockedNodeIndices, setLockedNodeIndices] = useState<Set<number>>(new Set())

  // Load existing pipeline data
  useEffect(() => {
    if (pipeline) {
      setName(pipeline.name)
      setDescription(pipeline.description || '')
      setNodes(pipeline.nodes)
      setEdges(pipeline.edges)
      // Lock all existing nodes when loading a pipeline
      setLockedNodeIndices(new Set(pipeline.nodes.map((_, i) => i)))
    }
  }, [pipeline])

  // Compute available node types for new nodes
  // - Remove 'capture' if one already exists in the pipeline
  const availableNodeTypes = React.useMemo(() => {
    const allTypes: NodeType[] = NODE_TYPE_DEFINITIONS.map((d) => d.type)
    const hasCaptureNode = nodes.some((n) => n.type === 'capture')
    if (hasCaptureNode) {
      return allTypes.filter((t) => t !== 'capture')
    }
    return allTypes
  }, [nodes])

  // Compute validation hints for pipeline requirements
  const validationHints = React.useMemo(() => {
    const hints: string[] = []

    // Only validate nodes that have a type selected
    const typedNodes = nodes.filter(
      (n) => n.type && NODE_TYPE_DEFINITIONS.some((d) => d.type === n.type)
    )

    // Check for Capture node
    const hasCaptureNode = typedNodes.some((n) => n.type === 'capture')
    if (!hasCaptureNode) {
      hints.push('A Capture node is required to define camera patterns.')
    }

    // Check for at least one non-optional File node
    const hasRequiredFileNode = typedNodes.some(
      (n) => n.type === 'file' && !n.properties.optional
    )
    if (!hasRequiredFileNode) {
      hints.push('At least one non-optional File node is required.')
    }

    // Check for Termination node
    const hasTerminationNode = typedNodes.some((n) => n.type === 'termination')
    if (!hasTerminationNode) {
      hints.push('A Termination node is required to define end states.')
    }

    // Check that all nodes with IDs appear in at least one edge
    const validEdges = edges.filter((e) => e.from && e.to)
    const nodesInEdges = new Set<string>()
    validEdges.forEach((e) => {
      nodesInEdges.add(e.from)
      nodesInEdges.add(e.to)
    })

    const orphanedNodes = typedNodes.filter(
      (n) => n.id && !nodesInEdges.has(n.id)
    )
    if (orphanedNodes.length > 0 && typedNodes.length > 1) {
      const orphanedIds = orphanedNodes.map((n) => n.id).join(', ')
      hints.push(`Orphaned nodes not connected by any edge: ${orphanedIds}`)
    }

    // Check that pairing nodes have exactly 2 inputs (edges pointing to them)
    const pairingNodes = typedNodes.filter((n) => n.type === 'pairing')
    pairingNodes.forEach((pairingNode) => {
      const inputCount = validEdges.filter((e) => e.to === pairingNode.id).length
      if (inputCount !== 2) {
        hints.push(`Pairing node "${pairingNode.id}" must have exactly 2 inputs (currently has ${inputCount})`)
      }
    })

    return hints
  }, [nodes, edges])

  // Computed validity based on current editor state
  const isCurrentlyValid = validationHints.length === 0 && nodes.length > 0 &&
    nodes.every((n) => n.type && NODE_TYPE_DEFINITIONS.some((d) => d.type === n.type))

  // Node management
  const handleAddNode = useCallback(() => {
    // Create a new node with empty type - user must select type first
    const newNode: PipelineNode = {
      id: `node_${nodes.length + 1}`,
      type: '' as NodeType, // Empty type - will be selected by user
      properties: {},
    }
    setNodes([...nodes, newNode])
    // New nodes are NOT locked - they stay unlocked until user selects a type
  }, [nodes])

  const handleTypeLock = useCallback((index: number) => {
    setLockedNodeIndices((prev) => new Set([...prev, index]))
  }, [])

  const handleNodeChange = useCallback((index: number, node: PipelineNode) => {
    setNodes((prev) => prev.map((n, i) => (i === index ? node : n)))
  }, [])

  const handleNodeDelete = useCallback((index: number) => {
    const deletedId = nodes[index].id
    setNodes((prev) => prev.filter((_, i) => i !== index))
    setEdges((prev) => prev.filter((e) => e.from !== deletedId && e.to !== deletedId))
    // Recompute locked indices (shift down indices after deleted one)
    setLockedNodeIndices((prev) => {
      const newSet = new Set<number>()
      prev.forEach((i) => {
        if (i < index) {
          newSet.add(i)
        } else if (i > index) {
          newSet.add(i - 1)
        }
        // Skip i === index (the deleted one)
      })
      return newSet
    })
  }, [nodes])

  // Edge management
  const handleAddEdge = useCallback(() => {
    setEdges([...edges, { from: '', to: '' }])
  }, [edges])

  const handleEdgeChange = useCallback((index: number, edge: PipelineEdge) => {
    setEdges((prev) => prev.map((e, i) => (i === index ? edge : e)))
  }, [])

  const handleEdgeDelete = useCallback((index: number) => {
    setEdges((prev) => prev.filter((_, i) => i !== index))
  }, [])

  // Save handler
  const handleSave = async () => {
    setError(null)
    setValidationResult(null)

    if (!name.trim()) {
      setError('Pipeline name is required')
      return
    }

    if (nodes.length === 0) {
      setError('Pipeline must have at least one node')
      return
    }

    // Check for nodes without type selected
    const nodesWithoutType = nodes.filter(
      (n) => !n.type || !NODE_TYPE_DEFINITIONS.some((d) => d.type === n.type)
    )
    if (nodesWithoutType.length > 0) {
      setError(`Please select a type for all nodes. ${nodesWithoutType.length} node(s) have no type selected.`)
      return
    }

    const validEdges = edges.filter((e) => e.from && e.to)

    try {
      if (pipelineId) {
        const updateData: PipelineUpdateRequest = {
          name,
          description: description || undefined,
          nodes,
          edges: validEdges,
          change_summary: changeSummary || undefined,
        }
        await updatePipeline(pipelineId, updateData)
      } else {
        const createData: PipelineCreateRequest = {
          name,
          description: description || undefined,
          nodes,
          edges: validEdges,
        }
        await createPipeline(createData)
      }
      navigate('/pipelines')
    } catch (err: any) {
      setError(err.userMessage || 'Failed to save pipeline')
    }
  }

  // Determine page title
  const pageTitle = isNew
    ? 'Create Pipeline'
    : isEditMode
    ? 'Edit Pipeline'
    : 'Pipeline Details'

  if (loadingPipeline && pipelineId) {
    return (
      <MainLayout pageTitle={pageTitle} pageIcon={GitBranch}>
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      </MainLayout>
    )
  }

  // ============================================================================
  // VIEW MODE
  // ============================================================================
  if (isViewMode && pipeline) {
    return (
      <MainLayout pageTitle="Pipeline Details" pageIcon={GitBranch}>
        {/* Historical version warning */}
        {isHistoricalVersion && latestVersion && (
          <Alert className="mb-4 border-amber-500/50 bg-amber-500/10">
            <History className="h-4 w-4 text-amber-500" />
            <AlertDescription className="text-amber-600 dark:text-amber-400">
              <strong>Viewing historical version {currentVersion}</strong> — The latest version is v{latestVersion}.{' '}
              <button
                className="underline font-medium hover:no-underline"
                onClick={() => loadVersion(latestVersion)}
              >
                View latest
              </button>
            </AlertDescription>
          </Alert>
        )}

        {/* Future graph visualization placeholder */}
        <Alert className="mb-4 border-blue-500/50 bg-blue-500/10">
          <Beaker className="h-4 w-4 text-blue-500" />
          <AlertDescription className="text-blue-600 dark:text-blue-400">
            <strong>Coming Soon:</strong> Visual pipeline graph will be displayed here in a future release.
          </AlertDescription>
        </Alert>

        <div className="space-y-6">
          {/* Pipeline Header */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-2xl font-bold text-foreground">{pipeline.name}</h2>
                  {pipeline.description && (
                    <p className="text-muted-foreground mt-1">{pipeline.description}</p>
                  )}
                  <div className="flex items-center gap-2 mt-3">
                    {pipeline.is_active && !isHistoricalVersion && (
                      <Badge variant="default" className="gap-1">
                        <Zap className="h-3 w-3" />
                        Active
                      </Badge>
                    )}
                    {pipeline.is_valid ? (
                      <Badge variant="outline" className="gap-1 border-green-500/50 text-green-600 dark:text-green-400">
                        <CheckCircle className="h-3 w-3" />
                        Valid
                      </Badge>
                    ) : (
                      <Badge variant="destructive" className="gap-1">
                        <XCircle className="h-3 w-3" />
                        Invalid
                      </Badge>
                    )}
                    {/* Version picker */}
                    {latestVersion && (
                      <div className="flex items-center gap-2">
                        <History className="h-4 w-4 text-muted-foreground" />
                        <Select
                          value={String(currentVersion)}
                          onValueChange={(v) => loadVersion(Number(v))}
                        >
                          <SelectTrigger className="w-32 h-7 text-sm">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {/* Always include current/latest version first */}
                            <SelectItem value={String(latestVersion)}>
                              v{latestVersion} (latest)
                            </SelectItem>
                            {/* Add historical versions from history */}
                            {history
                              .filter((h) => h.version < latestVersion)
                              .map((h) => (
                                <SelectItem key={h.version} value={String(h.version)}>
                                  v{h.version}
                                  {h.change_summary && (
                                    <span className="text-muted-foreground ml-1">
                                      - {h.change_summary.slice(0, 20)}
                                      {h.change_summary.length > 20 ? '...' : ''}
                                    </span>
                                  )}
                                </SelectItem>
                              ))}
                          </SelectContent>
                        </Select>
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    onClick={() => pipelineId && currentVersion && downloadYaml(pipelineId, currentVersion)}
                    disabled={downloading}
                  >
                    <Download className="h-4 w-4 mr-2" />
                    {downloading ? 'Exporting...' : `Export YAML${isHistoricalVersion ? ` (v${currentVersion})` : ''}`}
                  </Button>
                  {!isHistoricalVersion && (
                    <Button onClick={() => navigate(`/pipelines/${id}/edit`)}>
                      <Pencil className="h-4 w-4 mr-2" />
                      Edit Pipeline
                    </Button>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Validation Errors (View mode only) */}
          {!pipeline.is_valid && pipeline.validation_errors && pipeline.validation_errors.length > 0 && (
            <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 p-4 rounded-lg">
              <div className="flex items-center gap-2 font-medium mb-2 text-red-700 dark:text-red-400">
                <AlertTriangle className="h-4 w-4" />
                Validation Errors
              </div>
              <ul className="list-disc list-inside space-y-1 text-sm text-red-600 dark:text-red-300">
                {pipeline.validation_errors.map((err, i) => (
                  <li key={i}>{err}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Nodes */}
          <Card>
            <CardHeader>
              <CardTitle>Nodes ({pipeline.nodes.length})</CardTitle>
            </CardHeader>
            <CardContent>
              {pipeline.nodes.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No nodes defined.
                </div>
              ) : (
                <div className="space-y-4">
                  {pipeline.nodes.map((node, index) => (
                    <NodeViewer key={index} node={node} index={index} />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Edges */}
          <Card>
            <CardHeader>
              <CardTitle>Edges ({pipeline.edges.length})</CardTitle>
            </CardHeader>
            <CardContent>
              {pipeline.edges.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No edges defined.
                </div>
              ) : (
                <div className="space-y-2">
                  {pipeline.edges.map((edge, index) => (
                    <EdgeViewer key={index} edge={edge} index={index} />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Actions */}
          <div className="flex items-center justify-between py-4">
            <Button variant="outline" onClick={() => navigate('/pipelines')}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Pipelines
            </Button>
            {!isHistoricalVersion && (
              <Button onClick={() => navigate(`/pipelines/${id}/edit`)}>
                <Pencil className="h-4 w-4 mr-2" />
                Edit Pipeline
              </Button>
            )}
          </div>
        </div>
      </MainLayout>
    )
  }

  // ============================================================================
  // EDIT/CREATE MODE
  // ============================================================================
  return (
    <MainLayout pageTitle={pageTitle} pageIcon={GitBranch}>
      {/* Beta indicator */}
      <Alert className="mb-4 border-amber-500/50 bg-amber-500/10">
        <Beaker className="h-4 w-4 text-amber-500" />
        <AlertDescription className="text-amber-600 dark:text-amber-400">
          <strong>Beta Feature:</strong> Pipeline editor is currently in beta.
          The visual graph editor will be available in a future release.
        </AlertDescription>
      </Alert>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription className="flex items-center justify-between">
            <span>{error}</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setError(null)}
              className="h-auto p-1"
            >
              Dismiss
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Validation Result */}
      {validationResult && !validationResult.is_valid && (
        <Alert className="mb-4 border-orange-500/50 bg-orange-500/10">
          <AlertTriangle className="h-4 w-4 text-orange-500" />
          <AlertDescription>
            <div className="font-medium text-orange-600 dark:text-orange-400 mb-2">
              Validation Errors
            </div>
            <ul className="list-disc list-inside space-y-1 text-sm">
              {validationResult.errors.map((err, i) => (
                <li key={i}>{err.message}</li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      <div className="space-y-6">
        {/* Basic Info */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle>Pipeline Details</CardTitle>
            {/* Real-time validity indicator */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Status:</span>
              {isCurrentlyValid ? (
                <Badge variant="outline" className="gap-1 border-green-500/50 text-green-600 dark:text-green-400">
                  <CheckCircle className="h-3 w-3" />
                  Valid
                </Badge>
              ) : (
                <Badge variant="destructive" className="gap-1">
                  <XCircle className="h-3 w-3" />
                  Invalid
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="name">
                  Name <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., Standard RAW Pipeline"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Input
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Optional description"
                />
              </div>
            </div>
            {pipelineId && (
              <div className="mt-4 space-y-2">
                <Label htmlFor="changeSummary">Change Summary</Label>
                <Input
                  id="changeSummary"
                  value={changeSummary}
                  onChange={(e) => setChangeSummary(e.target.value)}
                  placeholder="Describe what changed (for version history)"
                />
              </div>
            )}
          </CardContent>
        </Card>

        {/* Validation Hints */}
        {validationHints.length > 0 && (
          <Alert className="border-amber-500/50 bg-amber-500/10">
            <AlertTriangle className="h-4 w-4 text-amber-500" />
            <AlertDescription>
              <div className="font-medium text-amber-600 dark:text-amber-400 mb-2">
                Validation Issues
              </div>
              <ul className="list-disc list-inside space-y-1 text-sm text-amber-600 dark:text-amber-400">
                {validationHints.map((hint, i) => (
                  <li key={i}>{hint}</li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        )}

        {/* Nodes */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
            <CardTitle>Nodes ({nodes.length})</CardTitle>
            <Button onClick={handleAddNode} size="sm">
              <Plus className="h-4 w-4 mr-1" />
              Add Node
            </Button>
          </CardHeader>
          <CardContent>
            {nodes.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No nodes defined. Click "Add Node" to get started.
              </div>
            ) : (
              <div className="space-y-4">
                {nodes.map((node, index) => (
                  <NodeEditor
                    key={index}
                    node={node}
                    index={index}
                    allNodes={nodes}
                    availableTypes={availableNodeTypes}
                    isTypeLocked={lockedNodeIndices.has(index)}
                    onChange={handleNodeChange}
                    onDelete={handleNodeDelete}
                    onTypeLock={handleTypeLock}
                  />
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Edges */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
            <CardTitle>Edges ({edges.length})</CardTitle>
            <Button onClick={handleAddEdge} size="sm" disabled={nodes.length < 2}>
              <Plus className="h-4 w-4 mr-1" />
              Add Edge
            </Button>
          </CardHeader>
          <CardContent>
            {edges.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No edges defined. Edges connect nodes to define the processing flow.
              </div>
            ) : (
              <div className="space-y-2">
                {edges.map((edge, index) => (
                  <EdgeEditor
                    key={index}
                    edge={edge}
                    index={index}
                    nodes={nodes}
                    onChange={handleEdgeChange}
                    onDelete={handleEdgeDelete}
                  />
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="flex items-center justify-between py-4">
          <Button variant="outline" onClick={() => navigate('/pipelines')}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-foreground mr-2" />
                Saving...
              </>
            ) : (
              <>
                <Save className="h-4 w-4 mr-2" />
                {pipelineId ? 'Save Changes' : 'Create Pipeline'}
              </>
            )}
          </Button>
        </div>
      </div>
    </MainLayout>
  )
}

export default PipelineEditorPage
