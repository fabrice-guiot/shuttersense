/**
 * Tests for ServiceStep component (Step 5: Background Service Setup)
 *
 * Issue #136 - Agent Setup Wizard (FR-018 through FR-022)
 * Task: T054
 */

import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../../../utils/test-utils'
import { ServiceStep } from '@/components/agents/wizard/ServiceStep'

describe('ServiceStep', () => {
  describe('macOS (darwin-arm64)', () => {
    it('renders binary path input with macOS default', () => {
      render(<ServiceStep selectedPlatform="darwin-arm64" />)

      const input = screen.getByLabelText(/Agent Binary Path/i)
      expect(input).toHaveValue('/usr/local/bin/shuttersense-agent')
    })

    it('shows launchd service setup sections with valid path', () => {
      render(<ServiceStep selectedPlatform="darwin-arm64" />)

      // Check numbered instruction steps
      expect(screen.getByText('1. Download the service configuration file')).toBeInTheDocument()
      expect(screen.getByText('2. Install and start the service')).toBeInTheDocument()
      expect(screen.getByText('3. Manage the service')).toBeInTheDocument()
    })

    it('does not show service user input for macOS', () => {
      render(<ServiceStep selectedPlatform="darwin-arm64" />)

      expect(screen.queryByLabelText(/Service User/i)).not.toBeInTheDocument()
    })

    it('has a download button for the plist file', () => {
      render(<ServiceStep selectedPlatform="darwin-arm64" />)

      const downloadBtn = screen.getByRole('button', { name: /Download ai\.shuttersense\.agent\.plist/i })
      expect(downloadBtn).toBeInTheDocument()
    })

    it('mentions /Library/LaunchDaemons/ destination', () => {
      render(<ServiceStep selectedPlatform="darwin-arm64" />)

      // The code element containing the path
      const codeEl = screen.getByText('/Library/LaunchDaemons/')
      expect(codeEl).toBeInTheDocument()
    })

    it('has a download button for the newsyslog config', () => {
      render(<ServiceStep selectedPlatform="darwin-arm64" />)

      const downloadBtn = screen.getByRole('button', { name: /Download shuttersense\.conf/i })
      expect(downloadBtn).toBeInTheDocument()
    })

    it('shows log rotation section with explanation', () => {
      render(<ServiceStep selectedPlatform="darwin-arm64" />)

      expect(screen.getByText(/Configure log rotation/i)).toBeInTheDocument()
      expect(screen.getByText(/Without log rotation/i)).toBeInTheDocument()
    })

    it('has expandable file contents for plist and newsyslog', async () => {
      const user = userEvent.setup()
      render(<ServiceStep selectedPlatform="darwin-arm64" />)

      // Should have two expandable sections: plist and newsyslog
      const summaries = screen.getAllByText(/View file contents/i)
      expect(summaries).toHaveLength(2)

      // Expand the plist section
      await user.click(summaries[0])
      expect(screen.getByLabelText(/Copy launchd plist/i)).toBeInTheDocument()

      // Expand the newsyslog section
      await user.click(summaries[1])
      expect(screen.getByLabelText(/Copy newsyslog config/i)).toBeInTheDocument()
    })
  })

  describe('macOS Intel (darwin-amd64)', () => {
    it('renders with macOS default path for Intel', () => {
      render(<ServiceStep selectedPlatform="darwin-amd64" />)

      const input = screen.getByLabelText(/Agent Binary Path/i)
      expect(input).toHaveValue('/usr/local/bin/shuttersense-agent')
    })
  })

  describe('Linux (linux-amd64)', () => {
    it('renders binary path input with Linux default', () => {
      render(<ServiceStep selectedPlatform="linux-amd64" />)

      const input = screen.getByLabelText(/Agent Binary Path/i)
      expect(input).toHaveValue('/usr/local/bin/shuttersense-agent')
    })

    it('shows service user input for Linux', () => {
      render(<ServiceStep selectedPlatform="linux-amd64" />)

      const userInput = screen.getByRole('textbox', { name: /Service User/i })
      expect(userInput).toHaveValue('shuttersense')
    })

    it('shows systemd service setup sections with valid path', () => {
      render(<ServiceStep selectedPlatform="linux-amd64" />)

      expect(screen.getByText('1. Download the service configuration file')).toBeInTheDocument()
      expect(screen.getByText('2. Install and start the service')).toBeInTheDocument()
      expect(screen.getByText('3. Manage the service')).toBeInTheDocument()
    })

    it('shows useradd command with service user', () => {
      render(<ServiceStep selectedPlatform="linux-amd64" />)

      expect(screen.getByLabelText(/Copy create service user/i)).toBeInTheDocument()
    })

    it('mentions /etc/systemd/system/ destination', () => {
      render(<ServiceStep selectedPlatform="linux-amd64" />)

      const codeEl = screen.getByText('/etc/systemd/system/')
      expect(codeEl).toBeInTheDocument()
    })

    it('has a download button for the unit file', () => {
      render(<ServiceStep selectedPlatform="linux-amd64" />)

      const downloadBtn = screen.getByRole('button', { name: /Download shuttersense-agent\.service/i })
      expect(downloadBtn).toBeInTheDocument()
    })
  })

  describe('Windows (windows-amd64)', () => {
    it('shows unsupported message for Windows', () => {
      render(<ServiceStep selectedPlatform="windows-amd64" />)

      expect(screen.getByText(/not yet supported/i)).toBeInTheDocument()
    })

    it('suggests Windows Task Scheduler', () => {
      render(<ServiceStep selectedPlatform="windows-amd64" />)

      expect(screen.getByText(/Task Scheduler/i)).toBeInTheDocument()
    })

    it('does not show binary path input for Windows', () => {
      render(<ServiceStep selectedPlatform="windows-amd64" />)

      expect(screen.queryByLabelText(/Agent Binary Path/i)).not.toBeInTheDocument()
    })

    it('instructs user to click Next', () => {
      render(<ServiceStep selectedPlatform="windows-amd64" />)

      expect(screen.getByText(/Next/)).toBeInTheDocument()
    })
  })

  describe('path validation', () => {
    it('shows error for relative Unix path', async () => {
      const user = userEvent.setup()
      render(<ServiceStep selectedPlatform="linux-amd64" />)

      const input = screen.getByLabelText(/Agent Binary Path/i)
      await user.clear(input)
      await user.type(input, 'relative/path/agent')

      expect(screen.getByText(/Path must be absolute/i)).toBeInTheDocument()
    })

    it('shows warning for path with spaces', async () => {
      const user = userEvent.setup()
      render(<ServiceStep selectedPlatform="darwin-arm64" />)

      const input = screen.getByLabelText(/Agent Binary Path/i)
      await user.clear(input)
      await user.type(input, '/usr/local/my folder/agent')

      expect(screen.getByText(/Path contains spaces/i)).toBeInTheDocument()
    })

    it('hides service config when path is empty', async () => {
      const user = userEvent.setup()
      render(<ServiceStep selectedPlatform="darwin-arm64" />)

      const input = screen.getByLabelText(/Agent Binary Path/i)
      await user.clear(input)

      // Service install sections should not be visible
      expect(screen.queryByText('2. Install and start the service')).not.toBeInTheDocument()
    })

    it('hides service config when path is invalid', async () => {
      const user = userEvent.setup()
      render(<ServiceStep selectedPlatform="linux-amd64" />)

      const input = screen.getByLabelText(/Agent Binary Path/i)
      await user.clear(input)
      await user.type(input, 'not-absolute')

      expect(screen.queryByText('2. Install and start the service')).not.toBeInTheDocument()
    })
  })

  describe('skippable step', () => {
    it('mentions the step is optional', () => {
      render(<ServiceStep selectedPlatform="darwin-arm64" />)

      expect(screen.getByText(/optional/i)).toBeInTheDocument()
    })
  })
})
