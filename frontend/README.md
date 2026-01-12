# Photo Admin Frontend

Modern, accessible photo collection management interface built with React, TypeScript, and Tailwind CSS.

## Tech Stack

### Core Framework
- **React 18** - UI library with hooks and modern patterns
- **TypeScript** - Type-safe JavaScript
- **Vite** - Fast build tool and dev server
- **React Router v6** - Client-side routing

### UI & Styling
- **Tailwind CSS v4** - Utility-first CSS framework
- **shadcn/ui** - Accessible, customizable component library built on Radix UI
- **Lucide React** - Beautiful, consistent icon set
- **Class Variance Authority (CVA)** - Component variant management

### Forms & Validation
- **React Hook Form** - Performant form state management
- **Zod** - TypeScript-first schema validation
- **@hookform/resolvers** - Form validation integrations

### HTTP & State
- **Axios** - HTTP client for API requests
- **MSW (Mock Service Worker)** - API mocking for tests

### Testing
- **Vitest** - Fast unit test framework
- **React Testing Library** - Component testing utilities
- **@testing-library/user-event** - User interaction simulation
- **jsdom** - DOM implementation for Node

### Build & Optimization
- **Rollup** - Module bundler (via Vite)
- **Terser** - JavaScript minification
- **rollup-plugin-visualizer** - Bundle size analysis

## Project Structure

```
frontend/
├── src/
│   ├── components/          # React components
│   │   ├── collections/     # Collection management components
│   │   ├── connectors/      # Connector management components
│   │   ├── events/          # Calendar events components (Issue #39)
│   │   ├── layout/          # Layout components (Sidebar, Header)
│   │   ├── settings/        # Settings page components
│   │   └── ui/              # shadcn/ui components
│   ├── contracts/           # API contracts (shared with backend)
│   │   └── api/             # TypeScript interfaces for API
│   ├── hooks/               # Custom React hooks
│   ├── lib/                 # Utility functions
│   ├── pages/               # Page components
│   ├── types/               # TypeScript type definitions
│   │   └── schemas/         # Zod validation schemas
│   ├── globals.css          # Global styles and CSS variables
│   ├── App.tsx              # Root component with routing
│   └── main.tsx             # Application entry point
├── tests/
│   ├── components/          # Component tests
│   ├── hooks/               # Hook tests
│   ├── integration/         # Integration tests
│   ├── mocks/               # MSW mock handlers
│   ├── utils/               # Test utilities
│   └── setup.ts             # Test setup and globals
├── public/                  # Static assets
├── dist/                    # Production build output
├── vite.config.ts           # Vite configuration
├── vitest.config.ts         # Vitest configuration
├── tsconfig.json            # TypeScript configuration
├── tailwind.config.js       # Tailwind CSS configuration
├── components.json          # shadcn/ui configuration
└── package.json             # Dependencies and scripts
```

## Available Scripts

### Development
```bash
npm run dev          # Start development server on port 3000
```

### Building
```bash
npm run build        # Create production build in dist/
npm run preview      # Preview production build locally
```

### Testing
```bash
npm test             # Run tests in watch mode
npm run test:run     # Run tests once
npm run test:ui      # Open Vitest UI
npm run test:coverage # Generate coverage report
```

### Code Quality
```bash
npm run lint         # Run ESLint
npm run type-check   # Run TypeScript compiler check
```

## Development Guide

### Adding New Components

1. **UI Components** (shadcn/ui):
   ```bash
   npx shadcn@latest add button
   npx shadcn@latest add dialog
   ```
   Components are added to `src/components/ui/`

2. **Feature Components**:
   - Place in appropriate directory (`collections/`, `connectors/`, etc.)
   - Use TypeScript for type safety
   - Follow existing patterns for props and composition

### Styling Guidelines

- Use Tailwind utility classes for styling
- Reference design tokens from `globals.css`:
  - Colors: `bg-background`, `text-foreground`, `border-border`, etc.
  - Spacing: Use Tailwind's spacing scale (p-4, m-2, etc.)
