import { useMemo, useCallback } from 'react'
import {
  ReactFlow,
  Controls,
  Background,
  type Node,
  type Edge,
  Position,
  MarkerType,
  BackgroundVariant,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { LineageNode, LineageEdge } from '../../types'
import './LineageGraph.css'

interface LineageGraphProps {
  nodes: LineageNode[]
  edges: LineageEdge[]
  rootType: string
  rootId: number
  onNodeClick?: (assetType: string, assetId: number) => void
}

const TYPE_COLORS: Record<string, string> = {
  table: '#1a73e8',
  view: '#34a853',
  function: '#f9ab00',
  model: '#ea4335',
  volume: '#9e9e9e',
  notebook: '#7b1fa2',
  job: '#00897b',
  dashboard: '#e65100',
  pipeline: '#c2185b',
  cluster: '#546e7a',
  experiment: '#2e7d32',
  app: '#1565c0',
  tool: '#ef6c00',
  server: '#757575',
}

const TYPE_LABELS: Record<string, string> = {
  table: 'TBL',
  view: 'VW',
  function: 'FN',
  model: 'MDL',
  volume: 'VOL',
  notebook: 'NB',
  job: 'JOB',
  dashboard: 'DASH',
  pipeline: 'PIPE',
  cluster: 'CLU',
  experiment: 'EXP',
  app: 'APP',
  tool: 'TOOL',
  server: 'SRV',
}

const REL_COLORS: Record<string, string> = {
  reads_from: '#1a73e8',
  writes_to: '#ea4335',
  depends_on: '#f9ab00',
  scheduled_by: '#00897b',
  created_by: '#7b1fa2',
  uses_model: '#e65100',
  derived_from: '#546e7a',
  consumes: '#1565c0',
}

export default function LineageGraph({
  nodes: lineageNodes,
  edges: lineageEdges,
  rootType,
  rootId,
  onNodeClick,
}: LineageGraphProps) {
  // Convert lineage data to React Flow nodes with auto-layout
  const { flowNodes, flowEdges } = useMemo(() => {
    // Group nodes by depth for layered layout
    const depthGroups = new Map<number, LineageNode[]>()
    for (const node of lineageNodes) {
      const depth = node.depth ?? 0
      if (!depthGroups.has(depth)) depthGroups.set(depth, [])
      depthGroups.get(depth)!.push(node)
    }

    const sortedDepths = Array.from(depthGroups.keys()).sort((a, b) => a - b)

    const flowNodes: Node[] = []
    const nodePositions = new Map<string, { x: number; y: number }>()

    const LAYER_GAP = 280
    const NODE_GAP = 120

    for (const depth of sortedDepths) {
      const group = depthGroups.get(depth)!
      const startY = -(group.length - 1) * NODE_GAP / 2

      group.forEach((node, idx) => {
        const nodeKey = `${node.asset_type}-${node.asset_id}`
        const x = depth * LAYER_GAP
        const y = startY + idx * NODE_GAP
        nodePositions.set(nodeKey, { x, y })

        const isRoot = node.asset_type === rootType && node.asset_id === rootId
        const color = TYPE_COLORS[node.asset_type] || '#757575'
        const shortName = node.name.split('.').pop() || node.name

        flowNodes.push({
          id: nodeKey,
          position: { x, y },
          data: {
            label: (
              <div className="lineage-node-content" style={{ borderLeftColor: color }}>
                <span className="lineage-node-badge" style={{ backgroundColor: color }}>
                  {TYPE_LABELS[node.asset_type] || node.asset_type.toUpperCase().slice(0, 3)}
                </span>
                <span className="lineage-node-name" title={node.name}>
                  {shortName}
                </span>
              </div>
            ),
          },
          sourcePosition: Position.Right,
          targetPosition: Position.Left,
          className: isRoot ? 'lineage-node lineage-node-root' : 'lineage-node',
          style: isRoot ? { boxShadow: `0 0 0 3px ${color}40` } : undefined,
        })
      })
    }

    const flowEdges: Edge[] = lineageEdges.map((edge, idx) => {
      const sourceKey = `${edge.source_type}-${edge.source_id}`
      const targetKey = `${edge.target_type}-${edge.target_id}`
      const color = REL_COLORS[edge.relationship_type] || '#999'

      return {
        id: `e-${idx}`,
        source: sourceKey,
        target: targetKey,
        label: edge.relationship_type.replace(/_/g, ' '),
        type: 'smoothstep',
        animated: edge.relationship_type === 'reads_from' || edge.relationship_type === 'writes_to',
        style: { stroke: color, strokeWidth: 2 },
        labelStyle: { fontSize: 10, fill: '#666' },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color,
        },
      }
    })

    return { flowNodes, flowEdges }
  }, [lineageNodes, lineageEdges, rootType, rootId])

  const handleNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    const [type, idStr] = node.id.split('-')
    const id = parseInt(idStr, 10)
    if (type && !isNaN(id)) {
      onNodeClick?.(type, id)
    }
  }, [onNodeClick])

  if (flowNodes.length === 0) {
    return (
      <div className="lineage-empty">
        <p>No lineage data available for this asset.</p>
        <p>Run "Crawl Lineage" to discover relationships.</p>
      </div>
    )
  }

  return (
    <div className="lineage-graph-container">
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        onNodeClick={handleNodeClick}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        minZoom={0.2}
        maxZoom={2}
        attributionPosition="bottom-left"
      >
        <Controls />
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
      </ReactFlow>
    </div>
  )
}
