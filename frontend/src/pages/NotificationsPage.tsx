/**
 * Notifications Page
 *
 * Full page for viewing and managing all notifications.
 * Provides text search, category filter, read/unread filter,
 * date range filter, and pagination.
 *
 * Accessible via "View all" link in the bell popover.
 *
 * Issue #114 - PWA with Push Notifications
 */

import { useState, useEffect, useCallback, useMemo } from 'react'
import { BellOff, Search } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { DatePicker } from '@/components/ui/date-picker'
import {
  ResponsiveTable,
  type ColumnDef,
} from '@/components/ui/responsive-table'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useHeaderStats } from '@/contexts/HeaderStatsContext'
import {
  useNotifications,
  useNotificationStats,
} from '@/hooks/useNotifications'
import { NotificationDetailDialog } from '@/components/notifications/NotificationDetailDialog'
import { formatRelativeTime } from '@/utils/dateFormat'
import type { NotificationResponse } from '@/contracts/api/notification-api'
import type { NotificationCategory } from '@/contracts/domain-labels'
import {
  NOTIFICATION_CATEGORY_LABELS,
  NOTIFICATION_CATEGORY_ICONS,
  NOTIFICATION_CATEGORY_BADGE_VARIANT,
} from '@/contracts/domain-labels'

// ============================================================================
// Constants
// ============================================================================

const DEBOUNCE_MS = 300

const DATE_PRESETS = [
  { label: 'All time', value: 'all' },
  { label: 'Last 7 days', value: '7' },
  { label: 'Last 30 days', value: '30' },
  { label: 'Last 90 days', value: '90' },
  { label: 'Custom', value: 'custom' },
] as const

const CATEGORIES: { label: string; value: NotificationCategory }[] = [
  { label: 'Job Failures', value: 'job_failure' },
  { label: 'Inflection Points', value: 'inflection_point' },
  { label: 'Agent Status', value: 'agent_status' },
  { label: 'Deadlines', value: 'deadline' },
  { label: 'Retry Warnings', value: 'retry_warning' },
]

const READ_STATUS_OPTIONS = [
  { label: 'All', value: 'all' },
  { label: 'Unread', value: 'unread' },
  { label: 'Read', value: 'read' },
] as const

// ============================================================================
// Helpers
// ============================================================================

function getDateRangeFromPreset(preset: string): { from?: string; to?: string } {
  if (preset === 'all' || preset === 'custom') {
    return {}
  }
  const days = parseInt(preset, 10)
  const now = new Date()
  const from = new Date(now)
  from.setDate(from.getDate() - days)
  return {
    from: from.toISOString().slice(0, 10),
    to: now.toISOString().slice(0, 10),
  }
}

// ============================================================================
// Component
// ============================================================================

