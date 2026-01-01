# Frontend UI Migration Plan

**Branch**: `004-remote-photos-persistence` → `claude/evaluate-frontend-redesign-IR2tj`
**Created**: 2026-01-01
**Status**: Proposed
**Decision**: Migrate NOW (before Phase 4-7 implementation)

---

## Executive Summary

This document outlines the strategic plan to migrate the Photo Admin frontend from Material-UI to shadcn/ui with Tailwind CSS. The migration is recommended **NOW** (after Phase 3, before Phase 4-7) to minimize scope and establish a modern foundation for future development.

### Key Metrics

- **Current Scope**: 11 components, 2 pages, 2 hooks (Phase 3 only)
- **Migration Effort**: 95 hours (3 weeks for 1 developer)
- **Cost Avoidance**: 185-255 hours saved vs migrating after Phase 4-7
- **Future Phases**: 64 frontend tasks will inherit modern stack

---

## Strategic Analysis

### Current Situation

**Completed (Phase 3):**
- ✅ Connector management UI (List, Form, Test connection)
- ✅ Collection management UI (List, Form, Filters, Status badges)
- ✅ Basic navigation and routing
- ✅ Custom hooks (useConnectors, useCollections)
- ✅ ~30 frontend tasks completed

**Remaining (Phases 4-7):**
- 🔲 Phase 4: Tool execution UI, WebSocket progress monitors, Results viewer (~24 tasks)
- 🔲 Phase 5: Pipeline form editor, Node editor, Visual graph builder (~17 tasks)
- 🔲 Phase 6: Trend charts, Multi-collection comparison (~8 tasks)
- 🔲 Phase 7: Config editor, Conflict resolution UI (~15 tasks)
- **Total: ~64 frontend tasks ahead**

---

## Migration Scope Comparison

### Option A: Migrate NOW ✅ RECOMMENDED

**Components to Migrate:**
- 2 pages (ConnectorsPage, CollectionsPage)
- 6 components (ConnectorList, ConnectorForm, CollectionList, CollectionForm, CollectionStatus)
- 2 custom hooks
- App.jsx navigation
- ~11 test files

**Effort Estimate:**
- Styling migration: 20-25 hours
- Component replacement: 25-30 hours
- TypeScript conversion: 15-20 hours
- Test updates: 15-20 hours
- **Total: 75-95 hours (2-3 weeks)**

**Future Benefits:**
- ✅ Phases 4-7 built on modern stack from day one
- ✅ No migration needed for 64 future tasks
- ✅ Team learns with simple components first

---

### Option B: Migrate After Phase 4-7 ❌ NOT RECOMMENDED

**Components to Migrate:**
- 7 pages (all current + 5 new pages)
- 25+ components (current + ProgressMonitor, ToolSelector, ResultList, ReportViewer, PipelineFormEditor, NodeEditor, TrendChart, ConflictResolver, etc.)
- 8+ custom hooks
- WebSocket integration layer
- Recharts integration
- ~42 test files

**Effort Estimate:**
- Styling migration: 80-100 hours
- Component replacement: 100-120 hours
- TypeScript conversion: 40-50 hours
- Test updates: 60-80 hours
- **Total: 280-350 hours (7-9 weeks)**

**Risk Factors:**
- ❌ Team builds muscle memory with MUI that becomes obsolete
- ❌ More complex components (visual editors, WebSocket)
- ❌ Higher risk of bugs during large refactor
- ❌ Delays future features by 2+ months

---

## Recommended Approach: Hybrid Migration

### What We Keep

- ✅ **React 18.3.1** (no framework change to Next.js)
- ✅ **Vite** (fast, familiar build tool)
- ✅ **React Router DOM** (existing routing structure)
- ✅ **Axios** (API layer)
- ✅ **Vitest + React Testing Library** (test infrastructure)
- ✅ **Existing hooks pattern** (state management)

### What We Change

- 🔄 **Material-UI** → **shadcn/ui + Radix UI**
- 🔄 **Emotion/CSS-in-JS** → **Tailwind CSS**
- 🔄 **JavaScript** → **TypeScript**
- 🔄 **MUI theme** → **Dark theme design system** (from ui-style-proposal)
- 🔄 **Simple navigation** → **Sidebar + TopHeader layout**

