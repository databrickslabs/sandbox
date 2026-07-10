import { useState, useEffect, useCallback } from 'react'
import { SystemDefinition, WiringEdge, DeployResult } from '../types'
import { systemsApi } from '../api/systems'
import ThreePanel from '../components/chat/ThreePanel'
import AgentPalette from '../components/systems/AgentPalette'
import WiringCanvas from '../components/systems/WiringCanvas'
import PropertiesPanel from '../components/systems/PropertiesPanel'
import './SystemBuilderPage.css'

export default function SystemBuilderPage() {
  // System list state
  const [systems, setSystems] = useState<SystemDefinition[]>([])
  const [activeSystemId, setActiveSystemId] = useState<string | null>(null)

  // Current system editing state
  const [systemName, setSystemName] = useState('New System')
  const [systemDesc, setSystemDesc] = useState('')
  const [agents, setAgents] = useState<string[]>([])
  const [edges, setEdges] = useState<WiringEdge[]>([])
  const [ucCatalog, setUcCatalog] = useState('')
  const [ucSchema, setUcSchema] = useState('')

  // UI state
  const [selectedNode, setSelectedNode] = useState<string | null>(null)
  const [selectedEdge, setSelectedEdge] = useState<string | null>(null)
  const [nodePositions, setNodePositions] = useState<Record<string, { x: number; y: number }>>({})
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)

  // Load saved systems
  useEffect(() => {
    const load = async () => {
      const list = await systemsApi.listSystems()
      setSystems(list)
      if (list.length > 0) {
        loadSystem(list[0])
      }
      setLoading(false)
    }
    load()
  }, [])

  const loadSystem = (sys: SystemDefinition) => {
    setActiveSystemId(sys.id)
    setSystemName(sys.name)
    setSystemDesc(sys.description)
    setAgents(sys.agents)
    setEdges(sys.edges)
    setUcCatalog(sys.uc_catalog)
    setUcSchema(sys.uc_schema)
    setSelectedNode(null)
    setSelectedEdge(null)
    // Reset positions for loaded system
    const positions: Record<string, { x: number; y: number }> = {}
    sys.agents.forEach((name, idx) => {
      positions[name] = { x: 100 + (idx % 3) * 280, y: 80 + Math.floor(idx / 3) * 140 }
    })
    setNodePositions(positions)
  }

  const handleNewSystem = () => {
    setActiveSystemId(null)
    setSystemName('New System')
    setSystemDesc('')
    setAgents([])
    setEdges([])
    setUcCatalog('')
    setUcSchema('')
    setSelectedNode(null)
    setSelectedEdge(null)
    setNodePositions({})
  }

  // Build a SystemDefinition from current state (for prop passing)
  const currentSystem: SystemDefinition | null = {
    id: activeSystemId || '',
    name: systemName,
    description: systemDesc,
    agents,
    edges,
    uc_catalog: ucCatalog,
    uc_schema: ucSchema,
    created_at: '',
    updated_at: '',
  }

  const handleAddAgent = useCallback((agentName: string) => {
    if (!agents.includes(agentName)) {
      setAgents(prev => [...prev, agentName])
    }
  }, [agents])

  const handleRemoveAgent = useCallback((agentName: string) => {
    setAgents(prev => prev.filter(a => a !== agentName))
    setEdges(prev => prev.filter(e => e.source_agent !== agentName && e.target_agent !== agentName))
    setSelectedNode(null)
    setNodePositions(prev => {
      const next = { ...prev }
      delete next[agentName]
      return next
    })
  }, [])

  const handleEdgeUpdate = useCallback((edgeId: string, envVar: string) => {
    setEdges(prev => prev.map(e => {
      if (`${e.source_agent}->${e.target_agent}` === edgeId) {
        return { ...e, env_var: envVar }
      }
      return e
    }))
  }, [])

  const handleSystemMetaChange = useCallback((field: string, value: string) => {
    switch (field) {
      case 'name': setSystemName(value); break
      case 'description': setSystemDesc(value); break
      case 'uc_catalog': setUcCatalog(value); break
      case 'uc_schema': setUcSchema(value); break
    }
  }, [])

  const handleSave = async () => {
    setSaving(true)
    try {
      const payload = {
        name: systemName,
        description: systemDesc,
        agents,
        edges,
        uc_catalog: ucCatalog,
        uc_schema: ucSchema,
      }

      if (activeSystemId) {
        const updated = await systemsApi.updateSystem(activeSystemId, payload)
        setSystems(prev => prev.map(s => s.id === updated.id ? updated : s))
      } else {
        const created = await systemsApi.createSystem(payload)
        setActiveSystemId(created.id)
        setSystems(prev => [...prev, created])
      }
    } finally {
      setSaving(false)
    }
  }

  const handleDeploy = async (): Promise<DeployResult | null> => {
    // Save first if needed
    if (!activeSystemId) {
      await handleSave()
    }
    if (!activeSystemId && systems.length === 0) return null

    const idToDeploy = activeSystemId || systems[systems.length - 1]?.id
    if (!idToDeploy) return null

    return systemsApi.deploySystem(idToDeploy)
  }

  const handleDeleteSystem = async (id: string) => {
    await systemsApi.deleteSystem(id)
    setSystems(prev => prev.filter(s => s.id !== id))
    if (activeSystemId === id) {
      handleNewSystem()
    }
  }

  if (loading) {
    return <div className="system-builder-loading">Loading systems...</div>
  }

  return (
    <div className="system-builder-page">
      {/* System selector bar */}
      <div className="system-selector-bar">
        <div className="system-tabs">
          {systems.map(sys => (
            <button
              key={sys.id}
              className={`system-tab ${activeSystemId === sys.id ? 'system-tab-active' : ''}`}
              onClick={() => loadSystem(sys)}
            >
              {sys.name}
              <span
                className="system-tab-delete"
                onClick={e => { e.stopPropagation(); handleDeleteSystem(sys.id) }}
              >
                x
              </span>
            </button>
          ))}
          <button className="system-tab system-tab-new" onClick={handleNewSystem}>
            + New System
          </button>
        </div>
      </div>

      {/* Three-panel layout */}
      <ThreePanel
        left={
          <AgentPalette
            onAddAgent={handleAddAgent}
            addedAgents={new Set(agents)}
          />
        }
        center={
          <WiringCanvas
            agents={agents}
            edges={edges}
            onAgentsChange={setAgents}
            onEdgesChange={setEdges}
            selectedNodeId={selectedNode}
            selectedEdgeId={selectedEdge}
            onSelectNode={setSelectedNode}
            onSelectEdge={setSelectedEdge}
            nodePositions={nodePositions}
            onNodePositionsChange={setNodePositions}
          />
        }
        right={
          <PropertiesPanel
            system={currentSystem}
            selectedNode={selectedNode}
            selectedEdge={selectedEdge}
            edges={edges}
            onEdgeUpdate={handleEdgeUpdate}
            onRemoveAgent={handleRemoveAgent}
            onSystemMetaChange={handleSystemMetaChange}
            onSave={handleSave}
            onDeploy={handleDeploy}
            saving={saving}
          />
        }
      />
    </div>
  )
}
