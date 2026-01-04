import '@testing-library/jest-dom'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeAll, afterAll } from 'vitest'
import { server } from './mocks/server'

// Establish API mocking before all tests
beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' })
})

// Reset handlers after each test
afterEach(() => {
  server.resetHandlers()
  cleanup()
})

// Clean up after all tests are done
afterAll(() => {
  server.close()
})

// Mock ResizeObserver for Radix UI components
class MockResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
window.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver

// Mock window.matchMedia for responsive components
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string): MediaQueryList => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {}, // deprecated
    removeListener: () => {}, // deprecated
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
})

// Mock pointer capture methods for Radix UI Select components
// These are not available in JSDOM and cause test failures
Element.prototype.hasPointerCapture = () => false
Element.prototype.setPointerCapture = () => {}
Element.prototype.releasePointerCapture = () => {}

// Mock scrollIntoView for list components
Element.prototype.scrollIntoView = () => {}
