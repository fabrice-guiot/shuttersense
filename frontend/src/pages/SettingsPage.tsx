/**
 * Settings Page
 *
 * Configure application settings, connectors, and tool configuration.
 * Uses URL-synchronized tabs for deep linking.
 *
 * Issue #39 - Calendar Events feature navigation restructure.
 */

import { useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Settings, Plug, Cog, Tag } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ConnectorsTab } from '@/components/settings/ConnectorsTab'
import { ConfigTab } from '@/components/settings/ConfigTab'
import { CategoriesTab } from '@/components/settings/CategoriesTab'

// Tab configuration - order: Config, Categories, Connectors
const TABS = [
  {
    id: 'config',
    label: 'Configuration',
    icon: Cog,
  },
  {
    id: 'categories',
    label: 'Categories',
    icon: Tag,
  },
  {
    id: 'connectors',
    label: 'Connectors',
    icon: Plug,
  },
] as const

type TabId = typeof TABS[number]['id']

const DEFAULT_TAB: TabId = 'config'

export default function SettingsPage() {
  const [searchParams, setSearchParams] = useSearchParams()

  // Get current tab from URL, default to 'config'
  const currentTab = (searchParams.get('tab') as TabId) || DEFAULT_TAB

  // Validate tab exists
  const validTab = TABS.some(t => t.id === currentTab) ? currentTab : DEFAULT_TAB

  // Sync URL with tab state
  const handleTabChange = (value: string) => {
    setSearchParams({ tab: value }, { replace: true })
  }

  // Set default tab in URL if not present
  useEffect(() => {
    if (!searchParams.has('tab')) {
      setSearchParams({ tab: DEFAULT_TAB }, { replace: true })
    }
  }, [searchParams, setSearchParams])

  return (
    <div className="flex flex-col gap-6">
      {/* Page Header */}
      <div className="flex items-center gap-3">
        <Settings className="h-8 w-8" />
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
          <p className="text-muted-foreground">
            Configure tools, event categories, and storage connectors
          </p>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={validTab} onValueChange={handleTabChange} className="w-full">
        <TabsList>
          {TABS.map(tab => {
            const Icon = tab.icon
            return (
              <TabsTrigger key={tab.id} value={tab.id} className="gap-2">
                <Icon className="h-4 w-4" />
                {tab.label}
              </TabsTrigger>
            )
          })}
        </TabsList>

        <TabsContent value="config" className="mt-6">
          <ConfigTab />
        </TabsContent>

        <TabsContent value="categories" className="mt-6">
          <CategoriesTab />
        </TabsContent>

        <TabsContent value="connectors" className="mt-6">
          <ConnectorsTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
