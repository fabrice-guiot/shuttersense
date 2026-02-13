/**
 * Conflict Rules Section Component
 *
 * Displays and edits conflict detection rule settings (distance threshold,
 * consecutive window, travel buffer, colocation radius, performer ceiling).
 *
 * Issue #182 - Calendar Conflict Visualization & Event Picker (Phase 6, US4)
 */

import { useState } from 'react'
import { Shield, Pencil, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import type {
  ConflictRulesResponse,
  ConflictRulesUpdateRequest,
} from '@/contracts/api/conflict-api'

// ============================================================================
// Types
// ============================================================================

interface ConflictRulesSectionProps {
  settings: ConflictRulesResponse | null
  loading?: boolean
  onUpdate: (update: ConflictRulesUpdateRequest) => Promise<void>
}

// ============================================================================
// Constants
// ============================================================================

interface RuleConfig {
  key: keyof ConflictRulesResponse
  label: string
  description: string
  unit: string
  min: number
  max: number
  step: number
}

const RULES: RuleConfig[] = [
  {
    key: 'distance_threshold_miles',
    label: 'Distance Threshold',
    description: 'Maximum distance between venues to flag as a conflict',
    unit: 'miles',
    min: 1,
    max: 500,
    step: 1,
  },
  {
    key: 'consecutive_window_days',
    label: 'Consecutive Window',
    description: 'Window of days to check for consecutive-day conflicts',
    unit: 'days',
    min: 1,
    max: 14,
    step: 1,
  },
  {
    key: 'travel_buffer_days',
    label: 'Travel Buffer',
    description: 'Minimum days required between distant events for travel',
    unit: 'days',
    min: 0,
    max: 7,
    step: 1,
  },
  {
    key: 'colocation_radius_miles',
    label: 'Co-location Radius',
    description: 'Radius within which venues are considered co-located',
    unit: 'miles',
    min: 0.1,
    max: 50,
    step: 0.1,
  },
  {
    key: 'performer_ceiling',
    label: 'Performer Ceiling',
    description: 'Maximum performer count used to normalize lineup scores',
    unit: 'performers',
    min: 1,
    max: 100,
    step: 1,
  },
]

// ============================================================================
// Component
// ============================================================================

export function ConflictRulesSection({
  settings,
  loading = false,
  onUpdate,
}: ConflictRulesSectionProps) {
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [editingRule, setEditingRule] = useState<RuleConfig | null>(null)
  const [editValue, setEditValue] = useState('')

  const handleEdit = (rule: RuleConfig) => {
    setEditingRule(rule)
    setEditValue(settings ? String(settings[rule.key]) : '')
    setFormError(null)
    setEditDialogOpen(true)
  }

  const handleSave = async () => {
    if (!editingRule) return

    const parsed = parseFloat(editValue)
    if (isNaN(parsed)) {
      setFormError('Please enter a valid number')
      return
    }
    if (parsed < editingRule.min) {
      setFormError(`Minimum value is ${editingRule.min}`)
      return
    }
    if (parsed > editingRule.max) {
      setFormError(`Maximum value is ${editingRule.max}`)
      return
    }

    setIsSubmitting(true)
    setFormError(null)
    try {
      await onUpdate({ [editingRule.key]: parsed })
      setEditDialogOpen(false)
    } catch (err: any) {
      setFormError(err.message || 'Update failed')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-muted-foreground" />
          <div>
            <CardTitle className="text-lg">Conflict Detection Rules</CardTitle>
            <CardDescription>
              Configure thresholds and parameters for conflict detection
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-8 w-full bg-muted animate-pulse rounded" />
            ))}
          </div>
        ) : !settings ? (
          <p className="text-sm text-muted-foreground">Unable to load conflict rules</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Rule</TableHead>
                <TableHead>Value</TableHead>
                <TableHead className="w-16">Edit</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {RULES.map(rule => (
                <TableRow key={rule.key}>
                  <TableCell>
                    <div className="font-medium text-sm">{rule.label}</div>
                    <div className="text-xs text-muted-foreground">{rule.description}</div>
                  </TableCell>
                  <TableCell>
                    <span className="font-mono">
                      {settings[rule.key]} {rule.unit}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleEdit(rule)}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>

      <Dialog open={editDialogOpen} onOpenChange={() => setEditDialogOpen(false)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit {editingRule?.label}</DialogTitle>
            <DialogDescription>{editingRule?.description}</DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="ruleValue">
                Value ({editingRule?.unit})
              </Label>
              <Input
                id="ruleValue"
                type="number"
                value={editValue}
                onChange={e => setEditValue(e.target.value)}
                min={editingRule?.min}
                max={editingRule?.max}
                step={editingRule?.step}
              />
              <p className="text-xs text-muted-foreground">
                Range: {editingRule?.min} – {editingRule?.max} {editingRule?.unit}
              </p>
            </div>

            {formError && (
              <Alert variant="destructive">
                <AlertDescription>{formError}</AlertDescription>
              </Alert>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}
