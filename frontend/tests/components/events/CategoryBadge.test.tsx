/**
 * CategoryBadge Component Tests
 *
 * Tests for category icon badge display in compact calendar view.
 * Feature: 016-mobile-calendar-view (GitHub Issue #69)
 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { CategoryBadge } from '@/components/events/CategoryBadge'

describe('CategoryBadge', () => {
  const defaultProps = {
    icon: 'music',
    color: '#3b82f6',
    count: 2,
    name: 'Music',
  }

  describe('Rendering', () => {
    it('renders with category icon and color', () => {
      render(<CategoryBadge {...defaultProps} />)

      const badge = screen.getByRole('img', { name: /2 music events/i })
      expect(badge).toBeInTheDocument()
    })

    it('applies category color as background with opacity', () => {
      render(<CategoryBadge {...defaultProps} />)

      const badge = screen.getByRole('img')
      expect(badge).toHaveStyle({ backgroundColor: '#3b82f620' })
    })

    it('displays count badge when count > 1', () => {
      render(<CategoryBadge {...defaultProps} count={3} />)

      const badge = screen.getByRole('img')
      expect(badge).toHaveTextContent('3')
    })

    it('does not display count badge when count is 1', () => {
      render(<CategoryBadge {...defaultProps} count={1} />)

      const badge = screen.getByRole('img')
      // Should not have a count badge child
      const countBadge = badge.querySelector('span')
      expect(countBadge).toBeNull()
    })
  })

  describe('Count Display', () => {
    it('displays "99+" when count exceeds 99', () => {
      render(<CategoryBadge {...defaultProps} count={100} />)

      expect(screen.getByText('99+')).toBeInTheDocument()
    })

    it('displays exact count when count is 99', () => {
      render(<CategoryBadge {...defaultProps} count={99} />)

      expect(screen.getByText('99')).toBeInTheDocument()
    })

    it('displays exact count when count is between 2 and 99', () => {
      render(<CategoryBadge {...defaultProps} count={42} />)

      expect(screen.getByText('42')).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has correct aria-label for singular event', () => {
      render(<CategoryBadge {...defaultProps} count={1} name="Concert" />)

      expect(screen.getByRole('img', { name: '1 Concert event' })).toBeInTheDocument()
    })

    it('has correct aria-label for plural events', () => {
      render(<CategoryBadge {...defaultProps} count={5} name="Sports" />)

      expect(screen.getByRole('img', { name: '5 Sports events' })).toBeInTheDocument()
    })

    it('has title attribute for tooltip', () => {
      render(<CategoryBadge {...defaultProps} count={3} name="Theatre" />)

      const badge = screen.getByRole('img')
      expect(badge).toHaveAttribute('title', '3 Theatre events')
    })
  })

  describe('Icon Fallback', () => {
    it('renders fallback icon when icon prop is null', () => {
      render(<CategoryBadge {...defaultProps} icon={null} />)

      // Should still render without crashing
      expect(screen.getByRole('img')).toBeInTheDocument()
    })

    it('renders fallback icon when icon prop is invalid', () => {
      render(<CategoryBadge {...defaultProps} icon="nonexistent-icon" />)

      // Should render with fallback HelpCircle icon
      expect(screen.getByRole('img')).toBeInTheDocument()
    })
  })

  describe('Color Fallback', () => {
    it('applies muted background when color is null', () => {
      render(<CategoryBadge {...defaultProps} color={null} />)

      const badge = screen.getByRole('img')
      expect(badge).toHaveStyle({ backgroundColor: 'var(--muted)' })
    })
  })

  describe('Custom ClassName', () => {
    it('applies additional className', () => {
      render(<CategoryBadge {...defaultProps} className="custom-class" />)

      const badge = screen.getByRole('img')
      expect(badge).toHaveClass('custom-class')
    })
  })
})
