import type { NodeTypes } from '@xyflow/react'
import CaptureNode from './CaptureNode'
import FileNode from './FileNode'
import ProcessNode from './ProcessNode'
import PairingNode from './PairingNode'
import BranchingNode from './BranchingNode'
import TerminationNode from './TerminationNode'

export {
  CaptureNode,
  FileNode,
  ProcessNode,
  PairingNode,
  BranchingNode,
  TerminationNode,
}

export const nodeTypes: NodeTypes = {
  capture: CaptureNode,
  file: FileNode,
  process: ProcessNode,
  pairing: PairingNode,
  branching: BranchingNode,
  termination: TerminationNode,
}
