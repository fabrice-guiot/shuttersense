/**
 * Directory Page
 *
 * Manage event-related entities: Locations, Organizers, Performers.
 * Uses URL-synchronized tabs for deep linking.
 *
 * Issue #39 - Calendar Events feature.
 */

import { useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { BookOpen, MapPin, Building2, Users } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { LocationsTab } from '@/components/directory/LocationsTab'
import { OrganizersTab } from '@/components/directory/OrganizersTab'
import { PerformersTab } from '@/components/directory/PerformersTab'
import { useCategories } from '@/hooks/useCategories'

// Tab configuration
const TABS = [
  {
    id: 'locations',
    label: 'Locations',
    icon: MapPin,
  },
  {
    id: 'organizers',
    label: 'Organizers',
    icon: Building2,
  },
  {
    id: 'performers',
    label: 'Performers',
    icon: Users,
  },
] as const

type TabId = typeof TABS[number]['id']

const DEFAULT_TAB: TabId = 'locations'

export default function DirectoryPage() {
  const [searchParams, setSearchParams] = useSearchParams()

  // Fetch categories for LocationsTab
  const { categories } = useCategories()

  // Get current tab from URL, default to 'locations'
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
        <BookOpen className="h-8 w-8" />
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Directory</h1>
          <p className="text-muted-foreground">
            Manage event locations, organizers, and performers
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

        <TabsContent value="locations" className="mt-6">
          <LocationsTab categories={categories} />
        </TabsContent>

        <TabsContent value="organizers" className="mt-6">
          <OrganizersTab categories={categories} />
        </TabsContent>

        <TabsContent value="performers" className="mt-6">
          <PerformersTab categories={categories} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
