export interface TraceRecord {
  user_input: string;
  model_output: string;
  model: string;
  project_id?: string;
  provider?: string;
  tokens_total?: number;
  cost?: number;
  latency_ms?: number;
  status?: string;
  tags?: string[];
}

export interface TraceLoopConfig {
  apiUrl: string;
  apiKey?: string;
  projectId?: string;
}

let _config: TraceLoopConfig | null = null;

export function configure(config: TraceLoopConfig): void {
  _config = config;
}

export async function recordTrace(
  input: string,
  output: string,
  model: string,
  extra?: Partial<TraceRecord>
): Promise<void> {
  if (!_config) {
    console.warn("[traceloop] Not configured. Call configure() first.");
    return;
  }

  const payload: TraceRecord = {
    user_input: input,
    model_output: output,
    model,
    project_id: _config.projectId || "default",
    ...extra,
  };

  try {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (_config.apiKey) {
      headers["X-API-Key"] = _config.apiKey;
    }

    const resp = await fetch(`${_config.apiUrl}/v1/traces`, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });

    if (!resp.ok) {
      console.warn(`[traceloop] Record failed: ${resp.status}`);
    }
  } catch (e) {
    console.warn(`[traceloop] Record error: ${e}`);
  }
}

export function traceLoop(model: string) {
  return function (target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    const original = descriptor.value;
    descriptor.value = async function (...args: any[]) {
      const input = JSON.stringify(args);
      const t0 = Date.now();
      const result = await original.apply(this, args);
      const output = typeof result === "string" ? result : JSON.stringify(result);
      const latency = Date.now() - t0;

      await recordTrace(input, output, model, { latency_ms: latency });
      return result;
    };
    return descriptor;
  };
}