### Why Hybrid (Not Full Next.js)?

1. **Faster Migration**: 3 weeks vs 6-8 weeks
2. **Lower Risk**: Keep familiar React patterns
3. **Progressive Enhancement**: Can migrate to Next.js later if needed
4. **Immediate Value**: Get modern UI without framework rewrite
5. **Team Velocity**: Less learning curve, focus on design system

---

## Migration Task Breakdown

### PHASE 0: Setup & Infrastructure (Week 1, Days 1-2)

**Duration**: 8 hours
**Goal**: Install and configure Tailwind CSS, shadcn/ui, TypeScript

#### Tasks

**T-001** [2h] Install and configure Tailwind CSS v4
- Install: `npm install -D tailwindcss @tailwindcss/postcss autoprefixer`
- Create `tailwind.config.js` with design tokens
- Create `postcss.config.js`
- Update `frontend/src/index.css` with Tailwind directives

**T-002** [1h] Initialize shadcn/ui
- Run: `npx shadcn@latest init`
- Configure component paths, utils, CSS variables
- Create `frontend/components.json` configuration
- Choose "New York" style for modern aesthetic

**T-003** [2h] Set up design system CSS variables
- Create `frontend/src/globals.css` with dark theme (from ui-style-proposal)
- Define color scheme: `--background`, `--foreground`, `--primary`, `--accent`, etc.
- Add sidebar-specific variables: `--sidebar`, `--sidebar-primary`, etc.
- Configure border radius and spacing tokens

**T-004** [1h] Install required shadcn/ui components
```bash
npx shadcn@latest add button input label select table badge dialog
npx shadcn@latest add dropdown-menu checkbox form alert-dialog
npx shadcn@latest add tooltip separator scroll-area
```

**T-005** [2h] Configure TypeScript
- Install: `npm install -D typescript @types/react @types/react-dom`
- Create `tsconfig.json` with path aliases (`@/components`, `@/lib`)
- Update `vite.config.ts` to support TypeScript and path resolution
- Configure module resolution for shadcn components

**Checkpoint**: ✅ Build passes, Tailwind works, shadcn components available

---

### PHASE 1: Layout Migration (Week 1, Days 3-5)

**Duration**: 15 hours
**Goal**: Replace MUI AppBar with Sidebar + TopHeader layout

#### Tasks

**T-006** [3h] Build Sidebar component
- Create `frontend/src/components/layout/Sidebar.tsx`
- Implement navigation menu items:
  - Dashboard (icon: LayoutGrid)
  - Workflows (icon: Workflow)
  - Collections (icon: FolderOpen) - active
  - Assets (icon: Archive)
  - Analytics (icon: BarChart3)
  - Team (icon: Users)
  - Settings (icon: Settings)
- Add organization branding section (PA logo + "Photo Admin")
- Implement active state highlighting with `bg-sidebar-accent`
- Add footer with version number
- Use Lucide icons for all menu items

**T-007** [2h] Build TopHeader component
- Create `frontend/src/components/layout/TopHeader.tsx`
- Add left section: Page icon + title
- Add right section stats:
  - Collections count (e.g., "42")
  - Storage usage (e.g., "1.2 TB")
- Add notifications bell icon
- Add user profile dropdown with avatar (initials)
- Style with card background and border

**T-008** [2h] Build MainLayout component
- Create `frontend/src/components/layout/MainLayout.tsx`
- Compose: `<Sidebar />` + `<TopHeader />` + content area
- Use flex layout: sidebar fixed width (14rem), header full width, scrollable content
- Add proper overflow handling for content area
- Handle responsive collapse for mobile (optional for v1)

**T-009** [3h] Update App.tsx
- Rename `frontend/src/App.jsx` → `App.tsx`
- Remove MUI imports (`AppBar`, `Toolbar`, `Container`, etc.)
- Wrap routes with `<MainLayout>`
- Update navigation structure to highlight active route
- Add TypeScript route types
- Remove MUI theme provider

**T-010** [2h] Create shared UI utilities
- Create `frontend/src/lib/utils.ts`
- Add `cn()` helper function (combines `clsx` + `tailwind-merge`)
- Install: `npm install clsx tailwind-merge`
- Create common class name utilities for consistent styling

