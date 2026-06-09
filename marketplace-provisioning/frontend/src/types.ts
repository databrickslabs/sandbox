export interface Account {
  id: string;
  nickname: string;
  mystery: string;
  genie_url: string;
  created_at: string;
}

export interface EvidenceItem {
  field_order: number;
  type: "text" | "image" | "csv";
  content: string;
  filename?: string;
}

export interface Submission {
  id: string;
  solution: string;
  recommendation: string;
  submitted_at: string;
  score: number;
  evidence: EvidenceItem[];
}

export interface ProvisioningEvent {
  step: string;
  message: string;
  progress: number;
  total: number;
  genie_url?: string;
  error?: boolean;
}
