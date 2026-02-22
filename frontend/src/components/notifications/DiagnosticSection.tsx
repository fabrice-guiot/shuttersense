/**
 * DiagnosticSection component
 *
 * Collapsible group of diagnostic checks with a section header
 * showing title and overall status badge. Auto-expands if
 * the section has warnings or failures.
 *
 * Issue #025 - PWA Health Diagnostics
 */

import { useState } from 'react'
import { ChevronRight } from 'lucide-react'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Badge } from '@/components/ui/badge'
import { DiagnosticCheck } from './DiagnosticCheck'
import type { DiagnosticSection as DiagnosticSectionType } from '@/contracts/pwa-health'

const STATUS_BADGE = {
  pass: { label: 'OK', variant: 'success' as const },
  warn: { label: 'Warning', variant: 'warning' as const },
  fail: { label: 'Error', variant: 'destructive' as const },
  unknown: { label: 'Unknown', variant: 'muted' as const },
}

interface DiagnosticSectionProps {
  section: DiagnosticSectionType
}

export function DiagnosticSection({ section }: DiagnosticSectionProps) {
  const hasIssues = section.overallStatus === 'warn' || section.overallStatus === 'fail'
  const [open, setOpen] = useState(hasIssues)
  const badge = STATUS_BADGE[section.overallStatus]

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left hover:bg-muted/50 transition-colors">
        <ChevronRight
          className={`h-4 w-4 shrink-0 text-muted-foreground transition-transform ${open ? 'rotate-90' : ''}`}
        />
        <span className="flex-1 text-sm font-semibold">{section.title}</span>
        <Badge variant={badge.variant} className="text-xs">
          {badge.label}
        </Badge>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="ml-6 border-l border-border pl-4 pb-2">
          {section.checks.map((check) => (
            <DiagnosticCheck key={check.id} check={check} />
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}
