/**
 * Tests for AgentStatusBadge component
 *
 * Issue #90 - Distributed Agent Architecture (Phase 3)
 * Task: T046
 */

import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/react'
import { render } from '../../utils/test-utils'
import { AgentStatusBadge } from '@/components/agents/AgentStatusBadge'

describe('AgentStatusBadge', () => {
  it('renders online status with success styling', () => {
    render(<AgentStatusBadge status="online" />)

    // Online + verified + no running jobs = "Idle" (Issue #236)
    const badge = screen.getByText('Idle')
    expect(badge).toBeInTheDocument()
    // Check for success variant styling
    expect(badge).toHaveClass('bg-success')
  })

  it('renders offline status with gray styling', () => {
    render(<AgentStatusBadge status="offline" />)

    const badge = screen.getByText('Offline')
    expect(badge).toBeInTheDocument()
    // Check for secondary variant
    expect(badge).toHaveClass('bg-secondary')
  })

  it('renders error status with red styling', () => {
    render(<AgentStatusBadge status="error" />)

    const badge = screen.getByText('Error')
    expect(badge).toBeInTheDocument()
    // Check for destructive variant
    expect(badge).toHaveClass('bg-destructive')
  })

  it('renders revoked status with outline styling', () => {
    render(<AgentStatusBadge status="revoked" />)

    const badge = screen.getByText('Revoked')
    expect(badge).toBeInTheDocument()
    // Check for outline variant (border visible)
    expect(badge).toHaveClass('border')
  })

  it('shows pulsing dot for online status', () => {
    const { container } = render(<AgentStatusBadge status="online" />)

    // Find the pulsing dot element
    const pulsingDot = container.querySelector('.animate-pulse')
    expect(pulsingDot).toBeInTheDocument()
  })

  it('does not show pulsing dot for offline status', () => {
    const { container } = render(<AgentStatusBadge status="offline" />)

    const pulsingDot = container.querySelector('.animate-pulse')
    expect(pulsingDot).not.toBeInTheDocument()
  })

  it('can hide label when showLabel is false', () => {
    render(<AgentStatusBadge status="online" showLabel={false} />)

    // Badge should exist but without visible text
    expect(screen.queryByText('Idle')).not.toBeInTheDocument()
  })

  it('applies custom className', () => {
    render(<AgentStatusBadge status="online" className="custom-class" />)

    const badge = screen.getByText('Idle')
    expect(badge).toHaveClass('custom-class')
  })
})
