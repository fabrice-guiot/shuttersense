import { createContext, useContext, type ReactNode } from 'react'

interface PipelineEditorContextValue {
  pushUndo: () => void
  markDirty: () => void
  isEditable: boolean
  selectedEdgeId: string | null
}

const defaultValue: PipelineEditorContextValue = {
  pushUndo: () => {},
  markDirty: () => {},
  isEditable: false,
  selectedEdgeId: null,
}

const PipelineEditorContext = createContext<PipelineEditorContextValue>(defaultValue)

export function PipelineEditorProvider({
  children,
  pushUndo,
  markDirty,
  isEditable,
  selectedEdgeId,
}: PipelineEditorContextValue & { children: ReactNode }) {
  return (
    <PipelineEditorContext.Provider value={{ pushUndo, markDirty, isEditable, selectedEdgeId }}>
      {children}
    </PipelineEditorContext.Provider>
  )
}

export function usePipelineEditor() {
  return useContext(PipelineEditorContext)
}
