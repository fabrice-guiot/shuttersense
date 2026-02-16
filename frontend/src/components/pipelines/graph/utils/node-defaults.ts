import {
  Camera,
  FileText,
  Settings,
  Merge,
  GitBranch,
  Archive,
  type LucideIcon,
} from 'lucide-react'
import type { NodeType } from '@/contracts/api/pipelines-api'
import { NODE_TYPE_DEFINITIONS } from '@/contracts/api/pipelines-api'

export interface NodeConfig {
  icon: LucideIcon
  colorClass: string
  shapeClass: string
  defaultWidth: number
  defaultHeight: number
}

const NODE_CONFIGS: Record<NodeType, NodeConfig> = {
  capture: {
    icon: Camera,
    colorClass: 'border-primary text-primary',
    shapeClass: 'rounded-lg',
    defaultWidth: 224, // w-56
    defaultHeight: 80, // h-20
  },
  file: {
    icon: FileText,
    colorClass: 'border-muted-foreground text-muted-foreground',
    shapeClass: 'rounded-md',
    defaultWidth: 192, // w-48
    defaultHeight: 64, // h-16
  },
  process: {
    icon: Settings,
    colorClass: 'border-purple-500 text-purple-500',
    shapeClass: 'rounded-md',
    defaultWidth: 192,
    defaultHeight: 64,
  },
  pairing: {
    icon: Merge,
    colorClass: 'border-info text-info',
    shapeClass: 'rounded-md',
    defaultWidth: 208, // w-52
    defaultHeight: 80, // h-20
  },
  branching: {
    icon: GitBranch,
    colorClass: 'border-warning text-warning',
    shapeClass: 'rounded-md',
    defaultWidth: 208, // w-52
    defaultHeight: 80, // h-20
  },
  termination: {
    icon: Archive,
    colorClass: 'border-success text-success',
    shapeClass: 'rounded-lg',
    defaultWidth: 192,
    defaultHeight: 64,
  },
}

/** Get the node visual config (icon, color, shape) for a type */
export function getNodeConfig(type: NodeType): NodeConfig {
  return NODE_CONFIGS[type]
}

/** Generate a unique node ID for a given type */
export function generateNodeId(type: NodeType, existingIds: string[]): string {
  let counter = 1
  while (existingIds.includes(`${type}_${counter}`)) {
    counter++
  }
  return `${type}_${counter}`
}

/** Get default properties for a node type */
export function getDefaultProperties(type: NodeType): Record<string, unknown> {
  const definition = NODE_TYPE_DEFINITIONS.find((d) => d.type === type)
  if (!definition) return {}

  const defaults: Record<string, unknown> = {}
  for (const prop of definition.properties) {
    if (prop.default !== undefined) {
      defaults[prop.key] = prop.default
    } else if (prop.type === 'string') {
      defaults[prop.key] = ''
    } else if (prop.type === 'boolean') {
      defaults[prop.key] = false
    } else if (prop.type === 'array') {
      defaults[prop.key] = []
    } else if (prop.type === 'select' && prop.options?.length) {
      defaults[prop.key] = prop.options[0]
    }
  }
  return defaults
}
