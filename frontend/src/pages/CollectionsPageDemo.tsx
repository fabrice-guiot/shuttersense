/**
 * CollectionsPage Demo - Standalone version with mock data
 * No API dependencies, renders the collections UI directly
 */

import { useState } from 'react'
import { Plus, Search, MoreHorizontal, RefreshCw, Pencil, Trash2, Info, Cloud, CheckCircle, XCircle, Clock, Archive, Plug } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

// Mock data
const MOCK_COLLECTIONS = [
  {
    guid: 'col-001-wedding-2024',
    name: 'Wedding Photos 2024',
    description: 'Sarah & John wedding ceremony and reception',
    connector_name: 'AWS S3 Production',
    type: 'S3',
    state: 'LIVE',
    is_accessible: true,
    bound_agent_name: null,
    pipeline_name: 'Wedding Photo Pipeline',
    file_count: 2450,
    total_bytes: 45678901234,
    image_count: 2380,
    updated_at: '2024-03-15T10:30:00Z',
  },
  {
    guid: 'col-002-studio-portraits',
    name: 'Studio Portraits',
    description: 'Professional headshots and portrait sessions',
    connector_name: 'Local Storage',
    type: 'LOCAL',
    state: 'LIVE',
    is_accessible: true,
    bound_agent_name: 'Studio Workstation',
    pipeline_name: null,
    file_count: 890,
    total_bytes: 12345678901,
    image_count: 890,
    updated_at: '2024-03-14T16:00:00Z',
  },
  {
    guid: 'col-003-event-archive',
    name: 'Event Photography Archive',
    description: 'Corporate events and conferences 2023',
    connector_name: 'Google Cloud Storage',
    type: 'GCS_BETA',
    state: 'ARCHIVED',
    is_accessible: false,
    bound_agent_name: null,
    pipeline_name: 'Event Processing',
    file_count: 15000,
    total_bytes: 234567890123,
    image_count: 14500,
    updated_at: '2024-02-28T12:00:00Z',
  },
  {
    guid: 'col-004-corporate-headshots',
    name: 'Corporate Headshots',
    description: 'Executive portraits for company website',
    connector_name: 'Office NAS',
    type: 'SMB_BETA',
    state: 'CLOSED',
    is_accessible: null,
    bound_agent_name: null,
    pipeline_name: null,
    file_count: null,
    total_bytes: null,
    image_count: null,
    updated_at: '2024-03-01T14:00:00Z',
  },
  {
    guid: 'col-005-nature-photography',
    name: 'Nature Photography',
    description: 'Wildlife and landscape shots from 2024 expeditions',
    connector_name: 'AWS S3 Archive',
    type: 'S3',
    state: 'LIVE',
    is_accessible: true,
    bound_agent_name: null,
    pipeline_name: 'Nature Analysis',
    file_count: 5670,
    total_bytes: 98765432109,
    image_count: 5500,
    updated_at: '2024-03-15T08:00:00Z',
  },
]

function formatBytes(bytes: number | null): string {
  if (bytes === null || bytes === undefined) return '-'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let unitIndex = 0
  let size = bytes
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  return `${size.toFixed(1)} ${units[unitIndex]}`
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function StateIcon({ state }: { state: string }) {
  switch (state) {
    case 'LIVE':
      return <CheckCircle className="h-4 w-4 text-green-500" />
    case 'ARCHIVED':
      return <Archive className="h-4 w-4 text-muted-foreground" />
    case 'CLOSED':
      return <Clock className="h-4 w-4 text-yellow-500" />
    default:
      return null
  }
}

function AccessibilityBadge({ isAccessible }: { isAccessible: boolean | null }) {
  if (isAccessible === null) {
    return (
      <Badge variant="outline" className="text-muted-foreground">
        Pending
      </Badge>
    )
  }
  return isAccessible ? (
    <Badge variant="outline" className="text-green-600 border-green-600">
      Accessible
    </Badge>
  ) : (
    <Badge variant="outline" className="text-red-600 border-red-600">
      Not Accessible
    </Badge>
  )
}

function TypeBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    S3: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
    LOCAL: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    GCS_BETA: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    SMB_BETA: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  }
  return (
    <Badge className={colors[type] || 'bg-gray-100 text-gray-800'} variant="secondary">
      {type.replace('_BETA', ' Beta')}
    </Badge>
  )
}

