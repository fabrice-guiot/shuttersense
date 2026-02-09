import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './globals.css'
import { initServiceWorkerLifecycle } from './sw-lifecycle'

// Ensure new service worker versions activate immediately and reload the page.
// This must run outside the React tree so it works even if rendering fails.
initServiceWorkerLifecycle()

const rootElement = document.getElementById('root')

if (!rootElement) {
  throw new Error('Failed to find the root element')
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
