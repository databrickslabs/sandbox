/* System Builder types — mirrors backend SystemDefinition / WiringEdge */

export interface WiringEdge {
  source_agent: string;
  target_agent: string;
  env_var: string;
}

export interface SystemDefinition {
  id: string;
  name: string;
  description: string;
  agents: string[];
  edges: WiringEdge[];
  uc_catalog: string;
  uc_schema: string;
  created_at: string;
  updated_at: string;
}

export interface SystemCreate {
  name: string;
  description?: string;
  agents: string[];
  edges: WiringEdge[];
  uc_catalog?: string;
  uc_schema?: string;
}

export interface DeployStepResult {
  agent: string;
  action: string;
  status: "success" | "failed" | "skipped";
  detail: string;
}

export interface DeployResult {
  system_id: string;
  steps: DeployStepResult[];
  status: "success" | "partial" | "failed";
}

/** Async deploy progress — returned by GET /api/systems/{id}/deploy/status */
export interface DeployProgress {
  deploy_id: string;
  system_id: string;
  status: "pending" | "deploying" | "success" | "partial" | "failed";
  current_step: number;
  total_steps: number;
  steps: DeployStepResult[];
}
