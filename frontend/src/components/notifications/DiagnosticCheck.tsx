/**
 * DiagnosticCheck component
 *
 * Renders a single diagnostic check result row with status icon,
 * label, message, and optional remediation text.
 * Uses both color and icon for accessibility (NFR-04).
 *
 * Issue #025 - PWA Health Diagnostics
 */

import { CheckCircle2, AlertTriangle, XCircle, HelpCircle } from 'lucide-react'
import type { DiagnosticCheck as DiagnosticCheckType } from '@/contracts/pwa-health'

const STATUS_CONFIG = {
  pass: {
    icon: CheckCircle2,
    className: 'text-emerald-500',
  },
  warn: {
    icon: AlertTriangle,
    className: 'text-amber-500',
  },
  fail: {
    icon: XCircle,
    className: 'text-destructive',
  },
  unknown: {
    icon: HelpCircle,
    className: 'text-muted-foreground',
  },
} as const

interface DiagnosticCheckProps {
  check: DiagnosticCheckType
}

export function DiagnosticCheck({ check }: DiagnosticCheckProps) {
  const { icon: Icon, className } = STATUS_CONFIG[check.status]

  return (
    <div className="flex gap-3 py-1.5">
      <Icon className={`h-4 w-4 mt-0.5 shrink-0 ${className}`} />
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-medium">{check.label}</span>
          <span className="text-sm text-muted-foreground truncate">
            {check.message}
          </span>
        </div>
        {check.detail && (
          <pre className="mt-1 text-xs text-muted-foreground whitespace-pre-wrap font-mono">
            {check.detail}
          </pre>
        )}
        {check.remediation && (
          <p className="mt-1 text-xs text-muted-foreground italic">
            {check.remediation}
          </p>
        )}
      </div>
    </div>
  )
}
