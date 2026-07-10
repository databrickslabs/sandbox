import { useCallback, useMemo } from 'react'
import {
  ReactFlow,
  Controls,
  Background,
  type Node,
  type Edge,
  type Connection,
  type NodeChange,
  type EdgeChange,
  Position,
  MarkerType,
  BackgroundVariant,
  applyNodeChanges,
  applyEdgeChanges,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { WiringEdge } from '../../types'
import './WiringCanvas.css'

interface WiringCanvasProps {
  agents: string[]
  edges: WiringEdge[]
  onAgentsChange: (agents: string[]) => void
  onEdgesChange: (edges: WiringEdge[]) => void
  selectedNodeId: string | null
  selectedEdgeId: string | null
  onSelectNode: (agentName: string | null) => void
  onSelectEdge: (edgeId: string | null) => void
  nodePositions: Record<string, { x: number; y: number }>
  onNodePositionsChange: (positions: Record<string, { x: number; y: number }>) => void
}

const AGENT_COLOR = '#1565c0'

export default function WiringCanvas({
  agents,
  edges: wiringEdges,
  onEdgesChange: onWiringEdgesChange,
  selectedNodeId,
  selectedEdgeId,
  onSelectNode,
  onSelectEdge,
  nodePositions,
  onNodePositionsChange,
}: WiringCanvasProps) {
  // Convert system agents to React Flow nodes
  const flowNodes: Node[] = useMemo(() => {
    return agents.map((name, idx) => {
      const pos = nodePositions[name] || { x: 100 + (idx % 3) * 280, y: 80 + Math.floor(idx / 3) * 140 }
      return {
        id: name,
        position: pos,
        data: {
          label: (
            <div className="wiring-node-content">
              <span className="wiring-node-badge" style={{ backgroundColor: AGENT_COLOR }}>
                AGENT
              </span>
              <span className="wiring-node-name">{name}</span>
            </div>
          ),
        },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        className: selectedNodeId === name ? 'wiring-node wiring-node-selected' : 'wiring-node',
      }
    })
  }, [agents, nodePositions, selectedNodeId])

  // Convert wiring edges to React Flow edges
  const flowEdges: Edge[] = useMemo(() => {
    return wiringEdges.map((edge) => {
      const edgeId = `${edge.source_agent}->${edge.target_agent}`
      return {
        id: edgeId,
        source: edge.source_agent,
        target: edge.target_agent,
        label: edge.env_var || 'click to set env var',
        type: 'smoothstep',
        animated: true,
        style: {
          stroke: selectedEdgeId === edgeId ? '#0066cc' : '#666',
          strokeWidth: selectedEdgeId === edgeId ? 3 : 2,
        },
        labelStyle: { fontSize: 11, fill: '#333', fontWeight: selectedEdgeId === edgeId ? 600 : 400 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#666' },
      }
    })
  }, [wiringEdges, selectedEdgeId])

  const handleNodesChange = useCallback((changes: NodeChange[]) => {
    // Apply position changes and track them
    const updated = applyNodeChanges(changes, flowNodes)
    const newPositions = { ...nodePositions }
    for (const node of updated) {
      newPositions[node.id] = node.position
    }
    onNodePositionsChange(newPositions)
  }, [flowNodes, nodePositions, onNodePositionsChange])

  const handleEdgesChange = useCallback((changes: EdgeChange[]) => {
    const updated = applyEdgeChanges(changes, flowEdges)
    // Convert back to WiringEdge format
    const newWiringEdges: WiringEdge[] = updated.map(fe => {
      const existing = wiringEdges.find(
        we => `${we.source_agent}->${we.target_agent}` === fe.id
      )
      return {
        source_agent: fe.source as string,
        target_agent: fe.target as string,
        env_var: existing?.env_var || '',
      }
    })
    onWiringEdgesChange(newWiringEdges)
  }, [flowEdges, wiringEdges, onWiringEdgesChange])

  const handleConnect = useCallback((connection: Connection) => {
    if (!connection.source || !connection.target) return
    if (connection.source === connection.target) return
    // Check for duplicate
    const exists = wiringEdges.some(
      e => e.source_agent === connection.source && e.target_agent === connection.target
    )
    if (exists) return

    const newEdge: WiringEdge = {
      source_agent: connection.source,
      target_agent: connection.target,
      env_var: `${connection.source.toUpperCase().replace(/-/g, '_')}_URL`,
    }
    onWiringEdgesChange([...wiringEdges, newEdge])
    onSelectEdge(`${newEdge.source_agent}->${newEdge.target_agent}`)
  }, [wiringEdges, onWiringEdgesChange, onSelectEdge])

  const handleNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    onSelectNode(node.id)
    onSelectEdge(null)
  }, [onSelectNode, onSelectEdge])

  const handleEdgeClick = useCallback((_event: React.MouseEvent, edge: Edge) => {
    onSelectEdge(edge.id)
    onSelectNode(null)
  }, [onSelectEdge, onSelectNode])

  const handlePaneClick = useCallback(() => {
    onSelectNode(null)
    onSelectEdge(null)
  }, [onSelectNode, onSelectEdge])

  return (
    <div className="wiring-canvas-container">
      {agents.length === 0 ? (
        <div className="wiring-canvas-empty">
          <p>Add agents from the palette to start building a system.</p>
          <p>Then draw connections between them to define wiring.</p>
        </div>
      ) : (
        <ReactFlow
          nodes={flowNodes}
          edges={flowEdges}
          onNodesChange={handleNodesChange}
          onEdgesChange={handleEdgesChange}
          onConnect={handleConnect}
          onNodeClick={handleNodeClick}
          onEdgeClick={handleEdgeClick}
          onPaneClick={handlePaneClick}
          fitView
          fitViewOptions={{ padding: 0.3 }}
          minZoom={0.3}
          maxZoom={2}
          attributionPosition="bottom-left"
          deleteKeyCode="Backspace"
        >
          <Controls />
          <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
        </ReactFlow>
      )}
    </div>
  )
}
