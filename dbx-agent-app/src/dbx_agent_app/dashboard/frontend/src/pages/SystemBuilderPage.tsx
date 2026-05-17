/**
 * SystemBuilderPage — wizard container with step-gated sidebar.
 * Replaces the flat 3-panel layout with a guided 4-step flow.
 *
 * Steps: 1.Select → 2.Wire → 3.Configure → 4.Deploy
 * State is persisted in localStorage via workflow-state utilities.
 */
import { useState, useEffect, useCallback, useMemo, lazy, Suspense } from "react";
import { WizardSidebar, type WizardStep } from "../components/systems/WizardSidebar";

const SelectAgentsStep = lazy(() => import("../components/systems/steps/SelectAgentsStep"));
const WireStep = lazy(() => import("../components/systems/steps/WireStep"));
const ConfigureStep = lazy(() => import("../components/systems/steps/ConfigureStep"));
const DeployStep = lazy(() => import("../components/systems/steps/DeployStep"));
import {
  fetchSystems,
  createSystem,
  updateSystem,
} from "../api/systems";
import { apiFetch } from "../api/client";
import {
  saveState,
  loadState,
  clearAllWorkflowState,
} from "../lib/workflow-state";
import type { Agent } from "../types";
import type { SystemDefinition, WiringEdge } from "../types/systems";

