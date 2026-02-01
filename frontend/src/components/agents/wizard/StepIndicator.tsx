/**
 * StepIndicator — numbered step progress bar for the Agent Setup Wizard.
 *
 * Displays step numbers with titles, highlighting the current step.
 * Uses aria-current="step" for accessibility.
 *
 * Issue #136 - Agent Setup Wizard (FR-003, FR-800.1, FR-800.4)
 */

import { cn } from '@/lib/utils'

export const WIZARD_STEPS = [
  { number: 1, title: 'Download Agent' },
  { number: 2, title: 'Create Token' },
  { number: 3, title: 'Register Agent' },
  { number: 4, title: 'Launch Agent' },
  { number: 5, title: 'Background Service' },
  { number: 6, title: 'Summary' },
] as const

interface StepIndicatorProps {
  currentStep: number
}

export function StepIndicator({ currentStep }: StepIndicatorProps) {
  return (
    <nav aria-label="Setup progress" className="flex items-center gap-1 overflow-x-auto py-2">
      {WIZARD_STEPS.map((step, index) => {
        const isActive = step.number === currentStep
        const isCompleted = step.number < currentStep

        return (
          <div key={step.number} className="flex items-center">
            {index > 0 && (
              <div
                className={cn(
                  'h-px w-4 sm:w-6 flex-shrink-0',
                  isCompleted ? 'bg-primary' : 'bg-border'
                )}
              />
            )}
            <div
              className="flex items-center gap-1.5 flex-shrink-0"
              aria-current={isActive ? 'step' : undefined}
            >
              <div
                className={cn(
                  'flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium',
                  isActive && 'bg-primary text-primary-foreground',
                  isCompleted && 'bg-primary/20 text-primary',
                  !isActive && !isCompleted && 'bg-muted text-muted-foreground'
                )}
              >
                {step.number}
              </div>
              <span
                className={cn(
                  'text-xs hidden sm:inline whitespace-nowrap',
                  isActive && 'font-medium text-foreground',
                  !isActive && 'text-muted-foreground'
                )}
              >
                {step.title}
              </span>
            </div>
          </div>
        )
      })}
    </nav>
  )
}