**T-011** [3h] Update navigation state
- Add active route detection using `useLocation()` from React Router
- Highlight active menu item in Sidebar
- Update page titles in TopHeader dynamically
- Add keyboard shortcuts for navigation (optional)
- Test route transitions

**Checkpoint**: ✅ New layout renders, navigation works, responsive design functional

---

### PHASE 2: Connectors Page Migration (Week 2, Days 1-3)

**Duration**: 18 hours
**Goal**: Migrate all Connector-related components to shadcn/ui + Tailwind

#### Tasks

**T-012** [4h] Migrate ConnectorList component
- Rename: `frontend/src/components/connectors/ConnectorList.jsx` → `.tsx`
- **Replace components:**
  - `<Table>` (MUI) → `<Table>` (shadcn/ui from `@/components/ui/table`)
  - `<Chip>` → `<Badge variant="secondary">`
  - `<IconButton>` → `<Button variant="ghost" size="icon">`
  - `<Tooltip>` → `<Tooltip>` (shadcn)
  - `<Select>` → `<Select>` (shadcn)
  - `<Checkbox>` → `<Checkbox>` (shadcn)
- **Styling changes:**
  - Remove all `sx` props
  - Add Tailwind classes: `hover:bg-secondary/30`, `border-border`, etc.
  - Style table rows with hover effects
  - Update badge colors to match design system
- **TypeScript:**
  - Create `frontend/src/types/connector.ts`
  - Define `Connector`, `ConnectorType`, `ConnectorResponse` interfaces
  - Type all props and state
- **Filters:**
  - Implement type filter with shadcn Select
  - Implement active-only filter with shadcn Checkbox
  - Style filters section with flex layout

**T-013** [5h] Migrate ConnectorForm component
- Rename: `frontend/src/components/connectors/ConnectorForm.jsx` → `.tsx`
- **Replace form system:**
  - Remove MUI form components entirely
  - Install: `npm install react-hook-form zod @hookform/resolvers`
  - Use shadcn `<Form>` with `react-hook-form`
  - Implement field validation with Zod schemas
- **Dynamic credential fields:**
  - S3: `<Input>` fields for `access_key_id`, `secret_access_key`, `region`
  - GCS: `<Textarea>` for `service_account_json`
  - SMB: `<Input>` fields for `server`, `share`, `username`, `password` (type="password")
- **Validation schemas:**
  - Create S3CredentialsSchema (Zod): validate AWS key format, region enum
  - Create GCSCredentialsSchema: validate JSON format
  - Create SMBCredentialsSchema: validate required fields
- **Test connection button:**
  - Add loading state with spinner
  - Show success/error feedback with shadcn Toast
  - Style with `variant="secondary"`
- **TypeScript:**
  - Type all form fields
  - Type credentials union type
  - Type form submission handler

**T-014** [3h] Migrate ConnectorsPage
- Rename: `frontend/src/pages/ConnectorsPage.jsx` → `.tsx`
- **Replace components:**
  - `<Dialog>` (MUI) → `<Dialog>` (shadcn)
  - `<Button>` (MUI) → `<Button>` (shadcn)
  - Remove `<Box>`, `<Typography>` (use semantic HTML + Tailwind)
- **Page header:**
  - Add page title: "Connectors" (text-3xl font-semibold)
  - Add "NEW CONNECTOR" button with Plus icon (lucide-react)
  - Style with flex justify-between
- **Delete confirmation:**
  - Replace MUI Dialog → shadcn `<AlertDialog>`
  - Show warning if collections reference connector
  - Style destructive action with `variant="destructive"`
- **TypeScript:**
  - Type page state (open, editingConnector, formError)
  - Type all event handlers

**T-015** [3h] Update useConnectors hook with TypeScript
- Rename: `frontend/src/hooks/useConnectors.js` → `.ts`
- **TypeScript changes:**
  - Import types from `@/types/connector`
  - Type return value: `{ connectors: Connector[], loading: boolean, error: string | null, ... }`
  - Type all API call responses
  - Type error handling
- **No functional changes** - only type annotations

**T-016** [3h] Update connectors service with TypeScript
- Rename: `frontend/src/services/connectors.js` → `.ts`
- **TypeScript changes:**
  - Type axios responses: `AxiosResponse<ConnectorResponse>`
  - Type all function parameters
  - Type error responses
