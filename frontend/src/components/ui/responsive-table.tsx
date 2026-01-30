import * as React from 'react'

import { cn } from '@/lib/utils'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

export type CardRole = 'title' | 'subtitle' | 'badge' | 'detail' | 'action' | 'hidden'

export interface ColumnDef<T> {
  header: string
  headerClassName?: string
  cell: (item: T) => React.ReactNode
  cellClassName?: string
  cardRole?: CardRole
}

export interface ResponsiveTableProps<T> {
  data: T[]
  columns: ColumnDef<T>[]
  keyField: keyof T
  emptyState?: React.ReactNode
  className?: string
}

export function ResponsiveTable<T>({
  data,
  columns,
  keyField,
  emptyState,
  className,
}: ResponsiveTableProps<T>) {
  if (data.length === 0) {
    return emptyState ? <>{emptyState}</> : null
  }

  const titleCols = columns.filter((c) => c.cardRole === 'title')
  const subtitleCols = columns.filter((c) => c.cardRole === 'subtitle')
  const badgeCols = columns.filter((c) => c.cardRole === 'badge')
  const detailCols = columns.filter(
    (c) => !c.cardRole || c.cardRole === 'detail'
  )
  const actionCols = columns.filter((c) => c.cardRole === 'action')

  return (
    <div className={className}>
      {/* Desktop table view */}
      <div className="hidden md:block" data-testid="desktop-view">
        <div className="rounded-md border border-border overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                {columns.map((col) => (
                  <TableHead key={col.header} className={col.headerClassName}>
                    {col.header}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((item) => (
                <TableRow key={String(item[keyField])}>
                  {columns.map((col) => (
                    <TableCell key={col.header} className={col.cellClassName}>
                      {col.cell(item)}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* Mobile card view */}
      <div className="md:hidden space-y-3" data-testid="mobile-view">
        {data.map((item) => (
          <div
            key={String(item[keyField])}
            className="rounded-lg border border-border bg-card p-4"
          >
            {/* Title + Badge row */}
            {(titleCols.length > 0 || badgeCols.length > 0) && (
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  {titleCols.map((col) => (
                    <div key={col.header} className="font-medium truncate">
                      {col.cell(item)}
                    </div>
                  ))}
                </div>
                {badgeCols.length > 0 && (
                  <div className="flex flex-wrap items-center gap-1 shrink-0">
                    {badgeCols.map((col) => (
                      <React.Fragment key={col.header}>
                        {col.cell(item)}
                      </React.Fragment>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Subtitle row */}
            {subtitleCols.length > 0 && (
              <div className="mt-1">
                {subtitleCols.map((col) => (
                  <div
                    key={col.header}
                    className="text-sm text-muted-foreground truncate"
                  >
                    {col.cell(item)}
                  </div>
                ))}
              </div>
            )}

            {/* Detail key-value rows */}
            {detailCols.length > 0 && (
              <div
                className={cn(
                  'space-y-1',
                  (titleCols.length > 0 ||
                    subtitleCols.length > 0 ||
                    badgeCols.length > 0) &&
                    'mt-3 border-t border-border pt-3'
                )}
              >
                {detailCols.map((col) => (
                  <div
                    key={col.header}
                    className="flex items-center justify-between gap-2 text-sm"
                  >
                    <span className="text-muted-foreground shrink-0">
                      {col.header}
                    </span>
                    <span className="text-right truncate">{col.cell(item)}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Action row */}
            {actionCols.length > 0 && (
              <div className="mt-3 border-t border-border pt-3 flex items-center gap-1 min-h-11">
                {actionCols.map((col) => (
                  <React.Fragment key={col.header}>
                    {col.cell(item)}
                  </React.Fragment>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
