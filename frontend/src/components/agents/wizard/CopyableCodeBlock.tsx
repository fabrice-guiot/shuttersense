/**
 * CopyableCodeBlock — a code/command display with a per-block Copy button.
 *
 * Uses the useClipboard hook for clipboard access with Copy→Check visual feedback.
 *
 * Issue #136 - Agent Setup Wizard (FR-024)
 */

import { Check, Copy } from 'lucide-react'
import { useClipboard } from '@/hooks/useClipboard'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'

interface CopyableCodeBlockProps {
  /** The text content to display and copy */
  children: string
  /** Optional label for the copy button (used as aria-label) */
  label?: string
  /** Optional language hint for syntax highlighting context (informational only) */
  language?: string
  /** Additional CSS classes for the outer container */
  className?: string
}

export function CopyableCodeBlock({
  children,
  label,
  language,
  className,
}: CopyableCodeBlockProps) {
  const { copy, copied } = useClipboard()

  const ariaLabel = label ? `Copy ${label}` : 'Copy to clipboard'

  return (
    <div className={cn('group relative', className)}>
      <pre
        className={cn(
          'overflow-x-auto rounded-md border bg-muted p-4 pr-12 text-sm',
          'font-mono whitespace-pre-wrap break-all'
        )}
        data-language={language}
      >
        <code>{children}</code>
      </pre>
      <Button
        variant="ghost"
        size="icon"
        className="absolute right-2 top-2 h-8 w-8 opacity-0 transition-opacity group-hover:opacity-100 focus:opacity-100"
        onClick={() => copy(children)}
        aria-label={ariaLabel}
      >
        {copied ? (
          <Check className="h-4 w-4 text-green-600" />
        ) : (
          <Copy className="h-4 w-4 text-muted-foreground" />
        )}
      </Button>
    </div>
  )
}