- **Update types file:**
  - Add `ConnectorCreate`, `ConnectorUpdate` interfaces
  - Add `ConnectorTestResponse` interface
  - Export all from `@/types/connector`

**Checkpoint**: ✅ Connectors page fully migrated, tests pass, TypeScript compiles

---

### PHASE 3: Collections Page Migration (Week 2, Days 4-5 + Week 3, Day 1)

**Duration**: 18 hours
**Goal**: Migrate all Collection-related components to shadcn/ui + Tailwind

#### Tasks

**T-017** [4h] Migrate CollectionList component
- Rename: `frontend/src/components/collections/CollectionList.jsx` → `.tsx`
- **Replace components:**
  - `<Table>` → shadcn `<Table>`
  - `<Chip>` → `<Badge>` with custom variants (Local, S3, etc.)
  - State badges: `<Badge variant="default">` with blue background for "Live"
  - Status indicator: Green dot + "Accessible" text
- **Add tab navigation:**
  - Create tabs: "All Collections", "Recently Accessed", "Archived"
  - Style with border-bottom, active state with `border-primary`
  - Use button elements with Tailwind hover states
- **Create FiltersSection component:**
  - Separate component: `FiltersSection.tsx`
  - State filter: shadcn `<Select>` with options (All, Live, Closed, Archived)
  - Type filter: shadcn `<Select>` with options (All, Local, S3, GCS, SMB)
  - Accessible only: shadcn `<Checkbox>`
  - Layout: flex gap-4 with proper spacing
- **Action buttons:**
  - Use Lucide icons: Info, RefreshCw, Edit, Trash2
  - Style: `variant="ghost"`, hover states, icon size w-4 h-4
  - Add tooltips for accessibility
- **TypeScript:**
  - Create `frontend/src/types/collection.ts`
  - Define `Collection`, `CollectionState`, `CollectionType` interfaces
  - Type all props, especially filter callbacks

**T-018** [4h] Migrate CollectionForm component
- Rename: `frontend/src/components/collections/CollectionForm.jsx` → `.tsx`
- **Replace form system:**
  - Use shadcn `<Form>` + react-hook-form
  - Create Zod validation schema: `CollectionFormSchema`
- **Form fields:**
  - Name: `<Input>` with required validation
  - Type: `<Select>` with options (LOCAL, S3, GCS, SMB)
  - Location: `<Input>` with path validation
  - State: `<Select>` with options (LIVE, CLOSED, ARCHIVED)
  - Connector: `<Select>` with connector options (hidden for LOCAL)
  - Cache TTL: `<Input type="number">` with optional override
- **Connector selection:**
  - Show connector dropdown only for remote types (S3, GCS, SMB)
  - Populate from `useConnectors()` hook
  - Add "Create New Connector" button that opens inline ConnectorForm
  - Handle connector created callback to refresh list
- **Validation:**
  - LOCAL type: connector_id must be null
  - Remote types: connector_id required (>= 1)
  - Location format validation (path for LOCAL, bucket for S3, etc.)
- **Test connection button:**
  - Call POST `/collections/{id}/test`
  - Show loading spinner
  - Display success/error with Toast
- **TypeScript:**
  - Type form data: `CollectionFormData`
  - Type submit handler: `(data: CollectionFormData) => Promise<void>`

**T-019** [2h] Migrate CollectionStatus component
- Rename: `frontend/src/components/collections/CollectionStatus.jsx` → `.tsx`
- **Status display:**
  - Accessible: Green badge with dot (bg-green-900/30 text-green-400)
  - Not accessible: Red badge with dot (bg-red-900/30 text-red-400)
  - Show error message below status in muted text
- **TypeScript:**
  - Type prop: `{ collection: Collection }`
  - Type status rendering logic

**T-020** [4h] Migrate CollectionsPage
- Rename: `frontend/src/pages/CollectionsPage.jsx` → `.tsx`
- **Page header:**
  - Title: "Collections" (text-3xl font-semibold)
  - Button: "NEW COLLECTION" with Plus icon (shadcn Button)
  - Style: flex justify-between mb-6
