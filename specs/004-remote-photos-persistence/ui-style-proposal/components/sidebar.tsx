"use client"

import { LayoutGrid, Archive, BarChart3, Users, Settings, Workflow, FolderOpen } from "lucide-react"

const menuItems = [
  { icon: LayoutGrid, label: "Dashboard", href: "#" },
  { icon: Workflow, label: "Workflows", href: "#" },
  { icon: FolderOpen, label: "Collections", href: "#", active: true },
  { icon: Archive, label: "Assets", href: "#" },
  { icon: BarChart3, label: "Analytics", href: "#" },
  { icon: Users, label: "Team", href: "#" },
  { icon: Settings, label: "Settings", href: "#" },
]

export function Sidebar() {
  return (
    <div className="w-56 bg-sidebar border-r border-sidebar-border flex flex-col">
      {/* Logo and Org Info */}
      <div className="p-6 border-b border-sidebar-border">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-sidebar-primary flex items-center justify-center text-sidebar-primary-foreground font-semibold">
            PA
          </div>
          <div className="flex-1">
            <div className="text-sm font-semibold text-sidebar-foreground">Photo Admin</div>
            <div className="text-xs text-sidebar-foreground/60">Organization</div>
          </div>
        </div>
      </div>

      {/* Navigation Menu */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {menuItems.map((item) => (
          <a
            key={item.label}
            href={item.href}
            className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
              item.active
                ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
            }`}
          >
            <item.icon className="w-4 h-4" />
            <span>{item.label}</span>
          </a>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-sidebar-border">
        <div className="text-xs text-sidebar-foreground/60">Photo Admin v1.0</div>
      </div>
    </div>
  )
}
