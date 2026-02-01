/**
 * Tests for AuditTrailSection component.
 *
 * Issue #120: Audit Trail Visibility Enhancement (Phase 4)
 */

import { describe, test, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AuditTrailSection } from '../AuditTrailSection'
import type { AuditInfo } from '@/contracts/api/audit-api'

// ============================================================================
// Mock dateFormat
// ============================================================================

vi.mock('@/utils/dateFormat', () => ({
  formatDateTime: (d: string | null | undefined) =>
    d ? `datetime(${d})` : 'Never',
}))

// ============================================================================
// Fixtures
// ============================================================================

const NOW = '2026-01-20T12:00:00Z'
const EARLIER = '2026-01-15T10:00:00Z'

const auditDifferentTimestamps: AuditInfo = {
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

const auditEmailFallback: AuditInfo = {
  created_at: EARLIER,
  created_by: {
    guid: 'usr_noname',
    display_name: null,
    email: 'noname@example.com',
  },
  updated_at: NOW,
  updated_by: {
    guid: 'usr_noname',
    display_name: null,
    email: 'noname@example.com',
  },
}

const auditNullUsers: AuditInfo = {
  created_at: EARLIER,
  created_by: null,
  updated_at: NOW,
  updated_by: null,
}

// ============================================================================
// Tests
// ============================================================================

describe('AuditTrailSection', () => {
  test('returns null when audit is null', () => {
    const { container } = render(<AuditTrailSection audit={null} />)
    expect(container.firstChild).toBeNull()
  })

  test('returns null when audit is undefined', () => {
    const { container } = render(<AuditTrailSection />)
    expect(container.firstChild).toBeNull()
  })

  test('renders created date and user', () => {
    render(<AuditTrailSection audit={auditDifferentTimestamps} />)
    expect(screen.getByText('Created')).toBeInTheDocument()
    expect(screen.getByText(`datetime(${EARLIER})`)).toBeInTheDocument()
    expect(screen.getByText('Alice')).toBeInTheDocument()
  })

  test('renders modified section when timestamps differ', () => {
    render(<AuditTrailSection audit={auditDifferentTimestamps} />)
    expect(screen.getByText('Modified')).toBeInTheDocument()
    expect(screen.getByText(`datetime(${NOW})`)).toBeInTheDocument()
    expect(screen.getByText('Bob')).toBeInTheDocument()
  })

  test('hides modified section when timestamps match', () => {
    render(<AuditTrailSection audit={auditSameTimestamps} />)
    expect(screen.getByText('Created')).toBeInTheDocument()
    expect(screen.queryByText('Modified')).not.toBeInTheDocument()
  })

  test('shows email fallback when display_name is null', () => {
    render(<AuditTrailSection audit={auditEmailFallback} />)
    // Both created_by and updated_by should show the email
    const emailElements = screen.getAllByText('noname@example.com')
    expect(emailElements.length).toBeGreaterThanOrEqual(1)
  })

  test('shows em dash when both display_name and email are null', () => {
    render(<AuditTrailSection audit={auditNullUsers} />)
    // Should show em-dashes for users
    const dashes = screen.getAllByText('\u2014')
    expect(dashes.length).toBeGreaterThanOrEqual(1)
  })
})
