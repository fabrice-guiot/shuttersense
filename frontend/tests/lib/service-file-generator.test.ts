/**
 * Unit tests for service file generators.
 *
 * Tests cover:
 *   - macOS launchd plist generation
 *   - Linux systemd unit generation
 *   - Various binary paths (standard, with spaces, edge cases)
 *
 * Issue #136 - Agent Setup Wizard
 */

import { describe, it, expect } from 'vitest'
import {
  generateLaunchdPlist,
  generateSystemdUnit,
} from '@/lib/service-file-generator'

describe('generateLaunchdPlist', () => {
  it('should generate valid plist XML with standard path', () => {
    const plist = generateLaunchdPlist('/usr/local/bin/shuttersense-agent')

    expect(plist).toContain('<?xml version="1.0" encoding="UTF-8"?>')
    expect(plist).toContain('<!DOCTYPE plist')
    expect(plist).toContain('<plist version="1.0">')
    expect(plist).toContain('</plist>')
  })

  it('should include the correct service label', () => {
    const plist = generateLaunchdPlist('/usr/local/bin/shuttersense-agent')
    expect(plist).toContain('<string>ai.shuttersense.agent</string>')
  })

  it('should include the binary path in ProgramArguments', () => {
    const plist = generateLaunchdPlist('/usr/local/bin/shuttersense-agent')
    expect(plist).toContain('<string>/usr/local/bin/shuttersense-agent</string>')
    expect(plist).toContain('<string>start</string>')
  })

  it('should configure RunAtLoad and KeepAlive', () => {
    const plist = generateLaunchdPlist('/usr/local/bin/shuttersense-agent')
    expect(plist).toContain('<key>RunAtLoad</key>')
    expect(plist).toContain('<key>KeepAlive</key>')
  })

  it('should configure log paths', () => {
    const plist = generateLaunchdPlist('/usr/local/bin/shuttersense-agent')
    expect(plist).toContain('shuttersense-agent.stdout.log')
    expect(plist).toContain('shuttersense-agent.stderr.log')
    expect(plist).toContain('/var/log/shuttersense/')
  })

  it('should handle path with spaces', () => {
    const plist = generateLaunchdPlist('/Applications/ShutterSense Agent/shuttersense-agent')
    expect(plist).toContain('<string>/Applications/ShutterSense Agent/shuttersense-agent</string>')
  })

  it('should handle path in user home directory', () => {
    const plist = generateLaunchdPlist('/Users/admin/bin/shuttersense-agent')
    expect(plist).toContain('<string>/Users/admin/bin/shuttersense-agent</string>')
  })

  it('should handle empty path (produces output with empty string)', () => {
    const plist = generateLaunchdPlist('')
    expect(plist).toContain('<string></string>')
    // Still valid XML structure
    expect(plist).toContain('</plist>')
  })
})

describe('generateSystemdUnit', () => {
  it('should generate valid systemd unit structure', () => {
    const unit = generateSystemdUnit('/usr/local/bin/shuttersense-agent', 'shuttersense')

    expect(unit).toContain('[Unit]')
    expect(unit).toContain('[Service]')
    expect(unit).toContain('[Install]')
  })

  it('should include correct description', () => {
    const unit = generateSystemdUnit('/usr/local/bin/shuttersense-agent', 'shuttersense')
    expect(unit).toContain('Description=ShutterSense Agent')
  })

  it('should configure network dependency', () => {
    const unit = generateSystemdUnit('/usr/local/bin/shuttersense-agent', 'shuttersense')
    expect(unit).toContain('After=network-online.target')
    expect(unit).toContain('Wants=network-online.target')
  })

  it('should include binary path in ExecStart', () => {
    const unit = generateSystemdUnit('/usr/local/bin/shuttersense-agent', 'shuttersense')
    expect(unit).toContain('ExecStart="/usr/local/bin/shuttersense-agent" start')
  })

  it('should configure restart policy', () => {
    const unit = generateSystemdUnit('/usr/local/bin/shuttersense-agent', 'shuttersense')
    expect(unit).toContain('Restart=always')
    expect(unit).toContain('RestartSec=10')
  })

  it('should include the specified user', () => {
    const unit = generateSystemdUnit('/usr/local/bin/shuttersense-agent', 'shuttersense')
    expect(unit).toContain('User=shuttersense')
  })

  it('should configure multi-user target', () => {
    const unit = generateSystemdUnit('/usr/local/bin/shuttersense-agent', 'shuttersense')
    expect(unit).toContain('WantedBy=multi-user.target')
  })

  it('should handle custom user', () => {
    const unit = generateSystemdUnit('/usr/local/bin/shuttersense-agent', 'deploy')
    expect(unit).toContain('User=deploy')
    expect(unit).not.toContain('User=shuttersense')
  })

  it('should handle path with spaces', () => {
    const unit = generateSystemdUnit('/opt/shutter sense/shuttersense-agent', 'shuttersense')
    expect(unit).toContain('ExecStart="/opt/shutter sense/shuttersense-agent" start')
  })

  it('should handle empty path', () => {
    const unit = generateSystemdUnit('', 'shuttersense')
    expect(unit).toContain('ExecStart="" start')
    // Still valid unit structure
    expect(unit).toContain('[Install]')
  })

  it('should handle empty user', () => {
    const unit = generateSystemdUnit('/usr/local/bin/shuttersense-agent', '')
    expect(unit).toContain('User=')
  })
})
