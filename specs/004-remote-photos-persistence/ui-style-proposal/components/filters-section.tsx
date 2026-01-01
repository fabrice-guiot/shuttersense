"use client"

import { Search } from "lucide-react"

interface FiltersSectionProps {
  selectedState: string
  setSelectedState: (value: string) => void
  selectedType: string
  setSelectedType: (value: string) => void
  accessibleOnly: boolean
  setAccessibleOnly: (value: boolean) => void
}

export function FiltersSection({
  selectedState,
  setSelectedState,
  selectedType,
  setSelectedType,
  accessibleOnly,
  setAccessibleOnly,
}: FiltersSectionProps) {
  return (
    <div className="flex items-center gap-4">
      {/* Search */}
      <div className="flex-1 max-w-xs relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search collections..."
          className="w-full bg-secondary border border-border rounded-lg pl-10 pr-4 py-2 text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
        />
      </div>

      <select
        value={selectedState}
        onChange={(e) => setSelectedState(e.target.value)}
        className="bg-secondary border border-border rounded-lg px-4 py-2 text-sm text-foreground min-w-[150px] focus:outline-none focus:ring-2 focus:ring-primary"
      >
        <option value="">State</option>
        <option value="live">Live</option>
        <option value="archived">Archived</option>
      </select>

      <select
        value={selectedType}
        onChange={(e) => setSelectedType(e.target.value)}
        className="bg-secondary border border-border rounded-lg px-4 py-2 text-sm text-foreground min-w-[150px] focus:outline-none focus:ring-2 focus:ring-primary"
      >
        <option value="">Type</option>
        <option value="local">Local</option>
        <option value="remote">Remote</option>
      </select>

      <label className="flex items-center gap-2 cursor-pointer text-sm text-foreground">
        <input
          type="checkbox"
          checked={accessibleOnly}
          onChange={(e) => setAccessibleOnly(e.target.checked)}
          className="w-4 h-4 rounded border border-border bg-secondary text-primary focus:ring-2 focus:ring-primary"
        />
        <span>Accessible Only</span>
      </label>
    </div>
  )
}
