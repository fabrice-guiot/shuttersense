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
  ChartNoAxesCombined,
  Users,
  Plug,
  Settings,
  GitBranch,
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
import PipelinesPage from './pages/PipelinesPage'
import PipelineEditorPage from './pages/PipelineEditorPage'
import ConfigurationPage from './pages/ConfigurationPage'

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
    pageIcon: ChartNoAxesCombined,
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
    path: '/pipelines',
    element: <PipelinesPage />,
    pageTitle: 'Pipelines',
    pageIcon: GitBranch,
  },
  {
    path: '/settings',
    element: <SettingsPage />,
    pageTitle: 'Settings',
    pageIcon: Settings,
  },
  {
    path: '/config',
    element: <ConfigurationPage />,
    pageTitle: 'Configuration',
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
        {/* Pipeline editor routes - these pages include their own MainLayout */}
        <Route path="/pipelines/new" element={<PipelineEditorPage />} />
        <Route path="/pipelines/:id" element={<PipelineEditorPage />} />
        <Route path="/pipelines/:id/edit" element={<PipelineEditorPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
