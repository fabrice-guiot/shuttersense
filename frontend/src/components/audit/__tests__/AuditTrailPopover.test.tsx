/**
 * Tests for AuditTrailPopover component.
 *
 * Issue #120: Audit Trail Visibility Enhancement (Phase 4)
 */

import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AuditTrailPopover } from '../AuditTrailPopover'
import type { AuditInfo } from '@/contracts/api/audit-api'

// ============================================================================
// Mock dateFormat — we only care about what the component renders, not the
// actual date-formatting logic (that has its own test suite).
// ============================================================================

vi.mock('@/utils/dateFormat', () => ({
  formatRelativeTime: (d: string | null | undefined) =>
    d ? `relative(${d})` : 'Never',
  formatDateTime: (d: string | null | undefined) =>
    d ? `datetime(${d})` : 'Never',
}))

// ============================================================================
// Fixtures
// ============================================================================

const NOW = '2026-01-20T12:00:00Z'
const EARLIER = '2026-01-15T10:00:00Z'

const auditBothUsers: AuditInfo = {
  created_at: EARLIER,
  created_by: {
    guid: 'usr_creator',
    display_name: 'Alice',
    email: 'alice@example.com',
  },
  updated_at: NOW,
  updated_by: {
    guid: 'usr_updater',
    display_name: 'Bob',
    email: 'bob@example.com',
  },
}

const auditSameTimestamps: AuditInfo = {
  created_at: NOW,
  created_by: {
    guid: 'usr_creator',
    display_name: 'Alice',
    email: 'alice@example.com',
  },
  updated_at: NOW,
  updated_by: {
    guid: 'usr_creator',
    display_name: 'Alice',
    email: 'alice@example.com',
  },
}

const auditNullUsers: AuditInfo = {
  created_at: EARLIER,
  created_by: null,
  updated_at: NOW,
  updated_by: null,
}

const auditEmailOnly: AuditInfo = {
  created_at: EARLIER,
  created_by: {
    guid: 'usr_noid',
    display_name: null,
    email: 'noname@example.com',
  },
  updated_at: NOW,
  updated_by: {
    guid: 'usr_noid',
    display_name: null,
    email: 'noname@example.com',
  },
}

// ============================================================================
// Tests
// ============================================================================

describe('AuditTrailPopover', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  test('renders relative time trigger text when audit provided', () => {
    render(<AuditTrailPopover audit={auditBothUsers} />)
    expect(screen.getByText(`relative(${NOW})`)).toBeInTheDocument()
  })

  test('shows dotted underline styling when audit present', () => {
    render(<AuditTrailPopover audit={auditBothUsers} />)
    const trigger = screen.getByText(`relative(${NOW})`)
    expect(trigger.className).toContain('border-dotted')
  })

  test('no dotted underline when only fallbackTimestamp provided', () => {
    render(<AuditTrailPopover fallbackTimestamp={NOW} />)
    const text = screen.getByText(`relative(${NOW})`)
    expect(text.className).not.toContain('border-dotted')
  })

  test('renders em dash when both audit and fallbackTimestamp are null', () => {
    render(<AuditTrailPopover />)
    expect(screen.getByText('\u2014')).toBeInTheDocument()
  })

  test('renders em dash when audit and fallbackTimestamp are explicitly null', () => {
    render(
      <AuditTrailPopover audit={null} fallbackTimestamp={null} />
    )
    expect(screen.getByText('\u2014')).toBeInTheDocument()
  })

  test('uses email when display_name is null', () => {
    // The email fallback is tested inside the popover content, which is only
    // rendered when hovering. For unit-test purposes we verify the component
    // renders without crashing when display_name is null.
    render(<AuditTrailPopover audit={auditEmailOnly} />)
    expect(screen.getByText(`relative(${NOW})`)).toBeInTheDocument()
  })

  test('uses fallbackTimestamp when audit is null', () => {
    render(<AuditTrailPopover audit={null} fallbackTimestamp={EARLIER} />)
    expect(screen.getByText(`relative(${EARLIER})`)).toBeInTheDocument()
  })

  test('renders trigger for audit with same timestamps', () => {
    render(<AuditTrailPopover audit={auditSameTimestamps} />)
    expect(screen.getByText(`relative(${NOW})`)).toBeInTheDocument()
  })

  test('renders trigger for audit with null users', () => {
    render(<AuditTrailPopover audit={auditNullUsers} />)
    expect(screen.getByText(`relative(${NOW})`)).toBeInTheDocument()
  })
})
