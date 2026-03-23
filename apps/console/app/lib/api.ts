export type RunResponse = {
  run_id: string;
  status: string;
  workflow_key: string;
  user_input: string | null;
  response_text: string | null;
  last_error: string | null;
  approval_request_id: string | null;
};

export type ApprovalResponse = {
  id: string;
  run_id: string;
  tool_invocation_id: string | null;
  status: string;
  reason: string;
  action_preview: Record<string, unknown> | null;
  requested_at: string;
  resolved_at: string | null;
  decision_comment: string | null;
  resume_result?: {
    run_state: string | null;
    response_text: string | null;
    failure_reason: string | null;
  } | null;
};

export type TimelineEvent = {
  sequence: number;
  event_type: string;
  title: string;
  timestamp: string;
  payload?: Record<string, unknown> | null;
};

export type RunTimeline = {
  run_id: string;
  event_count: number;
  events: TimelineEvent[];
};

export type EvalScoreCard = {
  groundedness: number;
  tool_choice: number;
  approval_trigger: number;
  response_usefulness: number;
  format_correctness: number;
  citation_presence: number;
  latency_signal: number;
  cost_signal: number;
  total_score: number;
};

export type EvalResult = {
  case_key: string;
  passed: boolean;
  summary: string;
  scorecard: EvalScoreCard;
  response_text: string;
  tool_name: string | null;
  requires_approval: boolean;
  citation_count: number;
  latency_ms: number;
  estimated_cost_usd: number | null;
};

export type EvalRun = {
  eval_run_id: string | null;
  run_name: string;
  model_name: string | null;
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  average_score: number;
  dimension_averages: Record<string, number>;
  results: EvalResult[];
  regression: Record<string, unknown> | null;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? `Request failed with status ${response.status}`);
  }

  return (await response.json()) as T;
}

export function createRun(payload: {
  workflow_key: string;
  user_input: string;
  tenant_id: string;
  requested_by?: string;
}): Promise<RunResponse> {
  return apiFetch<RunResponse>("/runs", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getRun(runId: string): Promise<RunResponse> {
  return apiFetch<RunResponse>(`/runs/${runId}`);
}

export function getRunTrace(runId: string): Promise<RunTimeline> {
  return apiFetch<RunTimeline>(`/runs/${runId}/trace`);
}

export function getApproval(approvalId: string): Promise<ApprovalResponse> {
  return apiFetch<ApprovalResponse>(`/approvals/${approvalId}`);
}

export function resolveApproval(
  approvalId: string,
  decision: "approve" | "reject",
): Promise<ApprovalResponse> {
  return apiFetch<ApprovalResponse>(`/approvals/${approvalId}/${decision}`, {
    method: "POST",
  });
}

export function runEvals(payload: {
  name: string;
  compare_to_latest: boolean;
}): Promise<EvalRun> {
  return apiFetch<EvalRun>("/evals/run", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getEvalRun(evalRunId: string): Promise<EvalRun> {
  return apiFetch<EvalRun>(`/evals/${evalRunId}`);
}
