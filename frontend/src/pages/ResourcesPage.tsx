/**
 * Resources Page
 *
 * Consolidates Camera management and Pipeline management under URL-synced tabs.
 * Replaces the standalone PipelinesPage in the sidebar.
 * Follows DirectoryPage.tsx pattern for URL-synchronized tabs.
 *
 * Issue #217 - Pipeline-Driven Analysis Tools (US4).
 */

import { useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Camera, Workflow } from 'lucide-react'
import { Tabs, TabsContent, TabsTrigger } from '@/components/ui/tabs'
import { ResponsiveTabsList, type TabOption } from '@/components/ui/responsive-tabs-list'
import { CamerasTab } from '@/components/cameras/CamerasTab'
import { PipelinesTab } from '@/components/pipelines/PipelinesTab'

// Tab configuration
const TABS = [
  {
    id: 'cameras',
    label: 'Cameras',
    icon: Camera,
  },
  {
    id: 'pipelines',
    label: 'Pipelines',
    icon: Workflow,
  },
] as const

type TabId = typeof TABS[number]['id']

const DEFAULT_TAB: TabId = 'cameras'

export default function ResourcesPage() {
  const [searchParams, setSearchParams] = useSearchParams()

  // Get current tab from URL, default to 'cameras'
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
      <Tabs value={validTab} onValueChange={handleTabChange} className="w-full">
        <ResponsiveTabsList
          tabs={TABS.map((tab): TabOption => ({ value: tab.id, label: tab.label, icon: tab.icon }))}
          value={validTab}
          onValueChange={handleTabChange}
        >
          {TABS.map(tab => {
            const Icon = tab.icon
            return (
              <TabsTrigger key={tab.id} value={tab.id} className="gap-2">
                <Icon className="h-4 w-4" />
                {tab.label}
              </TabsTrigger>
            )
          })}
        </ResponsiveTabsList>

        <TabsContent value="cameras" className="mt-6">
          <CamerasTab />
        </TabsContent>

        <TabsContent value="pipelines" className="mt-6">
          <PipelinesTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
