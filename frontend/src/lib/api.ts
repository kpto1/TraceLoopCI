const BASE = "http://localhost:8000";

export interface Trace {
  trace_id: string;
  user_input: string;
  model_output: string;
  model: string;
  tokens_total: number;
  cost: number;
  latency_ms: number;
  status: string;
  created_at: string;
}

export interface TraceListResponse {
  total: number;
  limit: number;
  offset: number;
  items: Trace[];
}

export async function listTraces(): Promise<TraceListResponse> {
  const res = await fetch(`${BASE}/v1/traces`);
  if (!res.ok) throw new Error(`Failed to fetch traces: ${res.status}`);
  return res.json();
}

export async function getTrace(id: string): Promise<Trace> {
  const res = await fetch(`${BASE}/v1/traces/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch trace ${id}: ${res.status}`);
  return res.json();
}
