import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../utils/test-utils'
import GuidBadge from '@/components/GuidBadge'

// Mock the clipboard API
const mockWriteText = vi.fn()

describe('GuidBadge', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockWriteText.mockResolvedValue(undefined)
    // Mock navigator.clipboard
    Object.defineProperty(navigator, 'clipboard', {
      value: {
        writeText: mockWriteText,
      },
      writable: true,
      configurable: true,
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('should render full GUID', () => {
    render(<GuidBadge guid="col_01hgw2bbg00000000000000001" />)

    expect(screen.getByText('col_01hgw2bbg00000000000000001')).toBeInTheDocument()
  })

  it('should render label when showLabel is true', () => {
    render(
      <GuidBadge
        guid="col_01hgw2bbg00000000000000001"
        showLabel
        label="Collection ID"
      />
    )

    expect(screen.getByText('Collection ID:')).toBeInTheDocument()
  })

  it('should not render label by default', () => {
    render(<GuidBadge guid="col_01hgw2bbg00000000000000001" />)

    expect(screen.queryByText('ID:')).not.toBeInTheDocument()
  })

  it('should copy to clipboard on click', async () => {
    const user = userEvent.setup()
    render(<GuidBadge guid="col_01hgw2bbg00000000000000001" />)

    const button = screen.getByRole('button')
    await user.click(button)

    // Wait for the copy success indicator (check icon appears when copied)
    await waitFor(() => {
      const checkIcon = button.querySelector('.lucide-check')
      expect(checkIcon).toBeInTheDocument()
    })
  })

  it('should have accessible label', () => {
    render(<GuidBadge guid="col_01hgw2bbg00000000000000001" />)

    const button = screen.getByRole('button')
    expect(button).toHaveAttribute(
      'aria-label',
      'Copy GUID: col_01hgw2bbg00000000000000001'
    )
  })

  it('should show copy icon by default', () => {
    render(<GuidBadge guid="col_01hgw2bbg00000000000000001" />)

    const button = screen.getByRole('button')
    expect(button.querySelector('svg')).toBeInTheDocument()
  })

  it('should apply custom className', () => {
    render(
      <GuidBadge
        guid="col_01hgw2bbg00000000000000001"
        className="custom-class"
      />
    )

    const button = screen.getByRole('button')
    expect(button).toHaveClass('custom-class')
  })

  it('should handle different entity prefixes', () => {
    const { rerender } = render(<GuidBadge guid="col_01hgw2bbg00000000000000001" />)
    expect(screen.getByText('col_01hgw2bbg00000000000000001')).toBeInTheDocument()

    rerender(<GuidBadge guid="con_01hgw2bbg00000000000000001" />)
    expect(screen.getByText('con_01hgw2bbg00000000000000001')).toBeInTheDocument()

    rerender(<GuidBadge guid="pip_01hgw2bbg00000000000000001" />)
    expect(screen.getByText('pip_01hgw2bbg00000000000000001')).toBeInTheDocument()

    rerender(<GuidBadge guid="res_01hgw2bbg00000000000000001" />)
    expect(screen.getByText('res_01hgw2bbg00000000000000001')).toBeInTheDocument()
  })
})
