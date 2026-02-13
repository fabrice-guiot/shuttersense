/**
 * Scoring Weights Section Component
 *
 * Displays and edits event quality scoring weights used to compute
 * the composite score for conflict comparison.
 *
 * Issue #182 - Calendar Conflict Visualization & Event Picker (Phase 6, US4)
 */

import { useState } from 'react'
import { SlidersHorizontal, Pencil, Loader2 } from 'lucide-react'
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
  ScoringWeightsResponse,
  ScoringWeightsUpdateRequest,
} from '@/contracts/api/conflict-api'

// ============================================================================
// Types
// ============================================================================

interface ScoringWeightsSectionProps {
  settings: ScoringWeightsResponse | null
  loading?: boolean
  onUpdate: (update: ScoringWeightsUpdateRequest) => Promise<void>
}

// ============================================================================
// Constants
// ============================================================================

interface WeightConfig {
  key: keyof ScoringWeightsResponse
  label: string
  description: string
}

const WEIGHTS: WeightConfig[] = [
  {
    key: 'weight_venue_quality',
    label: 'Venue Quality',
    description: 'Weight for location/venue rating in the composite score',
  },
  {
    key: 'weight_organizer_reputation',
    label: 'Organizer Reputation',
    description: 'Weight for event organizer rating in the composite score',
  },
  {
    key: 'weight_performer_lineup',
    label: 'Performer Lineup',
    description: 'Weight for confirmed performer count in the composite score',
  },
  {
    key: 'weight_logistics_ease',
    label: 'Logistics Ease',
    description: 'Weight for travel/accommodation logistics in the composite score',
  },
  {
    key: 'weight_readiness',
    label: 'Readiness',
    description: 'Weight for event readiness status in the composite score',
  },
]

// ============================================================================
// Helpers
// ============================================================================

function computePercentage(value: number, total: number): string {
  if (total === 0) return '0%'
  return `${Math.round((value / total) * 100)}%`
}

// ============================================================================
// Component
// ============================================================================

export function ScoringWeightsSection({
  settings,
  loading = false,
  onUpdate,
}: ScoringWeightsSectionProps) {
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [editingWeight, setEditingWeight] = useState<WeightConfig | null>(null)
  const [editValue, setEditValue] = useState('')

  const totalWeight = settings
    ? WEIGHTS.reduce((sum, w) => sum + settings[w.key], 0)
    : 0

  const handleEdit = (weight: WeightConfig) => {
    setEditingWeight(weight)
    setEditValue(settings ? String(settings[weight.key]) : '')
    setFormError(null)
    setEditDialogOpen(true)
  }

  const handleSave = async () => {
    if (!editingWeight) return

    const parsed = parseFloat(editValue)
    if (isNaN(parsed)) {
      setFormError('Please enter a valid number')
      return
    }
    if (parsed < 0) {
      setFormError('Weight cannot be negative')
      return
    }
    if (parsed > 10) {
      setFormError('Weight cannot exceed 10')
      return
    }

    setIsSubmitting(true)
    setFormError(null)
    try {
      await onUpdate({ [editingWeight.key]: parsed })
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
          <SlidersHorizontal className="h-5 w-5 text-muted-foreground" />
          <div>
            <CardTitle className="text-lg">Event Scoring Weights</CardTitle>
            <CardDescription>
              Adjust how each dimension contributes to the composite event score
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
          <p className="text-sm text-muted-foreground">Unable to load scoring weights</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Dimension</TableHead>
                <TableHead>Weight</TableHead>
                <TableHead>Share</TableHead>
                <TableHead className="w-16">Edit</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {WEIGHTS.map(weight => (
                <TableRow key={weight.key}>
                  <TableCell>
                    <div className="font-medium text-sm">{weight.label}</div>
                    <div className="text-xs text-muted-foreground">{weight.description}</div>
                  </TableCell>
                  <TableCell>
                    <span className="font-mono">{settings[weight.key]}</span>
                  </TableCell>
                  <TableCell>
                    <span className="text-muted-foreground">
                      {computePercentage(settings[weight.key], totalWeight)}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleEdit(weight)}
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
            <DialogTitle>Edit {editingWeight?.label} Weight</DialogTitle>
            <DialogDescription>{editingWeight?.description}</DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="weightValue">Weight</Label>
              <Input
                id="weightValue"
                type="number"
                value={editValue}
                onChange={e => setEditValue(e.target.value)}
                min={0}
                max={10}
                step={0.1}
              />
              <p className="text-xs text-muted-foreground">
                Enter a value between 0 and 10. Weights are normalized to percentages.
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
