"use client"

import { useState } from "react"
import { Plus } from "lucide-react"
import { CollectionsTable } from "./collections-table"
import { FiltersSection } from "./filters-section"

export function CollectionsPage() {
  const [selectedState, setSelectedState] = useState("")
  const [selectedType, setSelectedType] = useState("")
  const [accessibleOnly, setAccessibleOnly] = useState(false)
  const [activeTab, setActiveTab] = useState("all")

  return (
    <div className="flex-1 flex flex-col">
      {/* Content Area */}
      <div className="flex-1 overflow-auto">
        <div className="p-8">
          {/* Page Header with Tabs */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-3xl font-semibold text-foreground">Collections</h2>
              <button className="bg-primary text-primary-foreground px-4 py-2 rounded-lg font-medium text-sm hover:bg-primary/90 flex items-center gap-2 transition-colors">
                <Plus className="w-5 h-5" />
                NEW COLLECTION
              </button>
            </div>

            {/* Tabs */}
            <div className="flex gap-8 border-b border-border">
              {[
                { id: "all", label: "All Collections" },
                { id: "recent", label: "Recently Accessed" },
                { id: "archived", label: "Archived" },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`pb-3 text-sm font-medium transition-colors ${
                    activeTab === tab.id
                      ? "text-primary border-b-2 border-primary"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* Filters */}
          <div className="mb-6">
            <FiltersSection
              selectedState={selectedState}
              setSelectedState={setSelectedState}
              selectedType={selectedType}
              setSelectedType={setSelectedType}
              accessibleOnly={accessibleOnly}
              setAccessibleOnly={setAccessibleOnly}
            />
          </div>

          {/* Table */}
          <div className="rounded-lg border border-border overflow-hidden bg-card">
            <CollectionsTable
              selectedState={selectedState}
              selectedType={selectedType}
              accessibleOnly={accessibleOnly}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
