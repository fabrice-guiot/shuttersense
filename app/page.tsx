"use client"

import { useState, useMemo } from "react"
import { Plus, FolderOpen } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { FiltersSection } from "@/components/collections/filters-section"
import { CollectionList } from "@/components/collections/collection-list"
import type { Collection, CollectionState, CollectionType } from "@/lib/types"

// Mock data for demo
const mockCollections: Collection[] = [
  {
    guid: "col_001",
    name: "Wedding Photos 2024",
    type: "s3",
    state: "live",
    location: "s3://shuttersense-photos/weddings/2024",
    connector_guid: "con_001",
    pipeline_guid: "pip_001",
    pipeline_version: 2,
    pipeline_name: "Standard Analysis",
    is_accessible: true,
    accessibility_message: null,
    cache_ttl: 3600,
    bound_agent: null,
    file_info: {
      count: 15420,
      source: "inventory",
      updated_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
      delta: {
        new_count: 523,
        modified_count: 12,
        deleted_count: 3,
        new_size_bytes: 1024000000,
        modified_size_change_bytes: 50000,
        deleted_size_bytes: 30000,
        total_changes: 538,
        is_first_import: false,
        computed_at: new Date().toISOString(),
      },
    },
    created_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
    last_scanned_at: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
  },
  {
    guid: "col_002",
    name: "Studio Portraits",
    type: "local",
    state: "live",
    location: "/mnt/studio/portraits",
    connector_guid: null,
    pipeline_guid: null,
    pipeline_version: null,
    pipeline_name: null,
    is_accessible: true,
    accessibility_message: null,
    cache_ttl: null,
    bound_agent: {
      guid: "agt_001",
      name: "Studio-PC-01",
      status: "online",
    },
    file_info: null,
    created_at: new Date(Date.now() - 60 * 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    last_scanned_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    guid: "col_003",
    name: "Event Photography Archive",
    type: "gcs",
    state: "archived",
    location: "gs://shuttersense-archive/events/2023",
    connector_guid: "con_002",
    pipeline_guid: "pip_002",
    pipeline_version: 1,
    pipeline_name: "Archive Pipeline",
    is_accessible: false,
    accessibility_message: "Bucket access denied. Check IAM permissions.",
    cache_ttl: 86400,
    bound_agent: null,
    file_info: {
      count: 45230,
      source: "api",
      updated_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
      delta: null,
    },
    created_at: new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
    last_scanned_at: null,
  },
  {
    guid: "col_004",
    name: "Corporate Headshots",
    type: "smb",
    state: "closed",
    location: "\\\\nas-01\\photos\\corporate",
    connector_guid: "con_003",
    pipeline_guid: null,
    pipeline_version: null,
    pipeline_name: null,
    is_accessible: null,
    accessibility_message: null,
    cache_ttl: 7200,
    bound_agent: null,
    file_info: null,
    created_at: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString(),
    last_scanned_at: null,
  },
  {
    guid: "col_005",
    name: "Nature Photography",
    type: "s3",
    state: "live",
    location: "s3://shuttersense-photos/nature",
    connector_guid: "con_001",
    pipeline_guid: "pip_003",
    pipeline_version: 3,
    pipeline_name: "Nature AI Analysis",
    is_accessible: true,
    accessibility_message: null,
    cache_ttl: 3600,
    bound_agent: null,
    file_info: {
      count: 8750,
      source: "inventory",
      updated_at: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
      delta: {
        new_count: 0,
        modified_count: 0,
        deleted_count: 25,
        new_size_bytes: 0,
        modified_size_change_bytes: 0,
        deleted_size_bytes: 125000000,
        total_changes: 25,
        is_first_import: false,
        computed_at: new Date().toISOString(),
      },
    },
    created_at: new Date(Date.now() - 45 * 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
    last_scanned_at: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
  },
]

export default function CollectionsPage() {
  const [collections] = useState<Collection[]>(mockCollections)
  const [search, setSearch] = useState("")
  const [selectedState, setSelectedState] = useState<CollectionState | "ALL" | "">("ALL")
  const [selectedType, setSelectedType] = useState<CollectionType | "ALL" | "">("ALL")
  const [accessibleOnly, setAccessibleOnly] = useState(false)

  // Filter collections based on search and filters
  const filteredCollections = useMemo(() => {
    return collections.filter((col) => {
      // Search filter
      if (search && !col.name.toLowerCase().includes(search.toLowerCase())) {
        return false
      }
      // State filter
      if (selectedState && selectedState !== "ALL" && col.state !== selectedState) {
        return false
      }
      // Type filter
      if (selectedType && selectedType !== "ALL" && col.type !== selectedType) {
        return false
      }
      // Accessible only filter
      if (accessibleOnly && col.is_accessible !== true) {
        return false
      }
      return true
    })
  }, [collections, search, selectedState, selectedType, accessibleOnly])

  const handleEdit = (collection: Collection) => {
    toast.info(`Edit: ${collection.name}`, { description: `GUID: ${collection.guid}` })
  }

  const handleDelete = (collection: Collection) => {
    toast.error(`Delete: ${collection.name}`, { description: "This is a demo - no actual deletion" })
  }

  const handleInfo = (collection: Collection) => {
    toast.loading("Testing accessibility...", { description: collection.name })
    setTimeout(() => {
      toast.success("Accessibility test complete", { description: collection.name })
    }, 1500)
  }

  const handleRefresh = (collection: Collection) => {
    toast.loading("Starting analysis...", { description: collection.name })
    setTimeout(() => {
      toast.success("Analysis complete", { description: collection.name })
    }, 2000)
  }

  const handleRefreshFromCloud = (collection: Collection) => {
    toast.loading("Refreshing from cloud storage...", { description: collection.name })
    setTimeout(() => {
      toast.success("Cloud refresh complete", { description: collection.name })
    }, 2500)
  }

  const handleNewCollection = () => {
    toast.info("New Collection dialog would open here")
  }

  return (
    <main className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <FolderOpen className="h-6 w-6 text-primary" />
              <h1 className="text-xl font-semibold">Collections</h1>
            </div>
            <div className="flex items-center gap-4">
              <div className="hidden sm:flex items-center gap-6 text-sm text-muted-foreground">
                <div>
                  <span className="font-medium text-foreground">{collections.length}</span> Total
                </div>
                <div>
                  <span className="font-medium text-foreground">69,400</span> Files
                </div>
                <div>
                  <span className="font-medium text-foreground">2.4 TB</span> Storage
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-6">
        <div className="flex flex-col gap-6">
          {/* Action Row */}
          <div className="flex justify-end">
            <Button onClick={handleNewCollection} className="gap-2">
              <Plus className="h-4 w-4" />
              New Collection
            </Button>
          </div>

          {/* Filters Section */}
          <FiltersSection
            selectedState={selectedState}
            setSelectedState={setSelectedState}
            selectedType={selectedType}
            setSelectedType={setSelectedType}
            accessibleOnly={accessibleOnly}
            setAccessibleOnly={setAccessibleOnly}
            search={search}
            onSearchChange={setSearch}
          />

          {/* Collection List */}
          <CollectionList
            collections={filteredCollections}
            loading={false}
            onEdit={handleEdit}
            onDelete={handleDelete}
            onInfo={handleInfo}
            onRefresh={handleRefresh}
            onRefreshFromCloud={handleRefreshFromCloud}
            search={search}
          />
        </div>
      </div>
    </main>
  )
}
