/**
 * Settings Page
 *
 * Configure application settings, connectors, and tool configuration.
 * Uses URL-synchronized tabs for deep linking.
 *
 * Issue #39 - Calendar Events feature navigation restructure.
 */

import { useEffect, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Plug, Cog, Tag, Key, Building2 } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { ConnectorsTab } from '@/components/settings/ConnectorsTab'
import { ConfigTab } from '@/components/settings/ConfigTab'
import { CategoriesTab } from '@/components/settings/CategoriesTab'
import { TokensTab } from '@/components/settings/TokensTab'
import { TeamsTab } from '@/components/settings/TeamsTab'
import { useIsSuperAdmin } from '@/hooks/useAuth'

// Base tab configuration - order: Config, Categories, Connectors, Tokens
const BASE_TABS = [
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
  {
    id: 'tokens',
    label: 'API Tokens',
    icon: Key,
  },
] as const

// Super admin only tab
const TEAMS_TAB = {
  id: 'teams',
  label: 'Teams',
  icon: Building2,
  superAdminOnly: true,
} as const

type TabId = 'config' | 'categories' | 'connectors' | 'tokens' | 'teams'

const DEFAULT_TAB: TabId = 'config'

export default function SettingsPage() {
  const isSuperAdmin = useIsSuperAdmin()

  // Build tabs list - include Teams tab for super admins
  const tabs = useMemo(() => {
    const allTabs: Array<{
      id: TabId
      label: string
      icon: typeof Cog
      superAdminOnly?: boolean
    }> = [...BASE_TABS]
    if (isSuperAdmin) {
      allTabs.push(TEAMS_TAB)
    }
    return allTabs
  }, [isSuperAdmin])

  const [searchParams, setSearchParams] = useSearchParams()

  // Get current tab from URL, default to 'config'
  const currentTab = (searchParams.get('tab') as TabId) || DEFAULT_TAB

  // Validate tab exists (must be in the current tabs list)
  const validTab = tabs.some(t => t.id === currentTab) ? currentTab : DEFAULT_TAB

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
      {/* Tabs (Issue #67 - Single Title Pattern: title moved to TopHeader, description to pageHelp) */}
      <Tabs value={validTab} onValueChange={handleTabChange} className="w-full">
        <TabsList>
          {tabs.map(tab => {
            const Icon = tab.icon
            return (
              <TabsTrigger key={tab.id} value={tab.id} className="gap-2">
                <Icon className="h-4 w-4" />
                {tab.label}
                {tab.superAdminOnly && (
                  <Badge variant="secondary" className="ml-1 text-xs py-0 px-1.5">
                    Admin
                  </Badge>
                )}
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

        <TabsContent value="tokens" className="mt-6">
          <TokensTab />
        </TabsContent>

        {isSuperAdmin && (
          <TabsContent value="teams" className="mt-6">
            <TeamsTab />
          </TabsContent>
        )}
      </Tabs>
    </div>
  )
}
