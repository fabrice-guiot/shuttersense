"use client"

import { Info, RefreshCw, Edit, Trash2 } from "lucide-react"

interface Collection {
  id: string
  name: string
  type: string
  state: string
  location: string
  status: "accessible" | "restricted"
}

const MOCK_COLLECTIONS: Collection[] = [
  {
    id: "1",
    name: "Test Collection for Photo Admin Tool (Chaplainville)",
    type: "Local",
    state: "Live",
    location: "/Volumes/T9-3/BKP/Chaplainville/",
    status: "accessible",
  },
]

interface CollectionsTableProps {
  selectedState: string
  selectedType: string
  accessibleOnly: boolean
}

export function CollectionsTable({ selectedState, selectedType, accessibleOnly }: CollectionsTableProps) {
  const filteredCollections = MOCK_COLLECTIONS.filter((collection) => {
    if (selectedState && collection.state.toLowerCase() !== selectedState.toLowerCase()) {
      return false
    }
    if (selectedType && collection.type.toLowerCase() !== selectedType.toLowerCase()) {
      return false
    }
    if (accessibleOnly && collection.status !== "accessible") {
      return false
    }
    return true
  })

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-border bg-secondary/50">
            <th className="text-left px-6 py-4 font-medium text-foreground text-sm">Name</th>
            <th className="text-left px-6 py-4 font-medium text-foreground text-sm">Type</th>
            <th className="text-left px-6 py-4 font-medium text-foreground text-sm">State</th>
            <th className="text-left px-6 py-4 font-medium text-foreground text-sm">Location</th>
            <th className="text-left px-6 py-4 font-medium text-foreground text-sm">Status</th>
            <th className="text-left px-6 py-4 font-medium text-foreground text-sm">Actions</th>
          </tr>
        </thead>
        <tbody>
          {filteredCollections.map((collection) => (
            <tr key={collection.id} className="border-b border-border hover:bg-secondary/30 transition-colors">
              <td className="px-6 py-4 text-sm text-foreground">{collection.name}</td>
              <td className="px-6 py-4 text-sm">
                <span className="bg-muted text-muted-foreground px-3 py-1 rounded-full text-xs font-medium">
                  {collection.type}
                </span>
              </td>
              <td className="px-6 py-4 text-sm">
                <span className="bg-primary text-primary-foreground px-3 py-1 rounded-full text-xs font-medium">
                  {collection.state}
                </span>
              </td>
              <td className="px-6 py-4 text-sm text-muted-foreground">{collection.location}</td>
              <td className="px-6 py-4 text-sm">
                <span className="bg-green-900/30 text-green-400 px-3 py-1 rounded-full text-xs font-medium flex items-center gap-1 w-fit">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                  {collection.status.charAt(0).toUpperCase() + collection.status.slice(1)}
                </span>
              </td>
              <td className="px-6 py-4 text-sm">
                <div className="flex items-center gap-2">
                  <button
                    className="p-2 hover:bg-secondary rounded-lg transition-colors text-muted-foreground hover:text-foreground"
                    title="Info"
                  >
                    <Info className="w-4 h-4" />
                  </button>
                  <button
                    className="p-2 hover:bg-secondary rounded-lg transition-colors text-muted-foreground hover:text-foreground"
                    title="Refresh"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>
                  <button
                    className="p-2 hover:bg-secondary rounded-lg transition-colors text-muted-foreground hover:text-foreground"
                    title="Edit"
                  >
                    <Edit className="w-4 h-4" />
                  </button>
                  <button
                    className="p-2 hover:bg-secondary rounded-lg transition-colors text-muted-foreground hover:text-foreground"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
