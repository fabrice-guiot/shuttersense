/**
 * CamerasTab component
 *
 * Camera management tab within the Resources page.
 * Includes search, status filter, edit dialog, pagination, and TopHeader KPI stats.
 */

import { useState, useEffect, useCallback } from 'react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useCameras, useCameraStats } from '@/hooks/useCameras'
import { useHeaderStats } from '@/contexts/HeaderStatsContext'
import { CameraList } from './CameraList'
import { CameraEditDialog } from './CameraEditDialog'
import { DirectoryPagination } from '@/components/directory/DirectoryPagination'
import type { CameraResponse, CameraStatus, CameraUpdateRequest } from '@/contracts/api/camera-api'

// ============================================================================
// Component
// ============================================================================

export function CamerasTab() {
  const {
    cameras,
    total,
    loading,
    error,
    fetchCameras,
    updateCamera,
    deleteCamera,
  } = useCameras({ autoFetch: false })

  // KPI Stats for header
  const { stats, refetch: refetchStats } = useCameraStats(true)
  const { setStats } = useHeaderStats()

  // Search state
  const [search, setSearch] = useState('')
  const [appliedSearch, setAppliedSearch] = useState('')

  // Status filter state
  const [statusFilter, setStatusFilter] = useState<string>('all')

  // Pagination state
  const [page, setPage] = useState(1)
  const [limit, setLimit] = useState(20)

  // Edit dialog state
  const [editingCamera, setEditingCamera] = useState<CameraResponse | null>(null)
  const [editDialogOpen, setEditDialogOpen] = useState(false)

  // Fetch with current filters and pagination
  const doFetch = useCallback(() => {
    fetchCameras({
      search: appliedSearch || undefined,
      status: statusFilter !== 'all' ? statusFilter as CameraStatus : undefined,
      limit,
      offset: (page - 1) * limit,
    })
  }, [fetchCameras, appliedSearch, statusFilter, limit, page])

  useEffect(() => {
    doFetch()
  }, [doFetch])

  // Update header stats when data changes
  useEffect(() => {
    if (stats) {
      setStats([
        { label: 'Total Cameras', value: stats.total_cameras },
        { label: 'Confirmed', value: stats.confirmed_count },
        { label: 'Temporary', value: stats.temporary_count },
      ])
    }
    return () => setStats([])
  }, [stats, setStats])

  // Handlers
  const handleEdit = (camera: CameraResponse) => {
    setEditingCamera(camera)
    setEditDialogOpen(true)
  }

  const handleEditSubmit = async (guid: string, data: CameraUpdateRequest) => {
    await updateCamera(guid, data)
    refetchStats()
    doFetch()
  }

  const handleDelete = (camera: CameraResponse) => {
    deleteCamera(camera.guid)
      .then(() => {
        refetchStats()
        doFetch()
      })
      .catch(() => {
        // Error handled by hook
      })
  }

  const handleSearch = () => {
    setAppliedSearch(search)
    setPage(1)
  }

  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  const handleStatusFilterChange = (value: string) => {
    setStatusFilter(value)
    setPage(1)
  }

  const handlePageChange = (newPage: number) => {
    setPage(newPage)
  }

  const handleLimitChange = (newLimit: number) => {
    setLimit(newLimit)
    setPage(1)
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Search + Filter Row */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap gap-2">
          <Input
            placeholder="Search cameras..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={handleSearchKeyDown}
            className="max-w-sm"
          />
          <Select value={statusFilter} onValueChange={handleStatusFilterChange}>
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder="All Statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="temporary">Temporary</SelectItem>
              <SelectItem value="confirmed">Confirmed</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={handleSearch}>
            Search
          </Button>
          {(search || statusFilter !== 'all') && (
            <Button variant="ghost" onClick={() => { setSearch(''); setAppliedSearch(''); setStatusFilter('all'); setPage(1) }}>
              Clear
            </Button>
          )}
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Camera List */}
      <CameraList
        cameras={cameras}
        loading={loading}
        onEdit={handleEdit}
        onDelete={handleDelete}
      />

      {/* Pagination */}
      {total > 0 && (
        <DirectoryPagination
          page={page}
          limit={limit}
          total={total}
          onPageChange={handlePageChange}
          onLimitChange={handleLimitChange}
        />
      )}

      {/* Edit Dialog */}
      <CameraEditDialog
        camera={editingCamera}
        open={editDialogOpen}
        onOpenChange={setEditDialogOpen}
        onSubmit={handleEditSubmit}
      />
    </div>
  )
}

export default CamerasTab