export function SystemBuilderPage() {
  const [systems, setSystems] = useState<SystemDefinition[]>([]);
  const [activeSystemId, setActiveSystemId] = useState<string | null>(null);

  // Current system editing state
  const [systemName, setSystemName] = useState("New System");
  const [systemDesc, setSystemDesc] = useState("");
  const [agents, setAgents] = useState<string[]>([]);
  const [edges, setEdges] = useState<WiringEdge[]>([]);
  const [ucCatalog, setUcCatalog] = useState("");
  const [ucSchema, setUcSchema] = useState("");

  // UI state
  const [step, setStep] = useState<number>(
    () => loadState<number>("active-step") ?? 1,
  );
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  // Agent metadata for richer node display
  const [agentMetaMap, setAgentMetaMap] = useState<
    Record<string, { description?: string; capabilities?: string }>
  >({});

  // Persist step changes
  useEffect(() => {
    saveState("active-step", step);
  }, [step]);

  // Persist agent selection
  useEffect(() => {
    saveState("selected-agents", agents);
  }, [agents]);

  // Persist edges
  useEffect(() => {
    saveState("wiring-edges", edges);
  }, [edges]);

  // Load systems on mount
  useEffect(() => {
    fetchSystems()
      .then((list) => {
        setSystems(list);
        // Restore from localStorage or load first system
        const savedSystemId = loadState<string>("active-system-id");
        const savedSystem = savedSystemId
          ? list.find((s) => s.id === savedSystemId)
          : null;
        if (savedSystem) {
          loadSystem(savedSystem);
        } else if (list.length > 0 && list[0]) {
          loadSystem(list[0]);
        } else {
          // Restore unsaved state from localStorage
          const savedAgents = loadState<string[]>("selected-agents");
          const savedEdges = loadState<WiringEdge[]>("wiring-edges");
          if (savedAgents) setAgents(savedAgents);
          if (savedEdges) setEdges(savedEdges);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  // Fetch agent metadata for richer display
  useEffect(() => {
    apiFetch<Agent[]>("/api/agents")
      .then((agentList) => {
        const meta: Record<string, { description?: string; capabilities?: string }> = {};
        for (const a of agentList) {
          meta[a.name] = {
            description: a.description ?? undefined,
            capabilities: a.capabilities ?? undefined,
          };
        }
        setAgentMetaMap(meta);
      })
      .catch(() => {});
  }, []);

  const loadSystem = (sys: SystemDefinition) => {
    setActiveSystemId(sys.id);
    setSystemName(sys.name);
    setSystemDesc(sys.description);
    setAgents(sys.agents);
    setEdges(sys.edges);
    setUcCatalog(sys.uc_catalog);
    setUcSchema(sys.uc_schema);
    saveState("active-system-id", sys.id);
  };

  const handleNewSystem = () => {
    setActiveSystemId(null);
    setSystemName("New System");
    setSystemDesc("");
    setAgents([]);
    setEdges([]);
    setUcCatalog("");
    setUcSchema("");
    setStep(1);
    saveState("active-system-id", null);
  };

  const handleReset = () => {
    clearAllWorkflowState();
    handleNewSystem();
  };

  const currentSystem: SystemDefinition = {
    id: activeSystemId ?? "",
    name: systemName,
    description: systemDesc,
    agents,
    edges,
    uc_catalog: ucCatalog,
    uc_schema: ucSchema,
    created_at: "",
    updated_at: "",
  };

  const handleAddAgent = useCallback(
    (name: string) => {
      if (!agents.includes(name)) {
        setAgents((prev) => [...prev, name]);
      }
    },
    [agents],
  );

  const handleRemoveAgent = useCallback((name: string) => {
    setAgents((prev) => prev.filter((a) => a !== name));
    setEdges((prev) =>
      prev.filter((e) => e.source_agent !== name && e.target_agent !== name),
    );
  }, []);

  const handleEdgeUpdate = useCallback((edgeId: string, envVar: string) => {
    setEdges((prev) =>
      prev.map((e) =>
        `${e.source_agent}->${e.target_agent}` === edgeId
          ? { ...e, env_var: envVar }
          : e,
      ),
    );
  }, []);

  const handleSystemMetaChange = useCallback(
    (field: string, value: string) => {
      switch (field) {
        case "name":
          setSystemName(value);
          break;
        case "description":
          setSystemDesc(value);
          break;
        case "uc_catalog":
          setUcCatalog(value);
          break;
        case "uc_schema":
          setUcSchema(value);
          break;
      }
    },
    [],
  );

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = {
        name: systemName,
        description: systemDesc,
        agents,
        edges,
        uc_catalog: ucCatalog,
        uc_schema: ucSchema,
      };

      if (activeSystemId) {
        const updated = await updateSystem(activeSystemId, payload);
        setSystems((prev) =>
          prev.map((s) => (s.id === updated.id ? updated : s)),
        );
      } else {
        const created = await createSystem(payload);
        setActiveSystemId(created.id);
        setSystems((prev) => [...prev, created]);
        saveState("active-system-id", created.id);
      }
    } finally {
      setSaving(false);
    }
  };

  const refreshSystems = useCallback(() => {
    fetchSystems()
      .then((list) => setSystems(list))
      .catch(() => {});
  }, []);


  // Step gating logic
  const wizardSteps: WizardStep[] = useMemo(() => {
    return [
      { id: 1, label: "Select Agents", icon: "\u25A6", completed: agents.length >= 2 },
      { id: 2, label: "Wire Connections", icon: "\u2194", completed: edges.length >= 1 },
      {
        id: 3,
        label: "Configure",
        icon: "\u2699",
        completed:
          systemName.trim() !== "" &&
          edges.every((e) => e.env_var.trim() !== ""),
      },
      { id: 4, label: "Deploy", icon: "\u26A1", completed: false },
    ];
  }, [agents, edges, systemName]);

  if (loading) {
    return (
      <div className="sb-muted-center" style={{ padding: "3rem" }}>
        Loading systems...
      </div>
    );
  }

  return (
    <div className="sb-wizard">
      <WizardSidebar
        step={step}
        onStepChange={setStep}
        steps={wizardSteps}
        systems={systems}
        activeSystemId={activeSystemId}
        onSelectSystem={(id) => {
          const sys = systems.find((s) => s.id === id);
          if (sys) loadSystem(sys);
        }}
        onNewSystem={handleNewSystem}
        onReset={handleReset}
      />

      <main className="sb-wizard-content">
        <div className="sb-wizard-header">
          <h2>System Builder</h2>
          <p style={{ color: "var(--muted)" }}>
            Wire agents together and deploy multi-agent systems
          </p>
        </div>

        <Suspense fallback={<div className="sb-muted-center" style={{ padding: "2rem" }}>Loading step...</div>}>
          {step === 1 && (
            <SelectAgentsStep
              agents={agents}
              edges={edges}
              onAddAgent={handleAddAgent}
              onRemoveAgent={handleRemoveAgent}
            />
          )}

          {step === 2 && (
            <WireStep
              agents={agents}
              edges={edges}
              onEdgesChange={setEdges}
              onEdgeUpdate={handleEdgeUpdate}
              agentMeta={agentMetaMap}
            />
          )}

          {step === 3 && (
            <ConfigureStep
              system={currentSystem}
              agents={agents}
              edges={edges}
              onEdgeUpdate={handleEdgeUpdate}
              onSystemMetaChange={handleSystemMetaChange}
              onSave={handleSave}
              saving={saving}
            />
          )}

          {step === 4 && (
            <DeployStep
              systemId={activeSystemId}
              agents={agents}
              edges={edges}
              onSave={handleSave}
              onDeployComplete={refreshSystems}
            />
          )}
        </Suspense>
      </main>
    </div>
  );
}
