/**
 * PipelineList component
 *
 * Displays a grid of pipeline cards with filtering and actions
 */

import React from 'react'
import { Plus, Upload, Search, GitBranch } from 'lucide-react'
import type { PipelineSummary } from '@/contracts/api/pipelines-api'
import { PipelineCard } from './PipelineCard'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Tabs, TabsTrigger } from '@/components/ui/tabs'
import { ResponsiveTabsList, type TabOption } from '@/components/ui/responsive-tabs-list'

interface PipelineListProps {
  pipelines: PipelineSummary[]
  loading: boolean
  error: string | null
  onCreateNew: () => void
  onImport: () => void
  onEdit: (pipeline: PipelineSummary) => void
  onDelete: (pipeline: PipelineSummary) => void
  onActivate: (pipeline: PipelineSummary) => void
  onDeactivate: (pipeline: PipelineSummary) => void
  onSetDefault: (pipeline: PipelineSummary) => void
  onUnsetDefault: (pipeline: PipelineSummary) => void
  onExport: (pipeline: PipelineSummary) => void
  onView: (pipeline: PipelineSummary) => void
  onValidateGraph?: (pipeline: PipelineSummary) => void
}

export const PipelineList: React.FC<PipelineListProps> = ({
  pipelines,
  loading,
  error,
  onCreateNew,
  onImport,
  onEdit,
  onDelete,
  onActivate,
  onDeactivate,
  onSetDefault,
  onUnsetDefault,
  onExport,
  onView,
  onValidateGraph,
}) => {
  const [searchTerm, setSearchTerm] = React.useState('')
  const [filterStatus, setFilterStatus] = React.useState<'all' | 'valid' | 'invalid' | 'active' | 'default'>(
    'all'
  )

  const filterTabOptions: TabOption[] = [
    { value: 'all', label: 'All' },
    { value: 'default', label: 'Default' },
    { value: 'active', label: 'Active' },
    { value: 'valid', label: 'Valid' },
    { value: 'invalid', label: 'Invalid' },
  ]

  // Filter pipelines
  const filteredPipelines = React.useMemo(() => {
    return pipelines.filter((pipeline) => {
      // Search filter
      const matchesSearch =
        !searchTerm ||
        pipeline.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (pipeline.description &&
          pipeline.description.toLowerCase().includes(searchTerm.toLowerCase()))

      // Status filter
      let matchesStatus = true
      if (filterStatus === 'valid') {
        matchesStatus = pipeline.is_valid
      } else if (filterStatus === 'invalid') {
        matchesStatus = !pipeline.is_valid
      } else if (filterStatus === 'active') {
        matchesStatus = pipeline.is_active
      } else if (filterStatus === 'default') {
        matchesStatus = pipeline.is_default
      }

      return matchesSearch && matchesStatus
    })
  }, [pipelines, searchTerm, filterStatus])

  if (error) {
    return (
      <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-4 text-destructive">
        <p className="font-medium">Error loading pipelines</p>
        <p className="text-sm">{error}</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        {/* Search and Filter */}
        <div className="flex items-center gap-3">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search pipelines..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9 w-64"
            />
          </div>

          {/* Status Filter */}
          <Tabs value={filterStatus} onValueChange={(v) => setFilterStatus(v as typeof filterStatus)}>
            <ResponsiveTabsList
              tabs={filterTabOptions}
              value={filterStatus}
              onValueChange={(v) => setFilterStatus(v as typeof filterStatus)}
            >
              {filterTabOptions.map((tab) => (
                <TabsTrigger key={tab.value} value={tab.value}>
                  {tab.label}
                </TabsTrigger>
              ))}
            </ResponsiveTabsList>
          </Tabs>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={onImport}>
            <Upload className="h-4 w-4 mr-2" />
            Import YAML
          </Button>
          <Button onClick={onCreateNew}>
            <Plus className="h-4 w-4 mr-2" />
            New Pipeline
          </Button>
        </div>
      </div>

      {/* Pipeline Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="bg-card rounded-lg border p-4 animate-pulse"
            >
              <div className="flex items-start gap-3 mb-3">
                <div className="h-10 w-10 bg-muted rounded-lg" />
                <div className="flex-1">
                  <div className="h-5 w-32 bg-muted rounded mb-2" />
                  <div className="h-4 w-16 bg-muted rounded" />
                </div>
              </div>
              <div className="h-4 w-full bg-muted rounded mb-3" />
              <div className="flex gap-2">
                <div className="h-5 w-16 bg-muted rounded-full" />
                <div className="h-5 w-16 bg-muted rounded-full" />
              </div>
            </div>
          ))}
        </div>
      ) : filteredPipelines.length === 0 ? (
        <div className="text-center py-12">
          <GitBranch className="h-12 w-12 text-muted-foreground/50 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-foreground mb-2">
            {pipelines.length === 0 ? 'No pipelines yet' : 'No matching pipelines'}
          </h3>
          <p className="text-muted-foreground mb-4">
            {pipelines.length === 0
              ? 'Create your first pipeline to define photo processing workflows.'
              : 'Try adjusting your search or filter criteria.'}
          </p>
          {pipelines.length === 0 && (
            <Button onClick={onCreateNew}>
              <Plus className="h-4 w-4 mr-2" />
              Create Pipeline
            </Button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredPipelines.map((pipeline) => (
            <PipelineCard
              key={pipeline.guid}
              pipeline={pipeline}
              onEdit={onEdit}
              onDelete={onDelete}
              onActivate={onActivate}
              onDeactivate={onDeactivate}
              onSetDefault={onSetDefault}
              onUnsetDefault={onUnsetDefault}
              onExport={onExport}
              onView={onView}
              onValidateGraph={onValidateGraph}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default PipelineList