- **Tabs implementation:**
  - Render tab buttons above filters
  - Track active tab in state: `useState<'all' | 'recent' | 'archived'>('all')`
  - Style active tab with border-primary
- **Filters section:**
  - Render `<FiltersSection>` component
  - Pass filter state and callbacks
- **Table:**
  - Wrap `<CollectionList>` in card with border
  - Style: `rounded-lg border border-border overflow-hidden bg-card`
- **Create/Edit dialog:**
  - Replace MUI Dialog → shadcn `<Dialog>`
  - Show `<CollectionForm>` in DialogContent
  - Handle form submission and error display
- **Delete confirmation:**
  - Use shadcn `<AlertDialog>`
  - Show result/job counts if exist (from API response)
  - Destructive button styling
- **TypeScript:**
  - Type all page state
  - Type dialog state: `{ open: boolean, collection: Collection | null }`

**T-021** [2h] Update useCollections hook with TypeScript
- Rename: `frontend/src/hooks/useCollections.js` → `.ts`
- **TypeScript changes:**
  - Import types from `@/types/collection`
  - Type return value with all methods
  - Type filter parameters: `(state?: CollectionState, type?: CollectionType, accessibleOnly?: boolean)`
  - Type error handling

**T-022** [2h] Update collections service with TypeScript
- Rename: `frontend/src/services/collections.js` → `.ts`
- **TypeScript changes:**
  - Type all API functions
  - Create `CollectionCreate`, `CollectionUpdate` interfaces in types file
  - Type axios responses
  - Export all types from `@/types/collection`

**Checkpoint**: ✅ Collections page fully migrated, all features work, TypeScript compiles

---

### PHASE 4: Shared Services & Utils Migration (Week 3, Day 2)

**Duration**: 6 hours
**Goal**: Convert shared services to TypeScript, create type definitions

#### Tasks

**T-023** [2h] Update API service with TypeScript
- Rename: `frontend/src/services/api.js` → `.ts`
- **TypeScript changes:**
  - Type axios instance configuration
  - Add response interceptor types: `AxiosResponse<T>`
  - Add error interceptor types: `AxiosError`
  - Create generic API error type: `ApiError`
- **Error handling:**
  - Type error response structure
  - Create error message extraction utility

**T-024** [2h] Create shared type definitions
- Create `frontend/src/types/index.ts` (barrel file)
- **Common types:**
  - `Pagination`: `{ limit: number, offset: number, total: number }`
  - `ApiError`: `{ message: string, code?: string, details?: unknown }`
  - `FilterOptions`: Generic filter type
- **Re-exports:**
  - Export all from `./connector`
  - Export all from `./collection`
- **Enums:**
  - Define as const objects for runtime + type usage
  - Example: `export const CollectionState = { LIVE: 'live', ... } as const`

**T-025** [2h] Update index/main files
- Rename: `frontend/src/main.jsx` → `main.tsx`
- Update imports to use `.tsx` extensions
- Verify all type checking passes: `npm run type-check` (add to package.json)
- Fix any remaining type errors in dependency chain
- Update `index.html` to reference `main.tsx`

**Checkpoint**: ✅ All TypeScript compiles without errors, type checking passes

---

### PHASE 5: Testing Migration (Week 3, Days 3-5)

**Duration**: 18 hours
**Goal**: Update all tests for shadcn/ui components, add TypeScript types

#### Tasks

**T-026** [3h] Update test infrastructure
- Update `vitest.config.js` → `vitest.config.ts`
- **TypeScript support:**
  - Configure TypeScript in Vitest
  - Add path aliases for tests (`@/components`, `@/lib`)
- **MSW handlers update:**
  - Update `frontend/tests/mocks/handlers.js` → `.ts`
  - Type all request handlers
  - Type response bodies
- **Test utilities:**
  - Create `frontend/tests/utils/test-utils.tsx`
  - Add custom render function with all providers
  - Add utilities for shadcn component testing (select options, open dialogs, etc.)

**T-027** [4h] Update ConnectorForm tests
- Rename: `frontend/tests/components/ConnectorForm.test.jsx` → `.tsx`
- **Update selectors:**
  - Find shadcn Select by label text
  - Interact with react-hook-form fields
  - Trigger Zod validation errors