- Use `cn()` helper from `@/lib/utils` to merge classes:
  ```tsx
  import { cn } from '@/lib/utils'
  <div className={cn('base-classes', conditional && 'conditional-classes')} />
  ```

### Form Handling

All forms use React Hook Form + Zod for validation:

```tsx
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { mySchema } from '@/types/schemas/my-schema'

const form = useForm({
  resolver: zodResolver(mySchema),
  defaultValues: { /* ... */ }
})
```

### API Integration

- API contracts defined in `src/contracts/api/`
- Use Axios for HTTP requests
- Custom hooks in `src/hooks/` handle data fetching

### Accessibility

- All interactive elements have proper ARIA labels
- Icon-only buttons use `aria-label` attributes
- Loading spinners use `role="status"`
- Keyboard navigation fully supported (Tab, Enter, Escape)
- Color contrast meets WCAG AA standards (4.5:1)

## Calendar Events Feature (Issue #39)

The frontend includes comprehensive event management:

### Pages
- **Events List** (`/events`) - Calendar view with filtering by category, status, attendance
- **Event Detail** (`/events/:guid`) - Full event details with related entities
- **Event Form** - Create/edit events with all fields including logistics

### Components (`src/components/events/`)
- `EventsPage.tsx` - Main events listing page with KPI header stats
- `EventForm.tsx` - Create/edit form with category, location, organizer selection
- `CategoryForm.tsx` - Category management with color picker and icon selector
- `LocationForm.tsx` - Location management with address and timezone
- `OrganizerForm.tsx` - Organizer management with contact info
- `PerformerForm.tsx` - Performer management with social media links

### Settings Integration
- **Categories** - Manage event categories in Settings > Directory > Categories
- **Locations** - Manage locations in Settings > Directory > Locations
- **Organizers** - Manage organizers in Settings > Directory > Organizers
- **Performers** - Manage performers in Settings > Directory > Performers
- **Event Statuses** - Configure event status options in Settings > Config

## Design System

### Color Palette

The application uses a dark theme with CSS custom properties:

- **Background**: `--background` - Main background color
- **Foreground**: `--foreground` - Main text color
- **Primary**: `--primary` - Primary actions and highlights
- **Secondary**: `--secondary` - Secondary elements
- **Accent**: `--accent` - Accent elements
- **Muted**: `--muted` - Muted backgrounds
- **Border**: `--border` - Border colors

See `src/globals.css` for complete color definitions.

### Typography

- Font: System font stack for optimal performance
- Scale: Tailwind's default type scale
- Weight: 400 (normal), 500 (medium), 600 (semibold), 700 (bold)

## Build Optimization

Production builds are optimized with:

- **Code Splitting**: Vendor chunks for better caching
  - `react-vendor`: React, React DOM, React Router
  - `radix-vendor`: Radix UI components
  - `form-vendor`: Form libraries (React Hook Form, Zod)
  - `utils-vendor`: Utility libraries
- **Minification**: Terser with console.log removal
- **Tree Shaking**: Automatic removal of unused code
- **Asset Optimization**: Hashed filenames for cache busting

Bundle analysis available after build at `dist/stats.html`

## Browser Support

- Chrome/Edge: Last 2 versions
- Firefox: Last 2 versions
- Safari: Last 2 versions

## Environment Variables

Create `.env.local` for local development:

```env
VITE_API_URL=http://localhost:8000
```

## API Proxy

Development server proxies `/api` requests to `http://localhost:8000` (configurable in `vite.config.ts`)

## Contributing

1. Follow TypeScript best practices
2. Write tests for new components and hooks
3. Ensure accessibility standards are met
4. Use design tokens (no hardcoded colors)
5. Run tests and type-check before committing

## License

GNU Affero General Public License v3.0 (AGPL-3.0)
