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

export interface LeaderboardEntry {
  nickname: string;
  mystery: string;
  score: number;
  root_cause_score: number;
  evidence_score: number;
  recommendation_score: number;
  submitted_at: string;
}

export interface ProvisioningEvent {
  step: string;
  message: string;
  progress: number;
  total: number;
  genie_url?: string;
  error?: boolean;
}