- **Test cases:**
  - ✅ Render form with all fields
  - ✅ Type selection shows correct credential fields (S3, GCS, SMB)
  - ✅ Zod validation: required fields, format validation
  - ✅ Test connection button click → loading state → success/error
  - ✅ Form submission → verify API call with correct payload
- **TypeScript:**
  - Type test setup data
  - Type custom matchers

**T-028** [3h] Update ConnectorList tests
- Rename: `frontend/tests/components/ConnectorList.test.jsx` → `.tsx`
- **Update selectors:**
  - Find shadcn Table rows
  - Find Badge components by text content
  - Interact with shadcn Select filters
- **Test cases:**
  - ✅ Render connector list from MSW data
  - ✅ Type filter changes visible connectors
  - ✅ Active-only checkbox filters correctly
  - ✅ Delete button opens AlertDialog
  - ✅ Delete protection error message displays (409 response)
  - ✅ Action buttons (edit, test, delete) trigger correct handlers
- **TypeScript:**
  - Type mock data
  - Type test assertions

**T-029** [4h] Update CollectionForm tests
- Rename: `frontend/tests/components/CollectionForm.test.jsx` → `.tsx`
- **Update selectors:**
  - Find react-hook-form fields
  - Interact with shadcn Select components
  - Test Zod validation
- **Test cases:**
  - ✅ Connector dropdown shows for remote types (S3, GCS, SMB)
  - ✅ LOCAL type hides connector field
  - ✅ "Create New Connector" button opens inline form
  - ✅ Form validation: required fields, connector_id constraints
  - ✅ Cache TTL validation (optional, must be positive)
  - ✅ Test connection button functionality
  - ✅ Form submission with valid data
- **TypeScript:**
  - Type form test data
  - Type validation scenarios

**T-030** [2h] Update hooks tests
- Rename files:
  - `frontend/tests/hooks/useConnectors.test.js` → `.ts`
  - `frontend/tests/hooks/useCollections.test.js` → `.ts`
- **Update tests:**
  - Add TypeScript type assertions
  - Type mock API responses
  - Verify hook return types match interfaces
- **Test cases remain the same:**
  - ✅ Fetch on mount
  - ✅ Create/update/delete operations
  - ✅ Error handling (409 delete protection)
  - ✅ Loading states

**T-031** [2h] Update integration tests
- Rename: `frontend/tests/integration/connector-collection-flow.test.jsx` → `.tsx`
- **Update selectors:**
  - Find shadcn Dialog components
  - Interact with new layout (Sidebar, TopHeader)
  - Navigate using new navigation structure
- **Test full flow:**
  - ✅ Create connector via form
  - ✅ Verify connector in list
  - ✅ Create collection referencing connector
  - ✅ Attempt delete connector → see 409 error in AlertDialog
  - ✅ Delete collection
  - ✅ Delete connector succeeds
- **TypeScript:**
  - Type test flow steps
  - Type assertions

**Checkpoint**: ✅ All tests pass, coverage maintained (>75%), TypeScript compiles

---

### PHASE 6: Polish & Quality Assurance (Week 4)

**Duration**: 12 hours
**Goal**: Final refinements, optimization, documentation

#### Tasks

**T-032** [3h] Implement dark theme properly
- **CSS variables verification:**
  - Ensure all components use `bg-background`, `text-foreground`, etc.
  - No hardcoded colors (except design system)
  - Test all components for consistency
- **Theme toggle (optional):**
  - Add theme provider from `next-themes` (works with Vite too)
  - Add toggle button in TopHeader user menu
  - Persist theme preference in localStorage
- **Accessibility:**
  - Verify color contrast ratios (WCAG AA compliance)
  - Test with dark mode browser extensions
  - Ensure all text is readable

**T-033** [2h] Optimize bundle size
- **Vite configuration:**
  - Update `vite.config.ts` for optimal tree-shaking
  - Configure chunk splitting for better caching
  - Verify shadcn components are tree-shakeable (should be)
- **Bundle analysis:**
  - Install: `npm install -D rollup-plugin-visualizer`
  - Generate bundle report: `npm run build -- --mode analyze`
  - Verify MUI is completely removed from bundle
  - Check for duplicate dependencies
- **Performance:**
  - Lazy load pages with `React.lazy()`
  - Measure First Contentful Paint (should improve)

