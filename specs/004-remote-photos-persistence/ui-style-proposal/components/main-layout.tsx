"use client"

import type React from "react"

import { Sidebar } from "./sidebar"
import { TopHeader } from "./top-header"

export function MainLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <TopHeader />
        <main className="flex-1 overflow-auto">{children}</main>
      </div>
    </div>
  )
}
