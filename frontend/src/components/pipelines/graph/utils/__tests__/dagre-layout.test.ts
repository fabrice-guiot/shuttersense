import { describe, it, expect } from 'vitest'
import type { Node, Edge } from '@xyflow/react'
import { findBackEdges, applyDagreLayout } from '../dagre-layout'

function makeNode(id: string, type = 'file'): Node {
  return { id, type, position: { x: 0, y: 0 }, data: {}, width: 200, height: 60 }
}

function makeEdge(source: string, target: string): Edge {
  return { id: `${source}-${target}`, source, target }
}

describe('findBackEdges', () => {
  it('returns empty array for a simple DAG', () => {
    const nodes = [makeNode('capture_1', 'capture'), makeNode('file_1'), makeNode('term_1', 'termination')]
    const edges = [makeEdge('capture_1', 'file_1'), makeEdge('file_1', 'term_1')]
    const backEdges = findBackEdges(nodes, edges, 'capture_1')
    expect(backEdges).toHaveLength(0)
  })

  it('detects a single back-edge creating a cycle', () => {
    const nodes = [
      makeNode('capture_1', 'capture'),
      makeNode('file_1'),
      makeNode('process_1', 'process'),
    ]
    const edges = [
      makeEdge('capture_1', 'file_1'),
      makeEdge('file_1', 'process_1'),
      makeEdge('process_1', 'file_1'), // back-edge
    ]
    const backEdges = findBackEdges(nodes, edges, 'capture_1')
    expect(backEdges).toHaveLength(1)
    expect(backEdges[0].id).toBe('process_1-file_1')
  })

  it('detects multiple back-edges', () => {
    const nodes = [
      makeNode('capture_1', 'capture'),
      makeNode('a'),
      makeNode('b'),
      makeNode('c'),
    ]
    const edges = [
      makeEdge('capture_1', 'a'),
      makeEdge('a', 'b'),
      makeEdge('b', 'c'),
      makeEdge('c', 'a'), // back-edge
      makeEdge('b', 'a'), // back-edge
    ]
    const backEdges = findBackEdges(nodes, edges, 'capture_1')
    expect(backEdges.length).toBeGreaterThanOrEqual(2)
  })

  it('handles graph with no capture node gracefully', () => {
    const nodes = [makeNode('a'), makeNode('b')]
    const edges = [makeEdge('a', 'b')]
    const backEdges = findBackEdges(nodes, edges, undefined)
    expect(backEdges).toHaveLength(0)
  })

  it('handles disconnected nodes', () => {
    const nodes = [
      makeNode('capture_1', 'capture'),
      makeNode('file_1'),
      makeNode('orphan'),
    ]
    const edges = [makeEdge('capture_1', 'file_1')]
    const backEdges = findBackEdges(nodes, edges, 'capture_1')
    expect(backEdges).toHaveLength(0)
  })
})

describe('applyDagreLayout', () => {
  it('assigns positions to all nodes', () => {
    const nodes = [makeNode('capture_1', 'capture'), makeNode('file_1'), makeNode('term_1', 'termination')]
    const edges = [makeEdge('capture_1', 'file_1'), makeEdge('file_1', 'term_1')]
    const result = applyDagreLayout(nodes, edges)
    expect(result).toHaveLength(3)
    for (const node of result) {
      expect(node.position.x).toBeDefined()
      expect(node.position.y).toBeDefined()
      expect(Number.isFinite(node.position.x)).toBe(true)
      expect(Number.isFinite(node.position.y)).toBe(true)
    }
  })

  it('positions capture node above termination nodes', () => {
    const nodes = [makeNode('capture_1', 'capture'), makeNode('file_1'), makeNode('term_1', 'termination')]
    const edges = [makeEdge('capture_1', 'file_1'), makeEdge('file_1', 'term_1')]
    const result = applyDagreLayout(nodes, edges)
    const capture = result.find((n) => n.id === 'capture_1')!
    const term = result.find((n) => n.id === 'term_1')!
    expect(capture.position.y).toBeLessThan(term.position.y)
  })

  it('produces non-overlapping positions for nodes at the same level', () => {
    const nodes = [
      makeNode('capture_1', 'capture'),
      makeNode('file_a'),
      makeNode('file_b'),
    ]
    const edges = [makeEdge('capture_1', 'file_a'), makeEdge('capture_1', 'file_b')]
    const result = applyDagreLayout(nodes, edges)
    const fileA = result.find((n) => n.id === 'file_a')!
    const fileB = result.find((n) => n.id === 'file_b')!
    // They should be at same y level but different x
    expect(fileA.position.x).not.toBe(fileB.position.x)
  })

  it('handles cyclic graph without errors', () => {
    const nodes = [
      makeNode('capture_1', 'capture'),
      makeNode('file_1'),
      makeNode('process_1', 'process'),
      makeNode('term_1', 'termination'),
    ]
    const edges = [
      makeEdge('capture_1', 'file_1'),
      makeEdge('file_1', 'process_1'),
      makeEdge('process_1', 'file_1'), // cycle
      makeEdge('process_1', 'term_1'),
    ]
    const result = applyDagreLayout(nodes, edges)
    expect(result).toHaveLength(4)
    for (const node of result) {
      expect(Number.isFinite(node.position.x)).toBe(true)
      expect(Number.isFinite(node.position.y)).toBe(true)
    }
  })

  it('returns empty array for empty graph', () => {
    const result = applyDagreLayout([], [])
    expect(result).toEqual([])
  })

  it('respects direction option', () => {
    const nodes = [makeNode('capture_1', 'capture'), makeNode('file_1')]
    const edges = [makeEdge('capture_1', 'file_1')]

    const tbResult = applyDagreLayout(nodes, edges, { direction: 'TB' })
    const lrResult = applyDagreLayout(nodes, edges, { direction: 'LR' })

    const tbCapture = tbResult.find((n) => n.id === 'capture_1')!
    const tbFile = tbResult.find((n) => n.id === 'file_1')!
    const lrCapture = lrResult.find((n) => n.id === 'capture_1')!
    const lrFile = lrResult.find((n) => n.id === 'file_1')!

    // TB: capture above file (y difference > x difference)
    expect(Math.abs(tbFile.position.y - tbCapture.position.y))
      .toBeGreaterThan(Math.abs(tbFile.position.x - tbCapture.position.x))

    // LR: capture left of file (x difference > y difference)
    expect(Math.abs(lrFile.position.x - lrCapture.position.x))
      .toBeGreaterThan(Math.abs(lrFile.position.y - lrCapture.position.y))
  })
})