export default function NotificationsPage() {
  // State: filters
  const [searchInput, setSearchInput] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [category, setCategory] = useState<string>('all')
  const [readStatus, setReadStatus] = useState<string>('all')
  const [datePreset, setDatePreset] = useState('all')
  const [customFrom, setCustomFrom] = useState<string | undefined>()
  const [customTo, setCustomTo] = useState<string | undefined>()

  // State: pagination
  const [page, setPage] = useState(1)
  const [limit, setLimit] = useState(20)

  // State: detail dialog
  const [selected, setSelected] = useState<NotificationResponse | null>(null)

  // Hooks
  const { stats } = useNotificationStats()
  const { setStats } = useHeaderStats()
  const {
    notifications,
    total,
    loading,
    fetchNotifications,
    markAsRead,
  } = useNotifications(false)

  // TopHeader KPI stats
  useEffect(() => {
    if (stats) {
      setStats([
        { label: 'Total', value: stats.total_count },
        { label: 'Unread', value: stats.unread_count },
        { label: 'This Week', value: stats.this_week_count },
      ])
    }
    return () => setStats([])
  }, [stats, setStats])

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearchTerm(searchInput)
      setPage(1)
    }, DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [searchInput])

  // Compute date range
  const dateRange = useMemo(() => {
    if (datePreset === 'custom') {
      return { from: customFrom, to: customTo }
    }
    return getDateRangeFromPreset(datePreset)
  }, [datePreset, customFrom, customTo])

  // Fetch notifications when filters or pagination change
  const doFetch = useCallback(() => {
    const params: Record<string, unknown> = {
      limit,
      offset: (page - 1) * limit,
    }
    if (searchTerm) params.search = searchTerm
    if (category !== 'all') params.category = category
    if (readStatus === 'unread') params.unread_only = true
    if (readStatus === 'read') params.read_only = true
    if (dateRange.from) params.from_date = dateRange.from
    if (dateRange.to) params.to_date = dateRange.to

    fetchNotifications(params)
  }, [limit, page, searchTerm, category, readStatus, dateRange, fetchNotifications])

  useEffect(() => {
    doFetch()
  }, [doFetch])

  // Reset page when filters change
  const handleCategoryChange = (value: string) => {
    setCategory(value)
    setPage(1)
  }
  const handleReadStatusChange = (value: string) => {
    setReadStatus(value)
    setPage(1)
  }
  const handleDatePresetChange = (value: string) => {
    setDatePreset(value)
    if (value !== 'custom') {
      setCustomFrom(undefined)
      setCustomTo(undefined)
    }
    setPage(1)
  }
  const handleLimitChange = (value: number) => {
    setLimit(value)
    setPage(1)
  }

  // Notification click → mark read + show detail
  const handleNotificationClick = async (notification: NotificationResponse) => {
    if (notification.read_at === null) {
      await markAsRead(notification.guid)
    }
    setSelected(notification)
  }

  const totalPages = Math.max(1, Math.ceil(total / limit))

  // Table columns
  const columns: ColumnDef<NotificationResponse>[] = [
    {
      header: 'Title',
      cardRole: 'title',
      cell: (n) => (
        <span className="flex items-center gap-2">
          {n.read_at === null && (
            <span className="h-2 w-2 shrink-0 rounded-full bg-primary" />
          )}
          <span className="truncate font-medium">{n.title}</span>
        </span>
      ),
      cellClassName: 'max-w-[250px]',
    },
    {
      header: 'Category',
      cardRole: 'badge',
      cell: (n) => {
        const Icon = NOTIFICATION_CATEGORY_ICONS[n.category]
        const label = NOTIFICATION_CATEGORY_LABELS[n.category]
        const variant = NOTIFICATION_CATEGORY_BADGE_VARIANT[n.category]
        return (
          <Badge variant={variant} className="gap-1">
            {Icon && <Icon className="h-3 w-3" />}
            {label}
          </Badge>
        )
      },
    },
    {
      header: 'Body',
      cardRole: 'subtitle',
      cell: (n) => (
        <span className="text-muted-foreground line-clamp-1">{n.body}</span>
      ),
      cellClassName: 'max-w-[300px]',
    },
    {
      header: 'Date',
      cell: (n) => (
        <span className="text-muted-foreground whitespace-nowrap">
          {formatRelativeTime(n.created_at)}
        </span>
      ),
    },
    {
      header: 'Status',
      cell: (n) =>
        n.read_at ? (
          <Badge variant="muted">Read</Badge>
        ) : (
          <Badge variant="secondary">Unread</Badge>
        ),
    },
  ]

  // Empty state
  const emptyState = (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <BellOff className="h-10 w-10 text-muted-foreground/50 mb-3" />
      <p className="text-sm font-medium text-muted-foreground">
        No notifications found
      </p>
      <p className="text-xs text-muted-foreground mt-1">
        Try adjusting your filters or check back later
      </p>
    </div>
  )

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="rounded-lg border border-border bg-card p-4">
        <div className="flex flex-col gap-3">
          {/* Row 1: Search + Category + Status */}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            {/* Search */}
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search notifications..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                className="pl-9"
              />
            </div>

            {/* Category */}
            <Select value={category} onValueChange={handleCategoryChange}>
              <SelectTrigger className="w-full sm:w-[180px]">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All categories</SelectItem>
                {CATEGORIES.map((cat) => (
                  <SelectItem key={cat.value} value={cat.value}>
                    {cat.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Read/Unread */}
            <Select value={readStatus} onValueChange={handleReadStatusChange}>
              <SelectTrigger className="w-full sm:w-[140px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                {READ_STATUS_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Row 2: Date range */}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <Select value={datePreset} onValueChange={handleDatePresetChange}>
              <SelectTrigger className="w-full sm:w-[160px]">
                <SelectValue placeholder="Date range" />
              </SelectTrigger>
              <SelectContent>
                {DATE_PRESETS.map((preset) => (
                  <SelectItem key={preset.value} value={preset.value}>
                    {preset.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {datePreset === 'custom' && (
              <>
                <DatePicker
                  value={customFrom}
                  onChange={(date) => {
                    setCustomFrom(date)
                    setPage(1)
                  }}
                  placeholder="From date"
                  clearable
                />
                <DatePicker
                  value={customTo}
                  onChange={(date) => {
                    setCustomTo(date)
                    setPage(1)
                  }}
                  placeholder="To date"
                  clearable
                />
              </>
            )}
          </div>
        </div>
      </div>

      {/* Table */}
      <ResponsiveTable
        data={notifications}
        columns={columns}
        keyField="guid"
        emptyState={!loading ? emptyState : undefined}
        onRowClick={handleNotificationClick}
      />

      {/* Loading state */}
      {loading && notifications.length === 0 && (
        <div className="flex items-center justify-center py-16">
          <p className="text-sm text-muted-foreground">Loading notifications...</p>
        </div>
      )}

      {/* Pagination */}
      {total > 0 && (
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Rows per page:</span>
            <Select
              value={limit.toString()}
              onValueChange={(value) => handleLimitChange(parseInt(value, 10))}
            >
              <SelectTrigger className="w-[70px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="10">10</SelectItem>
                <SelectItem value="20">20</SelectItem>
                <SelectItem value="50">50</SelectItem>
              </SelectContent>
            </Select>
            <span className="text-sm text-muted-foreground">
              {(page - 1) * limit + 1}-{Math.min(page * limit, total)} of {total}
            </span>
          </div>

          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="icon"
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="px-2 text-sm">
              Page {page} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="icon"
              disabled={page >= totalPages}
              onClick={() => setPage(page + 1)}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Detail dialog */}
      <NotificationDetailDialog
        notification={selected}
        onClose={() => setSelected(null)}
      />
    </div>
  )
}
