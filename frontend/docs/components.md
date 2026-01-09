# Component Documentation

Guide to using shadcn/ui components in the Photo Admin frontend application.

> **Important**: Before using components, review the [Design System](./design-system.md) for color guidelines, button usage patterns, and UI consistency requirements.

## Table of Contents

- [Overview](#overview)
- [UI Components](#ui-components)
- [Feature Components](#feature-components)
- [Patterns & Best Practices](#patterns--best-practices)

## Overview

Our component library is built on [shadcn/ui](https://ui.shadcn.com/), which provides:
- **Accessible**: Built on Radix UI primitives with ARIA attributes
- **Customizable**: Copy components into your project and modify as needed
- **Composable**: Small, focused components that work together
- **Styled with Tailwind**: Utility-first styling with design tokens

### Installation

Add new shadcn/ui components:
```bash
npx shadcn@latest add button
npx shadcn@latest add dialog
npx shadcn@latest add select
```

Components are installed to `src/components/ui/`

## UI Components

### Button

Versatile button component with multiple variants and sizes.

**Location**: `src/components/ui/button.tsx`

**Variants**:
- `default` - Primary button
- `destructive` - Dangerous actions (delete, remove)
- `outline` - Secondary button with border
- `secondary` - Secondary button
- `ghost` - Minimal button (often used for icons)
- `link` - Link-styled button

**Sizes**:
- `default` - Standard size (h-9)
- `sm` - Small (h-8)
- `lg` - Large (h-10)
- `icon` - Square button for icons only

**Usage**:
```tsx
import { Button } from '@/components/ui/button'

// Primary button
<Button>Click Me</Button>

// Destructive button
<Button variant="destructive">Delete</Button>

// Icon button with aria-label (required for accessibility)
<Button variant="ghost" size="icon" aria-label="Edit item">
  <Edit className="h-4 w-4" />
</Button>
```

### Dialog

Modal dialog for important actions and forms.

**Location**: `src/components/ui/dialog.tsx`

**Components**:
- `Dialog` - Root component
- `DialogTrigger` - Button that opens dialog
- `DialogContent` - Dialog body
- `DialogHeader` - Header section
- `DialogTitle` - Dialog title
- `DialogDescription` - Description text
- `DialogFooter` - Footer with action buttons

**Usage**:
```tsx
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

<Dialog open={isOpen} onOpenChange={setIsOpen}>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Confirm Action</DialogTitle>
      <DialogDescription>
        Are you sure you want to delete this item?
      </DialogDescription>
    </DialogHeader>
    <DialogFooter>
      <Button variant="outline" onClick={() => setIsOpen(false)}>
        Cancel
      </Button>
      <Button variant="destructive" onClick={handleDelete}>
        Delete
      </Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

### Form

Form components using React Hook Form + Zod validation.

**Location**: `src/components/ui/form.tsx`

**Components**:
- `Form` - Form wrapper
- `FormField` - Individual field
- `FormItem` - Field container
- `FormLabel` - Field label
- `FormControl` - Input wrapper
- `FormDescription` - Help text
- `FormMessage` - Error message

**Usage**:
```tsx
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Form, FormField, FormItem, FormLabel, FormControl, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'

const formSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  email: z.string().email('Invalid email'),
})

function MyForm() {
  const form = useForm({
    resolver: zodResolver(formSchema),
    defaultValues: { name: '', email: '' },
  })

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Name</FormLabel>
              <FormControl>
                <Input {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
      </form>
    </Form>
  )
}
```

### Input

Text input component.

**Location**: `src/components/ui/input.tsx`

**Usage**:
```tsx
import { Input } from '@/components/ui/input'

<Input
  type="text"
  placeholder="Enter your name"
  value={value}
  onChange={(e) => setValue(e.target.value)}
/>
```

### Select

Accessible dropdown select component.

**Location**: `src/components/ui/select.tsx`

**Components**:
- `Select` - Root component
- `SelectTrigger` - Button that opens dropdown
- `SelectValue` - Displays selected value
- `SelectContent` - Dropdown container
- `SelectItem` - Individual option
- `SelectGroup` - Option group
- `SelectLabel` - Group label

**Usage**:
```tsx
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

<Select value={value} onValueChange={setValue}>
  <SelectTrigger>
    <SelectValue placeholder="Select an option" />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="option1">Option 1</SelectItem>
    <SelectItem value="option2">Option 2</SelectItem>
  </SelectContent>
</Select>
```

### Table

Table components for data display.

**Location**: `src/components/ui/table.tsx`

**Components**:
- `Table` - Root table
- `TableHeader` - Header section
- `TableBody` - Body section
- `TableRow` - Row
- `TableHead` - Header cell
- `TableCell` - Body cell

**Usage**:
```tsx
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

<Table>
  <TableHeader>
    <TableRow>
      <TableHead>Name</TableHead>
      <TableHead>Status</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    <TableRow>
      <TableCell>Item 1</TableCell>
      <TableCell>Active</TableCell>
    </TableRow>
  </TableBody>
</Table>
```

### Badge

Small status indicator component.

**Location**: `src/components/ui/badge.tsx`

**Variants**:
- `default` - Primary badge
- `secondary` - Secondary badge
- `destructive` - Error/warning badge
- `outline` - Outlined badge

**Usage**:
```tsx
import { Badge } from '@/components/ui/badge'

<Badge>New</Badge>
<Badge variant="secondary">S3</Badge>
<Badge variant="destructive">Error</Badge>
```

### Checkbox

Accessible checkbox component.

**Location**: `src/components/ui/checkbox.tsx`

**Usage**:
```tsx
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'

<div className="flex items-center gap-2">
  <Checkbox id="terms" checked={checked} onCheckedChange={setChecked} />
  <Label htmlFor="terms">Accept terms</Label>
</div>
```

### Tooltip

Contextual help tooltip.

**Location**: `src/components/ui/tooltip.tsx`

**Components**:
- `TooltipProvider` - Required wrapper (only one needed at root)
- `Tooltip` - Tooltip instance
- `TooltipTrigger` - Element that shows tooltip on hover
- `TooltipContent` - Tooltip content

**Usage**:
```tsx
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'

<TooltipProvider>
  <Tooltip>
    <TooltipTrigger asChild>
      <Button variant="ghost" size="icon" aria-label="Delete">
        <Trash2 className="h-4 w-4" />
      </Button>
    </TooltipTrigger>
    <TooltipContent>Delete Item</TooltipContent>
  </Tooltip>
</TooltipProvider>
```

### Tabs

Tabbed interface component.

**Location**: `src/components/ui/tabs.tsx`

**Components**:
- `Tabs` - Root component
- `TabsList` - Tab button container
- `TabsTrigger` - Individual tab button
- `TabsContent` - Tab panel content

**Usage**:
```tsx
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

<Tabs defaultValue="all">
  <TabsList>
    <TabsTrigger value="all">All Items</TabsTrigger>
    <TabsTrigger value="active">Active</TabsTrigger>
  </TabsList>
  <TabsContent value="all">
    {/* All items content */}
  </TabsContent>
  <TabsContent value="active">
    {/* Active items content */}
  </TabsContent>
</Tabs>
```

## Feature Components

### ConnectorList

Displays list of storage connectors with filtering and actions.

**Location**: `src/components/connectors/ConnectorList.tsx`

**Props**:
```tsx
interface ConnectorListProps {
  connectors: Connector[]
  loading: boolean
  onEdit: (connector: Connector) => void
  onDelete: (connector: Connector) => void
  onTest: (connector: Connector) => void
}
```

**Features**:
- Type filtering (S3, GCS, SMB)
- Active/inactive filtering
- Icon buttons with tooltips
- Delete confirmation dialog

### ConnectorForm

Form for creating/editing storage connectors.

**Location**: `src/components/connectors/ConnectorForm.tsx`

**Props**:
```tsx
interface ConnectorFormProps {
  connector: Connector | null
  onSubmit: (data: ConnectorFormData) => Promise<void>
  onCancel: () => void
}
```

**Features**:
- Type-specific credential fields
- Zod validation
- React Hook Form integration
- Active/inactive toggle

### CollectionList

Displays list of photo collections with filtering and tabs.

**Location**: `src/components/collections/CollectionList.tsx`

**Props**:
```tsx
interface CollectionListProps {
  collections: Collection[]
  loading: boolean
  onEdit: (collection: Collection) => void
  onDelete: (collection: Collection) => void
  onInfo: (collection: Collection) => void
  onRefresh: (collection: Collection) => void
}
```

**Features**:
- Tabbed interface (All, Recent, Archived)
- State and type filtering
- Accessibility status indicators
- Multiple action buttons per item

### CollectionForm

Form for creating/editing photo collections.

**Location**: `src/components/collections/CollectionForm.tsx`

**Props**:
```tsx
interface CollectionFormProps {
  collection: Collection | null
  connectors: Connector[]
  onSubmit: (data: CollectionFormData) => Promise<void>
  onCancel: () => void
}
```

**Features**:
- Type-dependent connector selection
- State dropdown
- Zod validation with business rules
- Cache TTL configuration

### Layout Components

#### Sidebar

Navigation sidebar with menu items.

**Location**: `src/components/layout/Sidebar.tsx`

**Features**:
- Active route detection
- Icon + label navigation
- Responsive collapse behavior

#### TopHeader

Page header with title and actions.

**Location**: `src/components/layout/TopHeader.tsx`

**Features**:
- Dynamic page title
- Stats display
- User profile section

## Patterns & Best Practices

### Utility Function: cn()

Always use the `cn()` utility to merge Tailwind classes:

```tsx
import { cn } from '@/lib/utils'

// Conditional classes
<div className={cn('base-class', isActive && 'active-class')} />

// Override classes (Tailwind conflicts resolved)
<div className={cn('px-2', someCondition && 'px-4')} />
// Result: px-4 (not both px-2 and px-4)
```

### Design Tokens

Use CSS custom properties instead of hardcoded colors:

```tsx
// ❌ Bad - hardcoded color
<div className="bg-gray-900 text-white" />

// ✅ Good - design tokens
<div className="bg-background text-foreground" />
```

Available tokens:
- `bg-background`, `text-foreground`
- `bg-card`, `text-card-foreground`
- `bg-primary`, `text-primary-foreground`
- `bg-secondary`, `text-secondary-foreground`
- `bg-muted`, `text-muted-foreground`
- `bg-accent`, `text-accent-foreground`
- `bg-destructive`, `text-destructive-foreground`
- `border-border`, `border-input`

### Accessibility

Always provide proper ARIA attributes:

```tsx
// Icon-only buttons MUST have aria-label
<Button variant="ghost" size="icon" aria-label="Delete item">
  <Trash2 className="h-4 w-4" />
</Button>

// Loading spinners should have role="status"
<div role="status" className="animate-spin..." />

// Form labels must be associated with inputs
<Label htmlFor="name">Name</Label>
<Input id="name" {...field} />
```

### Form Validation

Define schemas with Zod and use with React Hook Form:

```tsx
// 1. Define schema
import { z } from 'zod'

const schema = z.object({
  name: z.string().min(1, 'Name is required'),
  email: z.string().email('Invalid email'),
})

type FormData = z.infer<typeof schema>

// 2. Setup form
const form = useForm<FormData>({
  resolver: zodResolver(schema),
  defaultValues: { name: '', email: '' },
})

// 3. Use in component
<FormField
  control={form.control}
  name="name"
  render={({ field }) => (
    <FormItem>
      <FormLabel>Name</FormLabel>
      <FormControl>
        <Input {...field} />
      </FormControl>
      <FormMessage />
    </FormItem>
  )}
/>
```

### Conditional Rendering

Use early returns for loading/error states:

```tsx
function MyComponent({ data, loading }) {
  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <div role="status" className="h-8 w-8 animate-spin..." />
      </div>
    )
  }

  if (!data || data.length === 0) {
    return (
      <div className="text-center text-muted-foreground">
        No data found
      </div>
    )
  }

  return <div>{/* Main content */}</div>
}
```

### Icon Usage

Use Lucide React icons consistently:

```tsx
import { Edit, Trash2, Info, RefreshCw } from 'lucide-react'

// Standard size: h-4 w-4
<Edit className="h-4 w-4" />

// Larger icons: h-5 w-5
<Info className="h-5 w-5" />
```

### Responsive Design

Use Tailwind's responsive prefixes:

```tsx
<div className="flex flex-col gap-4 sm:flex-row">
  {/* Stacks vertically on mobile, horizontal on sm+ */}
</div>

<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
  {/* 1 column mobile, 2 on md, 3 on lg */}
</div>
```

## Testing Components

Use React Testing Library with proper queries:

```tsx
import { render, screen } from '@testing-library/react'
import { Button } from '@/components/ui/button'

test('renders button with text', () => {
  render(<Button>Click Me</Button>)
  expect(screen.getByRole('button', { name: /click me/i })).toBeInTheDocument()
})

// Icon buttons - test by aria-label
test('renders icon button', () => {
  render(
    <Button variant="ghost" size="icon" aria-label="Delete">
      <Trash2 className="h-4 w-4" />
    </Button>
  )
  expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument()
})
```

## Resources

- [shadcn/ui Documentation](https://ui.shadcn.com/)
- [Radix UI Documentation](https://www.radix-ui.com/)
- [Tailwind CSS Documentation](https://tailwindcss.com/)
- [React Hook Form](https://react-hook-form.com/)
- [Zod](https://zod.dev/)
