import * as React from 'react'

import { TabsList } from '@/components/ui/tabs'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

export interface TabOption {
  value: string
  label: string
  icon?: React.ComponentType<{ className?: string }>
  badge?: React.ReactNode
}

export interface ResponsiveTabsListProps {
  tabs: TabOption[]
  value: string
  onValueChange: (value: string) => void
  children: React.ReactNode
}

export function ResponsiveTabsList({
  tabs,
  value,
  onValueChange,
  children,
}: ResponsiveTabsListProps) {
  const selectedTab = tabs.find((t) => t.value === value)

  return (
    <>
      {/* Desktop tab strip */}
      <TabsList className="hidden md:inline-flex">{children}</TabsList>

      {/* Mobile select dropdown */}
      <div className="md:hidden">
        <Select value={value} onValueChange={onValueChange}>
          <SelectTrigger>
            <SelectValue>
              {selectedTab && (
                <span className="flex items-center gap-2">
                  {selectedTab.icon && (
                    <selectedTab.icon className="h-4 w-4" />
                  )}
                  {selectedTab.label}
                </span>
              )}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            {tabs.map((tab) => (
              <SelectItem key={tab.value} value={tab.value}>
                <span className="flex items-center gap-2">
                  {tab.icon && <tab.icon className="h-4 w-4" />}
                  {tab.label}
                  {tab.badge}
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </>
  )
}