**T-034** [2h] Accessibility audit
- **Keyboard navigation:**
  - Test all interactive elements with Tab
  - Verify focus indicators visible (ring classes)
  - Test Escape to close dialogs
  - Test Enter to submit forms
- **ARIA labels:**
  - Add `aria-label` to icon-only buttons
  - Verify dialog titles have proper ARIA
  - Test with screen reader (VoiceOver/NVDA)
- **Color contrast:**
  - Use browser DevTools to check contrast ratios
  - Ensure all text meets WCAG AA (4.5:1 for normal text)

**T-035** [2h] Responsive design testing
- **Mobile viewport:**
  - Test on 375px width (iPhone SE)
  - Verify sidebar collapse/hamburger menu
  - Ensure tables scroll horizontally
  - Test touch interactions for dialogs
- **Tablet viewport:**
  - Test on 768px width (iPad)
  - Verify layout doesn't break
  - Test landscape orientation
- **Desktop:**
  - Test on 1920px+ width
  - Verify max-width constraints
  - Test ultra-wide monitors

**T-036** [1h] Remove old dependencies
- **Uninstall MUI:**
  ```bash
  npm uninstall @mui/material @mui/icons-material @emotion/react @emotion/styled
  ```
- **Clean up:**
  - Run `npm prune` to remove unused packages
  - Verify package-lock.json updated
  - Check bundle size reduction (~500KB expected)
- **Verify build:**
  - Run `npm run build`
  - Verify no MUI references in build output
  - Test production build locally

**T-037** [2h] Documentation updates
- **Update README.md:**
  - Document new tech stack (Tailwind, shadcn/ui, TypeScript)
  - Add setup instructions for new developers
  - Document component library location
  - Add Tailwind IntelliSense setup for VS Code
- **Create component docs:**
  - Create `frontend/docs/components.md`
  - Document how to add new shadcn components
  - Document custom styling patterns
  - Add examples of common patterns
- **Migration notes:**
  - Document breaking changes from MUI
  - Add troubleshooting section
  - Document type definitions location

**Checkpoint**: ✅ Production ready, documented, optimized, accessible

---

## Testing Strategy

### Test Coverage Goals

- **Overall coverage**: Maintain >75% (constitution requirement)
- **Component coverage**: >80% for UI components
- **Hook coverage**: >90% for custom hooks
- **Service coverage**: >85% for API services

### Test Types

1. **Unit Tests**: Component rendering, props, state
2. **Integration Tests**: User flows, API mocking with MSW
3. **Type Tests**: TypeScript compilation catches type errors
4. **Accessibility Tests**: ARIA, keyboard navigation, contrast

### Test Execution

```bash
# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run in watch mode (development)
npm run test:watch

# Type checking
npm run type-check
```

---

## Rollback Plan

If migration encounters critical issues:

1. **Git rollback**: Revert to pre-migration commit
2. **Feature flag**: Hide new UI behind flag, show MUI version
3. **Gradual rollout**: Deploy to staging first, monitor errors
4. **Hotfix process**: Document critical issues, fix in separate branch

---

## Success Criteria

### Functional Requirements

- ✅ All existing features work identically
- ✅ No regressions in connector management
- ✅ No regressions in collection management
- ✅ Navigation works across all pages
- ✅ Forms validate and submit correctly
- ✅ Error handling maintains parity

### Non-Functional Requirements

- ✅ Test coverage >75%
- ✅ TypeScript compiles without errors
- ✅ Bundle size reduced by ~500KB
- ✅ First Contentful Paint <1.5s
- ✅ Lighthouse accessibility score >90
- ✅ No console errors or warnings

### Design Requirements

- ✅ Matches ui-style-proposal visual design
- ✅ Dark theme consistent across components
- ✅ Responsive design works on mobile/tablet/desktop
- ✅ Hover states and interactions feel polished
- ✅ Typography hierarchy clear and readable

---

## Timeline & Milestones

### Week 1: Foundation
- **Day 1-2**: Setup (Phase 0)
- **Day 3-5**: Layout (Phase 1)
- **Deliverable**: New layout renders, navigation works

### Week 2: Feature Migration
- **Day 1-3**: Connectors (Phase 2)
- **Day 4-5 + Week 3 Day 1**: Collections (Phase 3)
- **Deliverable**: All pages migrated, functional parity

