/**
 * Tests for CamerasTab component
 *
 * Verifies camera list rendering, status filter, edit dialog, delete confirmation,
 * and TopHeader KPI stats integration.
 * Issue #217 - Pipeline-Driven Analysis Tools (US4)
 */

import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { CamerasTab } from '../CamerasTab'
import type { CameraStatus } from '@/contracts/api/camera-api'

const mockSetStats = vi.fn()

const CAMERA_DATA = {
  items: [
    {
      guid: 'cam_01hgw2bbg00000000000000001',
      camera_id: 'AB3D',
      status: 'confirmed' as CameraStatus,
      display_name: 'Canon EOS R5',
      make: 'Canon',
      model: 'EOS R5',
      serial_number: '12345',
      notes: null,
      metadata_json: null,
      created_at: '2026-01-15T10:00:00Z',
      updated_at: '2026-01-15T10:00:00Z',
      audit: null,
    },
    {
      guid: 'cam_01hgw2bbg00000000000000002',
      camera_id: 'XY5Z',
      status: 'temporary' as CameraStatus,
      display_name: null,
      make: 'Sony',
      model: 'A7R',
      serial_number: null,
      notes: null,
      metadata_json: null,
      created_at: '2026-01-16T10:00:00Z',
      updated_at: '2026-01-16T10:00:00Z',
      audit: null,
    },
  ],
  total: 2,
  limit: 50,
  offset: 0,
}

vi.mock('@/services/cameras')

vi.mock('@/contexts/HeaderStatsContext', () => ({
  useHeaderStats: () => ({
    stats: [],
    setStats: (...args: unknown[]) => mockSetStats(...args),
    clearStats: vi.fn(),
  }),
}))

vi.mock('@/components/audit', () => ({
  AuditTrailPopover: ({ fallbackTimestamp }: { fallbackTimestamp?: string }) => (
    <span data-testid="audit-popover">{fallbackTimestamp || 'No date'}</span>
  ),
}))

vi.mock('@/components/GuidBadge', () => ({
  GuidBadge: ({ guid }: { guid: string }) => <span data-testid="guid-badge">{guid}</span>,
}))

describe('CamerasTab', () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    const cameras = await import('@/services/cameras')
    vi.mocked(cameras.listCameras).mockResolvedValue(CAMERA_DATA)
    vi.mocked(cameras.updateCamera).mockResolvedValue(CAMERA_DATA.items[0] as any)
    vi.mocked(cameras.deleteCamera).mockResolvedValue({ message: 'Deleted', deleted_guid: 'cam_01hgw2bbg00000000000000001' })
    vi.mocked(cameras.getCameraStats).mockResolvedValue({
      total_cameras: 2,
      confirmed_count: 1,
      temporary_count: 1,
    })
  })

  test('renders camera list with correct data', async () => {
    render(
      <MemoryRouter>
        <CamerasTab />
      </MemoryRouter>,
    )

    // ResponsiveTable renders both desktop table and mobile cards, so use getAllByText
    await waitFor(() => {
      expect(screen.getAllByText('AB3D').length).toBeGreaterThanOrEqual(1)
    })

    expect(screen.getAllByText('Canon EOS R5').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('XY5Z').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Canon').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('EOS R5').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Sony').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('A7R').length).toBeGreaterThanOrEqual(1)
  })

  test('renders status badges', async () => {
    render(
      <MemoryRouter>
        <CamerasTab />
      </MemoryRouter>,
    )

    // ResponsiveTable renders both desktop table and mobile cards
    await waitFor(() => {
      expect(screen.getAllByText('Confirmed').length).toBeGreaterThanOrEqual(1)
    })

    expect(screen.getAllByText('Temporary').length).toBeGreaterThanOrEqual(1)
  })

  test('renders search input and filter', async () => {
    render(
      <MemoryRouter>
        <CamerasTab />
      </MemoryRouter>,
    )

    expect(screen.getByPlaceholderText('Search cameras...')).toBeDefined()
    expect(screen.getByText('Search')).toBeDefined()
  })

  test('sets header stats on mount', async () => {
    render(
      <MemoryRouter>
        <CamerasTab />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(mockSetStats).toHaveBeenCalledWith([
        { label: 'Total Cameras', value: 2 },
        { label: 'Confirmed', value: 1 },
        { label: 'Temporary', value: 1 },
      ])
    })
  })

  test('shows empty state when no cameras', async () => {
    const cameras = await import('@/services/cameras')
    vi.mocked(cameras.listCameras).mockResolvedValueOnce({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
    })

    render(
      <MemoryRouter>
        <CamerasTab />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('No cameras found')).toBeDefined()
    })
  })

  test('opens edit dialog when edit button is clicked', async () => {
    render(
      <MemoryRouter>
        <CamerasTab />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getAllByText('AB3D').length).toBeGreaterThanOrEqual(1)
    })

    const editButtons = screen.getAllByTitle('Edit camera')
    fireEvent.click(editButtons[0])

    await waitFor(() => {
      expect(screen.getByText('Edit Camera')).toBeDefined()
    })
  })

  test('shows delete confirmation when delete button is clicked', async () => {
    render(
      <MemoryRouter>
        <CamerasTab />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getAllByText('AB3D').length).toBeGreaterThanOrEqual(1)
    })

    const deleteButtons = screen.getAllByTitle('Delete camera')
    fireEvent.click(deleteButtons[0])

    await waitFor(() => {
      expect(screen.getByText('Delete Camera')).toBeDefined()
    })
  })
})
