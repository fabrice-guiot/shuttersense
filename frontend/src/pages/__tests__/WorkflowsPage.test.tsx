import { describe, test, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import WorkflowsPage from '../WorkflowsPage'

describe('WorkflowsPage', () => {
  test('renders coming soon placeholder', () => {
    render(<WorkflowsPage />)

    expect(screen.getByText('Workflows')).toBeDefined()
    expect(screen.getByText(/Workflow management coming soon/)).toBeDefined()
  })
})
