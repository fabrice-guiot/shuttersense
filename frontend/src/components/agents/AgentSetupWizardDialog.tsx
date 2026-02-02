/**
 * AgentSetupWizardDialog — Root wizard dialog for guided agent setup.
 *
 * 6-step wizard: Download Agent, Create Token, Register Agent,
 * Launch Agent, Background Service, Summary.
 *
 * Issue #136 - Agent Setup Wizard (FR-002, FR-012, FR-013, FR-025, FR-026, FR-028, FR-029, FR-030)
 */

import { useState, useCallback } from 'react'
import { ArrowLeft, ArrowRight, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Separator } from '@/components/ui/separator'

import { StepIndicator, WIZARD_STEPS } from '@/components/agents/wizard/StepIndicator'
import { DownloadStep } from '@/components/agents/wizard/DownloadStep'
import { TokenStep } from '@/components/agents/wizard/TokenStep'
import { RegisterStep, getServerUrl } from '@/components/agents/wizard/RegisterStep'
import { LaunchStep } from '@/components/agents/wizard/LaunchStep'
import { ServiceStep } from '@/components/agents/wizard/ServiceStep'
import { SummaryStep } from '@/components/agents/wizard/SummaryStep'

import { detectPlatform } from '@/lib/os-detection'
import type { ValidPlatform } from '@/contracts/api/release-manifests-api'
import type { RegistrationToken } from '@/contracts/api/agent-api'

const TOTAL_STEPS = WIZARD_STEPS.length

interface AgentSetupWizardDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  createToken: (data?: { name?: string; expires_in_hours?: number }) => Promise<RegistrationToken>
  /** Called when wizard closes after a token was created */
  onComplete?: () => void
}

export function AgentSetupWizardDialog({
  open,
  onOpenChange,
  createToken,
  onComplete,
}: AgentSetupWizardDialogProps) {
  // Wizard state
  const [currentStep, setCurrentStep] = useState(1)
  const [createdToken, setCreatedToken] = useState<RegistrationToken | null>(null)
  const [confirmCloseOpen, setConfirmCloseOpen] = useState(false)
  const [hasLeftTokenStep, setHasLeftTokenStep] = useState(false)

  // Platform detection (runs once on mount)
  const [detected] = useState(() => detectPlatform())
  const [selectedPlatform, setSelectedPlatform] = useState<ValidPlatform>(detected.platform as ValidPlatform)

  const serverUrl = getServerUrl()

  // Navigation
  const canGoNext = currentStep === 2 ? createdToken !== null : true
  const isLastStep = currentStep === TOTAL_STEPS

  const handleNext = () => {
    if (currentStep === 2 && createdToken) {
      setHasLeftTokenStep(true)
    }
    if (currentStep < TOTAL_STEPS) {
      setCurrentStep((s) => s + 1)
    }
  }

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep((s) => s - 1)
    }
  }

  const handleTokenCreated = (token: RegistrationToken) => {
    setCreatedToken(token)
  }

  // Close behavior (FR-026, FR-800.7)
  const handleClose = useCallback(() => {
    // If token created and not on summary, show confirmation
    if (createdToken && currentStep !== TOTAL_STEPS) {
      setConfirmCloseOpen(true)
      return
    }
    doClose()
  }, [createdToken, currentStep])

  const doClose = useCallback(() => {
    const hadToken = createdToken !== null
    onOpenChange(false)

    // Reset state after close animation (200ms)
    setTimeout(() => {
      setCurrentStep(1)
      setCreatedToken(null)
      setHasLeftTokenStep(false)
      setSelectedPlatform(detected.platform as ValidPlatform)
      setConfirmCloseOpen(false)
    }, 200)

    // Notify parent to refresh lists if a token was created
    if (hadToken && onComplete) {
      onComplete()
    }
  }, [createdToken, detected.platform, onComplete, onOpenChange])

  const handleDone = () => {
    doClose()
  }

  const handleConfirmClose = () => {
    setConfirmCloseOpen(false)
    doClose()
  }

  // Render current step content
  const renderStep = () => {
    switch (currentStep) {
      case 1:
        return (
          <DownloadStep
            detectedPlatform={detected.platform as ValidPlatform}
            selectedPlatform={selectedPlatform}
            onPlatformChange={setSelectedPlatform}
            platformConfidence={detected.confidence}
          />
        )
      case 2:
        return (
          <TokenStep
            createdToken={createdToken}
            onTokenCreated={handleTokenCreated}
            createToken={createToken}
            isRevisit={hasLeftTokenStep}
          />
        )
      case 3:
        return (
          <RegisterStep
            token={createdToken?.token ?? '(create a token in Step 2)'}
            serverUrl={serverUrl}
            selectedPlatform={selectedPlatform}
          />
        )
      case 4:
        return (
          <LaunchStep
            token={createdToken?.token ?? ''}
            serverUrl={serverUrl}
            selectedPlatform={selectedPlatform}
          />
        )
      case 5:
        return <ServiceStep selectedPlatform={selectedPlatform} />
      case 6:
        return (
          <SummaryStep
            selectedPlatform={selectedPlatform}
            tokenName={createdToken?.name ?? null}
            serverUrl={serverUrl}
          />
        )
      default:
        return null
    }
  }

  return (
    <>
      <Dialog open={open} onOpenChange={(isOpen) => { if (!isOpen) handleClose() }}>
        <DialogContent className="max-w-4xl max-h-[90vh] flex flex-col p-4 sm:p-6">
          <DialogHeader>
            <DialogTitle>Agent Setup Wizard</DialogTitle>
            <DialogDescription>
              Follow these steps to install and register a new ShutterSense agent.
            </DialogDescription>
          </DialogHeader>

          <StepIndicator currentStep={currentStep} />

          <Separator />

          {/* Step content — scrollable */}
          <div className="flex-1 overflow-y-auto py-4 min-h-0">
            {renderStep()}
          </div>

          <Separator />

          <DialogFooter className="gap-2 sm:gap-0">
            {currentStep > 1 && (
              <Button variant="outline" onClick={handleBack} className="mr-auto" aria-label="Go to previous step">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Button>
            )}
            {isLastStep ? (
              <Button onClick={handleDone} aria-label="Finish wizard">
                <Check className="h-4 w-4 mr-2" />
                Done
              </Button>
            ) : (
              <Button onClick={handleNext} disabled={!canGoNext} aria-label="Go to next step">
                Next
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Close confirmation dialog */}
      <AlertDialog open={confirmCloseOpen} onOpenChange={setConfirmCloseOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Close wizard?</AlertDialogTitle>
            <AlertDialogDescription>
              You have created a registration token in this session. If you close now, make sure you have copied the token — it will not be shown again.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Continue Setup</AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmClose}>
              Close Wizard
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
