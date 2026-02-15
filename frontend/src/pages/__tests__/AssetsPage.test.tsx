import { describe, test, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import AssetsPage from '../AssetsPage'

describe('AssetsPage', () => {
  test('renders coming soon placeholder', () => {
    render(<AssetsPage />)

    expect(screen.getByText('Assets')).toBeDefined()
    expect(screen.getByText(/Asset browser coming soon/)).toBeDefined()
  })
})
