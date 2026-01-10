/**
 * PipelineFilter Component
 *
 * Dropdown selectors for filtering trends by pipeline and version
 */

import { useEffect, useState, useCallback, useMemo } from 'react'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import type { PipelineSummary, PipelineHistoryEntry } from '@/contracts/api/pipelines-api'
import * as pipelinesService from '@/services/pipelines'

interface VersionOption {
  version: number
  label: string
  isCurrent: boolean
}

interface PipelineFilterProps {
  pipelines: PipelineSummary[]
  selectedPipelineGuid: string | null
  selectedPipelineVersion: number | null
  onPipelineChange: (pipelineGuid: string | null) => void
  onVersionChange: (version: number | null) => void
  className?: string
}

export function PipelineFilter({
  pipelines,
  selectedPipelineGuid,
  selectedPipelineVersion,
  onPipelineChange,
  onVersionChange,
  className = ''
}: PipelineFilterProps) {
  const [historyVersions, setHistoryVersions] = useState<PipelineHistoryEntry[]>([])
  const [loadingVersions, setLoadingVersions] = useState(false)

  // Get the selected pipeline to access its current version
  const selectedPipeline = useMemo(() => {
    return pipelines.find((p) => p.guid === selectedPipelineGuid) ?? null
  }, [pipelines, selectedPipelineGuid])

  // Build version options: current version + history versions
  const versionOptions = useMemo((): VersionOption[] => {
    const options: VersionOption[] = []

    // Add current version from the pipeline itself
    if (selectedPipeline) {
      options.push({
        version: selectedPipeline.version,
        label: `v${selectedPipeline.version} (Current)`,
        isCurrent: true
      })
    }

    // Add historical versions (excluding current if it's in history)
    for (const entry of historyVersions) {
      if (!selectedPipeline || entry.version !== selectedPipeline.version) {
        options.push({
          version: entry.version,
          label: entry.change_summary
            ? `v${entry.version} - ${entry.change_summary}`
            : `v${entry.version}`,
          isCurrent: false
        })
      }
    }

    // Sort by version descending (newest first)
    return options.sort((a, b) => b.version - a.version)
  }, [selectedPipeline, historyVersions])

  // Fetch history versions when pipeline changes
  const fetchVersions = useCallback(async (pipelineGuid: string) => {
    setLoadingVersions(true)
    try {
      const history = await pipelinesService.getPipelineHistory(pipelineGuid)
      setHistoryVersions(history)
    } catch (err) {
      console.error('Failed to load pipeline versions:', err)
      setHistoryVersions([])
    } finally {
      setLoadingVersions(false)
    }
  }, [])

  useEffect(() => {
    if (selectedPipelineGuid) {
      fetchVersions(selectedPipelineGuid)
    } else {
      setHistoryVersions([])
    }
  }, [selectedPipelineGuid, fetchVersions])

  const handlePipelineChange = (value: string) => {
    if (value === 'all') {
      onPipelineChange(null)
      onVersionChange(null)
    } else {
      onPipelineChange(value)
      onVersionChange(null) // Reset version when pipeline changes
    }
  }

  const handleVersionChange = (value: string) => {
    if (value === 'all') {
      onVersionChange(null)
    } else {
      onVersionChange(parseInt(value, 10))
    }
  }

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Pipeline Selector */}
      <div className="space-y-2">
        <Label className="text-sm font-medium">Pipeline</Label>
        <Select
          value={selectedPipelineGuid ?? 'all'}
          onValueChange={handlePipelineChange}
        >
          <SelectTrigger>
            <SelectValue placeholder="All Pipelines" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Pipelines</SelectItem>
            {pipelines.map((pipeline) => (
              <SelectItem key={pipeline.guid} value={pipeline.guid}>
                {pipeline.name}
                {pipeline.is_default && ' (Default)'}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Version Selector - only show when pipeline is selected */}
      {selectedPipelineGuid && (
        <div className="space-y-2">
          <Label className="text-sm font-medium">Version</Label>
          <Select
            value={selectedPipelineVersion?.toString() ?? 'all'}
            onValueChange={handleVersionChange}
            disabled={loadingVersions || versionOptions.length === 0}
          >
            <SelectTrigger>
              <SelectValue placeholder={loadingVersions ? 'Loading...' : 'All Versions'} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Versions</SelectItem>
              {versionOptions.map((option) => (
                <SelectItem key={option.version} value={option.version.toString()}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}
    </div>
  )
}
