const BASE = "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  createAccount: (nickname: string, mystery: string) =>
    request<{
      id: string;
      nickname: string;
      mystery: string;
      provisioning_status: string;
      genie_url: string | null;
    }>("/accounts", {
      method: "POST",
      body: JSON.stringify({ nickname, mystery }),
    }),

  getAccount: (accountId: string) =>
    request<{ id: string; nickname: string; mystery: string; genie_url: string }>(
      `/accounts/${accountId}`
    ),

  submitAnswer: (data: {
    account_id: string;
    solution: string;
    recommendation: string;
    evidence: { field_order: number; type: string; content: string }[];
  }) =>
    request<{ id: string; score: number; root_cause_score: number; evidence_score: number; recommendation_score: number }>("/submissions", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getLatestSubmission: (accountId: string) =>
    request<any>(`/submissions/${accountId}`),

  scoreMySubmission: (accountId: string) =>
    request<{
      score: number;
      root_cause_score: number;
      evidence_score: number;
      recommendation_score: number;
    }>(`/score/${accountId}`, { method: "POST" }),

  getAnswer: (mystery: string) =>
    request<{
      mystery: string;
      root_cause: string;
      sample_recommendation: string;
      query_path: string[];
    }>(`/answer/${encodeURIComponent(mystery)}`),

  getConfig: () =>
    request<{ workspace_host: string }>("/config"),
};
