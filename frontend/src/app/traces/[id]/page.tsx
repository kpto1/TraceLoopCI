"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getTrace, type Trace } from "@/lib/api";

export default function TraceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [trace, setTrace] = useState<Trace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getTrace(id)
      .then(setTrace)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="muted mono text-sm">loading trace...</div>;
  if (error) return <div className="mono text-sm" style={{ color: "#fca5a5" }}>error: {error}</div>;
  if (!trace) return null;

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-4">
        <Link href="/traces" className="muted mono text-sm">
          &larr; back to traces
        </Link>
      </div>

      <div className="card">
        <h1 className="mono mb-4" style={{ fontSize: 16, fontWeight: 600 }}>Trace {trace.trace_id}</h1>
        <dl className="grid">
          <div>
            <dt>Model</dt>
            <dd>{trace.model}</dd>
          </div>
          <div>
            <dt>Status</dt>
            <dd>
              <span className={`badge ${
                trace.status === "completed" ? "badge-success" :
                trace.status === "failed" ? "badge-error" :
                "badge-default"
              }`}>
                {trace.status}
              </span>
            </dd>
          </div>
          <div>
            <dt>Total Tokens</dt>
            <dd>{trace.tokens_total.toLocaleString()}</dd>
          </div>
          <div>
            <dt>Cost</dt>
            <dd>${trace.cost.toFixed(6)}</dd>
          </div>
          <div>
            <dt>Latency</dt>
            <dd>{trace.latency_ms}ms</dd>
          </div>
          <div>
            <dt>Created</dt>
            <dd>{new Date(trace.created_at).toLocaleString()}</dd>
          </div>
        </dl>
      </div>

      <div className="card">
        <h2 className="muted text-sm mb-2" style={{ textTransform: "uppercase", letterSpacing: "0.5px" }}>Input</h2>
        <pre>{trace.user_input}</pre>
      </div>

      <div className="card">
        <h2 className="muted text-sm mb-2" style={{ textTransform: "uppercase", letterSpacing: "0.5px" }}>Output</h2>
        <pre>{trace.model_output}</pre>
      </div>
    </div>
  );
}
