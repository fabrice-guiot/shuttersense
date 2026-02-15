import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { NotFoundPage } from '../NotFoundPage'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

describe('NotFoundPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  test('renders 404 heading and description', () => {
    render(
      <MemoryRouter>
        <NotFoundPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('404')).toBeDefined()
    expect(screen.getByText('Page not found')).toBeDefined()
    expect(
      screen.getByText("The page you're looking for doesn't exist or has been moved."),
    ).toBeDefined()
  })

  test('renders Go Back and Go Home buttons', () => {
    render(
      <MemoryRouter>
        <NotFoundPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('Go Back')).toBeDefined()
    expect(screen.getByText('Go Home')).toBeDefined()
  })

  test('Go Back navigates back', async () => {
    render(
      <MemoryRouter>
        <NotFoundPage />
      </MemoryRouter>,
    )

    await userEvent.click(screen.getByText('Go Back'))
    expect(mockNavigate).toHaveBeenCalledWith(-1)
  })

  test('Go Home navigates to root', async () => {
    render(
      <MemoryRouter>
        <NotFoundPage />
      </MemoryRouter>,
    )

    await userEvent.click(screen.getByText('Go Home'))
    expect(mockNavigate).toHaveBeenCalledWith('/')
  })
})