### Week 3: Testing & Services
- **Day 2**: Services (Phase 4)
- **Day 3-5**: Testing (Phase 5)
- **Deliverable**: All tests pass, TypeScript compiles

### Week 4: Polish
- **Day 1-5**: QA & Polish (Phase 6)
- **Deliverable**: Production ready, documented

---

## Dependencies & Risks

### Dependencies

- shadcn/ui components must be compatible with Vite (✅ verified)
- Tailwind CSS v4 stable release (✅ available)
- TypeScript compiler (✅ no issues expected)
- Team availability for 3 weeks

### Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Component API differences cause bugs | Medium | High | Comprehensive testing, gradual rollout |
| TypeScript errors block progress | Low | Medium | Start with `any` types, refine incrementally |
| Design system incomplete | Low | Low | ui-style-proposal provides full design |
| Timeline overruns | Medium | Medium | Buffer time in estimates, parallel work |
| Team learning curve | Medium | Low | Pair programming, documentation |

---

## Post-Migration: Phases 4-7 Benefit

### Phase 4: Tool Execution UI (24 tasks)

**Built on modern stack from day one:**
- ProgressMonitor: WebSocket state + Tailwind animations
- ToolSelector: shadcn Buttons + icons
- ResultList: shadcn Table + pagination
- ReportViewer: iframe + shadcn Dialog

**Estimated time saved**: 30-40 hours (no migration needed)

---

### Phase 5: Pipeline Forms (17 tasks)

**Leverage modern form tools:**
- PipelineFormEditor: react-hook-form + Zod validation
- NodeEditor: Dynamic forms with type safety
- Visual validation: Tailwind for graph visualization

**Estimated time saved**: 25-30 hours (no migration needed)

---

### Phase 6: Trend Charts (8 tasks)

**Modern charting:**
- TrendChart: Recharts + Tailwind theming
- Responsive charts with dark theme
- TypeScript types for chart data

**Estimated time saved**: 10-15 hours (no migration needed)

---

### Phase 7: Config Migration UI (15 tasks)

**Complex forms made easy:**
- ConflictResolver: react-hook-form for nested objects
- Type-safe YAML parsing
- Zod validation for config schema

**Estimated time saved**: 20-25 hours (no migration needed)

---

## Total Value Proposition

### Investment
- **Migration effort**: 95 hours (3 weeks)
- **One-time cost**: Developer learning curve

### Return
- **Time saved on Phase 4-7**: 85-110 hours
- **Avoided migration later**: 185-255 hours
- **Total savings**: 270-365 hours
- **ROI**: 3-4x return on time investment

### Qualitative Benefits
- ✅ Modern, professional UI from ui-style-proposal
- ✅ Better developer experience (Tailwind IntelliSense, TypeScript)
- ✅ Easier onboarding for new developers
- ✅ Future-proof tech stack
- ✅ Faster feature development in Phases 4-7

---

## Conclusion

Migrating NOW is the optimal strategic decision:

1. **Minimal scope**: Only 11 components vs 25+ later
2. **Maximum benefit**: 64 future tasks inherit modern stack
3. **Best ROI**: 3-4x return on time investment
4. **No user disruption**: Not yet in production
5. **Team learning**: Master tools with simple components first

**Recommendation**: Proceed with migration plan before starting Phase 4.

---

## Appendix: Technology Comparison

### Current Stack (Phase 3)
```
React 18.3.1
Vite 6.0.5
Material-UI 6.3.1
Emotion (CSS-in-JS)
JavaScript
Recharts 2.15.0
```

### Target Stack (Post-Migration)
```
React 18.3.1 (unchanged)
Vite 6.0.5 (unchanged)
shadcn/ui + Radix UI
Tailwind CSS 4.1.9
TypeScript 5.x
Recharts 2.15.0 (unchanged)
react-hook-form + Zod
Lucide icons
```

### Bundle Size Impact
- **Before**: ~800KB (gzipped ~250KB)
- **After**: ~300KB (gzipped ~90KB)
- **Savings**: ~500KB raw, ~160KB gzipped

---

**Document Version**: 1.0
**Last Updated**: 2026-01-01
**Status**: Awaiting Approval
