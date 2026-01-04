/**
 * Photo Admin Application
 *
 * Main application component with routing and layout
 */

import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { type ReactElement } from 'react'
import {
  LayoutGrid,
  Workflow,
  FolderOpen,
  Archive,
  BarChart3,
  Users,
  Plug,
  Settings,
  Wrench,
  FileText,
  type LucideIcon
} from 'lucide-react'
import { MainLayout } from './components/layout/MainLayout'

// Page components
import DashboardPage from './pages/DashboardPage'
import WorkflowsPage from './pages/WorkflowsPage'
import CollectionsPage from './pages/CollectionsPage'
import AssetsPage from './pages/AssetsPage'
import AnalyticsPage from './pages/AnalyticsPage'
import TeamPage from './pages/TeamPage'
import ConnectorsPage from './pages/ConnectorsPage'
import SettingsPage from './pages/SettingsPage'
import ToolsPage from './pages/ToolsPage'
import ResultsPage from './pages/ResultsPage'

// ============================================================================
// Route Configuration
// ============================================================================

interface RouteConfig {
  path: string
  element: ReactElement
  pageTitle: string
  pageIcon?: LucideIcon
}

const routes: RouteConfig[] = [
  {
    path: '/',
    element: <DashboardPage />,
    pageTitle: 'Dashboard',
    pageIcon: LayoutGrid,
  },
  {
    path: '/workflows',
    element: <WorkflowsPage />,
    pageTitle: 'Workflows',
    pageIcon: Workflow,
  },
  {
    path: '/collections',
    element: <CollectionsPage />,
    pageTitle: 'Collections',
    pageIcon: FolderOpen,
  },
  {
    path: '/assets',
    element: <AssetsPage />,
    pageTitle: 'Assets',
    pageIcon: Archive,
  },
  {
    path: '/analytics',
    element: <AnalyticsPage />,
    pageTitle: 'Analytics',
    pageIcon: BarChart3,
  },
  {
    path: '/team',
    element: <TeamPage />,
    pageTitle: 'Team',
    pageIcon: Users,
  },
  {
    path: '/connectors',
    element: <ConnectorsPage />,
    pageTitle: 'Connectors',
    pageIcon: Plug,
  },
  {
    path: '/tools',
    element: <ToolsPage />,
    pageTitle: 'Tools',
    pageIcon: Wrench,
  },
  {
    path: '/results',
    element: <ResultsPage />,
    pageTitle: 'Results',
    pageIcon: FileText,
  },
  {
    path: '/settings',
    element: <SettingsPage />,
    pageTitle: 'Settings',
    pageIcon: Settings,
  },
]

// ============================================================================
// Component
// ============================================================================

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {routes.map(({ path, element, pageTitle, pageIcon }) => (
          <Route
            key={path}
            path={path}
            element={
              <MainLayout pageTitle={pageTitle} pageIcon={pageIcon}>
                {element}
              </MainLayout>
            }
          />
        ))}
      </Routes>
    </BrowserRouter>
  )
}

export default App
