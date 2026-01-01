"use client"

import { Bell, ChevronDown, BarChart3 } from "lucide-react"

export function TopHeader() {
  return (
    <div className="h-16 bg-card border-b border-border flex items-center justify-between px-8">
      {/* Left Section */}
      <div className="flex items-center gap-2">
        <BarChart3 className="w-5 h-5 text-primary" />
        <h1 className="text-xl font-semibold text-foreground">Photo Collections</h1>
      </div>

      {/* Right Section */}
      <div className="flex items-center gap-6">
        {/* Stats */}
        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="text-xs text-muted-foreground">Collections</div>
            <div className="text-lg font-semibold text-foreground">42</div>
          </div>
          <div className="w-px h-6 bg-border" />
          <div className="text-right">
            <div className="text-xs text-muted-foreground">Storage</div>
            <div className="text-lg font-semibold text-foreground">1.2 TB</div>
          </div>
        </div>

        {/* Divider */}
        <div className="w-px h-6 bg-border" />

        {/* Notifications and Profile */}
        <div className="flex items-center gap-4">
          <button className="p-2 hover:bg-secondary rounded-lg transition-colors">
            <Bell className="w-5 h-5 text-foreground/70" />
          </button>
          <button className="flex items-center gap-2 px-3 py-2 hover:bg-secondary rounded-lg transition-colors">
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-sm font-semibold">
              JD
            </div>
            <ChevronDown className="w-4 h-4 text-foreground/70" />
          </button>
        </div>
      </div>
    </div>
  )
}