export default function CollectionsPageDemo() {
  const [search, setSearch] = useState('')
  const [selectedState, setSelectedState] = useState<string>('ALL')
  const [selectedType, setSelectedType] = useState<string>('ALL')
  const [accessibleOnly, setAccessibleOnly] = useState(false)

  // Filter collections based on current filters
  const filteredCollections = MOCK_COLLECTIONS.filter((c) => {
    if (search && !c.name.toLowerCase().includes(search.toLowerCase())) {
      return false
    }
    if (selectedState !== 'ALL' && c.state !== selectedState) {
      return false
    }
    if (selectedType !== 'ALL' && c.type !== selectedType) {
      return false
    }
    if (accessibleOnly && c.is_accessible !== true) {
      return false
    }
    return true
  })

  const stats = {
    total: MOCK_COLLECTIONS.length,
    files: MOCK_COLLECTIONS.reduce((acc, c) => acc + (c.file_count || 0), 0),
    storage: MOCK_COLLECTIONS.reduce((acc, c) => acc + (c.total_bytes || 0), 0),
  }

  return (
    <TooltipProvider>
      <div className="flex flex-col gap-6 p-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Collections</h1>
            <p className="text-sm text-muted-foreground mt-1">
              {stats.total} collections &middot; {stats.files.toLocaleString()} files &middot; {formatBytes(stats.storage)}
            </p>
          </div>
          <Button onClick={() => toast.info('Create collection dialog would open')} className="gap-2">
            <Plus className="h-4 w-4" />
            New Collection
          </Button>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-4">
          <div className="relative flex-1 min-w-[200px] max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search collections..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>

          <Select value={selectedState} onValueChange={setSelectedState}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="State" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">All States</SelectItem>
              <SelectItem value="LIVE">Live</SelectItem>
              <SelectItem value="ARCHIVED">Archived</SelectItem>
              <SelectItem value="CLOSED">Closed</SelectItem>
            </SelectContent>
          </Select>

          <Select value={selectedType} onValueChange={setSelectedType}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">All Types</SelectItem>
              <SelectItem value="S3">S3</SelectItem>
              <SelectItem value="LOCAL">Local</SelectItem>
              <SelectItem value="GCS_BETA">GCS Beta</SelectItem>
              <SelectItem value="SMB_BETA">SMB Beta</SelectItem>
            </SelectContent>
          </Select>

          <div className="flex items-center gap-2">
            <Checkbox
              id="accessible-only"
              checked={accessibleOnly}
              onCheckedChange={(checked) => setAccessibleOnly(checked === true)}
            />
            <Label htmlFor="accessible-only" className="text-sm cursor-pointer">
              Accessible only
            </Label>
          </div>
        </div>

        {/* Table */}
        <div className="rounded-lg border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[250px]">Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>State</TableHead>
                <TableHead>Accessibility</TableHead>
                <TableHead>Connector</TableHead>
                <TableHead className="text-right">Files</TableHead>
                <TableHead className="text-right">Size</TableHead>
                <TableHead>Updated</TableHead>
                <TableHead className="w-[50px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredCollections.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} className="h-24 text-center text-muted-foreground">
                    No collections found
                  </TableCell>
                </TableRow>
              ) : (
                filteredCollections.map((collection) => (
                  <TableRow key={collection.guid}>
                    <TableCell>
                      <div>
                        <div className="font-medium">{collection.name}</div>
                        {collection.description && (
                          <div className="text-sm text-muted-foreground truncate max-w-[220px]">
                            {collection.description}
                          </div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <TypeBadge type={collection.type} />
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <StateIcon state={collection.state} />
                        <span className="text-sm">{collection.state}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <AccessibilityBadge isAccessible={collection.is_accessible} />
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Plug className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm">{collection.connector_name}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-right font-mono text-sm">
                      {collection.file_count?.toLocaleString() || '-'}
                    </TableCell>
                    <TableCell className="text-right font-mono text-sm">
                      {formatBytes(collection.total_bytes)}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDate(collection.updated_at)}
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-8 w-8">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => toast.info(`Run analysis on ${collection.name}`)}>
                            <RefreshCw className="h-4 w-4 mr-2" />
                            Run Analysis
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => toast.info(`Refresh from cloud: ${collection.name}`)}>
                            <Cloud className="h-4 w-4 mr-2" />
                            Refresh from Cloud
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => toast.info(`Test accessibility: ${collection.name}`)}>
                            <Info className="h-4 w-4 mr-2" />
                            Test Accessibility
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem onClick={() => toast.info(`Edit ${collection.name}`)}>
                            <Pencil className="h-4 w-4 mr-2" />
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() => toast.error(`Delete ${collection.name}`)}
                            className="text-red-600"
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>
    </TooltipProvider>
  )
}
