/**
 * Wizard sidebar — 4-step gated navigation for the system builder.
 * Adapted from Tables-to-Genies _sidebar/route.tsx pattern.
 */
import { useState, useEffect } from "react";
import { loadState, saveState } from "../../lib/workflow-state";
import type { SystemDefinition } from "../../types/systems";

export interface WizardStep {
  id: number;
  label: string;
  icon: string;
  completed: boolean;
}

interface Props {
  step: number;
  onStepChange: (step: number) => void;
  steps: WizardStep[];
  systems: SystemDefinition[];
  activeSystemId: string | null;
  onSelectSystem: (id: string) => void;
  onNewSystem: () => void;
  onReset: () => void;
}

export function WizardSidebar({
  step,
  onStepChange,
  steps,
  systems,
  activeSystemId,
  onSelectSystem,
  onNewSystem,
  onReset,
}: Props) {
  const [collapsed, setCollapsed] = useState<boolean>(
    () => loadState<boolean>("sidebar-collapsed") ?? false,
  );

  useEffect(() => {
    saveState("sidebar-collapsed", collapsed);
  }, [collapsed]);

  return (
    <aside className={`sb-wizard-sidebar${collapsed ? " collapsed" : ""}`}>
      {/* Collapse toggle */}
      <button
        className="sb-sidebar-toggle"
        onClick={() => setCollapsed(!collapsed)}
        title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {collapsed ? "\u276F" : "\u276E"}
      </button>

      {!collapsed && (
        <>
          {/* System selector */}
          <div className="sb-sidebar-section">
            <select
              className="sb-input sb-sidebar-select"
              value={activeSystemId ?? ""}
              onChange={(e) => {
                if (e.target.value) onSelectSystem(e.target.value);
              }}
            >
              <option value="" disabled>
                Select system...
              </option>
              {systems.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>

          {/* Step navigation */}
          <nav className="sb-sidebar-nav">
            {steps.map((s) => {
              const isActive = step === s.id;
              const isDisabled =
                s.id > 1 && !steps[s.id - 2]?.completed;
              return (
                <button
                  key={s.id}
                  className={`sb-step${isActive ? " sb-step--active" : ""}${isDisabled ? " sb-step--disabled" : ""}${s.completed ? " sb-step--completed" : ""}`}
                  onClick={() => !isDisabled && onStepChange(s.id)}
                  disabled={isDisabled}
                >
                  <span className="sb-step-num">
                    {s.completed ? "\u2713" : s.id}
                  </span>
                  <span className="sb-step-icon">{s.icon}</span>
                  <span className="sb-step-label">{s.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Bottom actions */}
          <div className="sb-sidebar-actions">
            <button className="btn btn-outline btn-sm" onClick={onNewSystem}>
              + New System
            </button>
            <button
              className="btn btn-outline btn-sm"
              style={{ color: "var(--muted)", borderColor: "var(--border)" }}
              onClick={onReset}
            >
              Reset
            </button>
          </div>
        </>
      )}
    </aside>
  );
}
