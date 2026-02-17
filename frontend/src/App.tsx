/**
 * ShutterSense Application
 *
 * Main application component with routing and layout
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { type ReactElement } from 'react'
import {
  LayoutGrid,
  Workflow,
  FolderOpen,
  Archive,
  ChartNoAxesCombined,
  Users,
  Settings,
  GitBranch,
  Calendar,
  BookOpen,
  User,
  Bot,
  Bell,
  Box,
  type LucideIcon
} from 'lucide-react'
import { MainLayout } from './components/layout/MainLayout'
import { ErrorBoundary } from './components/error'
import { AuthProvider } from './contexts/AuthContext'
import { ProtectedRoute } from './components/auth/ProtectedRoute'
import { AuthRedirectHandler } from './components/auth/AuthRedirectHandler'

// Page components
import DashboardPage from './pages/DashboardPage'
import NotFoundPage from './pages/NotFoundPage'
import WorkflowsPage from './pages/WorkflowsPage'
import CollectionsPage from './pages/CollectionsPage'
import AssetsPage from './pages/AssetsPage'
import AnalyticsPage from './pages/AnalyticsPage'
import TeamPage from './pages/TeamPage'
import SettingsPage from './pages/SettingsPage'
import PipelineEditorPage from './pages/PipelineEditorPage'
import ResourcesPage from './pages/ResourcesPage'
import EventsPage from './pages/EventsPage'
import DirectoryPage from './pages/DirectoryPage'
import LoginPage from './pages/LoginPage'
import ProfilePage from './pages/ProfilePage'
import AgentsPage from './pages/AgentsPage'
import AgentDetailPage from './pages/AgentDetailPage'
import NotificationsPage from './pages/NotificationsPage'

// ============================================================================
// Route Configuration
// ============================================================================

interface RouteConfig {
  path: string
  element: ReactElement
  pageTitle: string
  pageIcon?: LucideIcon
  /**
   * Optional help text for the page (Issue #67)
   * When provided, displays a help icon with tooltip in TopHeader
   */
  pageHelp?: string
}

const routes: RouteConfig[] = [
  {
    path: '/',
    element: <DashboardPage />,
    pageTitle: 'Dashboard',
    pageIcon: LayoutGrid,
    pageHelp: 'Overview of collections, analysis trends, queue status, and recent activity',
  },
  {
    path: '/events',
    element: <EventsPage />,
    pageTitle: 'Events',
    pageIcon: Calendar,
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
    path: '/resources',
    element: <ResourcesPage />,
    pageTitle: 'Resources',
    pageIcon: Box,
    pageHelp: 'Manage cameras discovered by agents and photo processing pipelines',
  },
  {
    path: '/directory',
    element: <DirectoryPage />,
    pageTitle: 'Directory',
    pageIcon: BookOpen,
    pageHelp: 'Manage locations, organizers, and performers for your events',
  },
  {
    path: '/settings',
    element: <SettingsPage />,
    pageTitle: 'Settings',
    pageIcon: Settings,
    pageHelp: 'Configure tools, event categories, and storage connectors',
  },
]

// ============================================================================
// Component
// ============================================================================

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <AuthRedirectHandler>
            <Routes>
            {/* Login page - public, no auth required */}
            <Route path="/login" element={<LoginPage />} />

            {/* Protected routes - require authentication */}
            {routes.map(({ path, element, pageTitle, pageIcon, pageHelp }) => (
              <Route
                key={path}
                path={path}
                element={
                  <ProtectedRoute>
                    <MainLayout pageTitle={pageTitle} pageIcon={pageIcon} pageHelp={pageHelp}>
                      {element}
                    </MainLayout>
                  </ProtectedRoute>
                }
              />
            ))}

            {/* Profile page - user profile view */}
            <Route
              path="/profile"
              element={
                <ProtectedRoute>
                  <MainLayout pageTitle="Profile" pageIcon={User}>
                    <ProfilePage />
                  </MainLayout>
                </ProtectedRoute>
              }
            />

            {/* Agents page - NOT in sidebar, accessed via header badge (Issue #90) */}
            <Route
              path="/agents"
              element={
                <ProtectedRoute>
                  <MainLayout pageTitle="Agents" pageIcon={Bot} pageHelp="Manage distributed agents for local photo collection analysis">
                    <AgentsPage />
                  </MainLayout>
                </ProtectedRoute>
              }
            />

            {/* Agent detail page (Issue #90 - Phase 11) */}
            <Route
              path="/agents/:guid"
              element={
                <ProtectedRoute>
                  <MainLayout pageTitle="Agent Details" pageIcon={Bot} pageHelp="View detailed agent information and job history">
                    <AgentDetailPage />
                  </MainLayout>
                </ProtectedRoute>
              }
            />

            {/* Notifications page - NOT in sidebar, accessed via bell popover (Issue #114) */}
            <Route
              path="/notifications"
              element={
                <ProtectedRoute>
                  <MainLayout pageTitle="Notifications" pageIcon={Bell} pageHelp="View and manage all your notifications">
                    <NotificationsPage />
                  </MainLayout>
                </ProtectedRoute>
              }
            />

            {/* Pipeline editor routes - these pages include their own MainLayout */}
            <Route
              path="/pipelines/new"
              element={
                <ProtectedRoute>
                  <PipelineEditorPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/pipelines/:id"
              element={
                <ProtectedRoute>
                  <PipelineEditorPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/pipelines/:id/edit"
              element={
                <ProtectedRoute>
                  <PipelineEditorPage />
                </ProtectedRoute>
              }
            />

            {/* Legacy route redirects (Issue #39 - Navigation restructure) */}
            <Route path="/connectors" element={<Navigate to="/settings?tab=connectors" replace />} />
            <Route path="/config" element={<Navigate to="/settings?tab=config" replace />} />
            {/* Issue #217 - Pipelines moved under Resources page */}
            <Route path="/pipelines" element={<Navigate to="/resources?tab=pipelines" replace />} />

            {/* Catch-all 404 route */}
            <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </AuthRedirectHandler>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  )
}

export default App
