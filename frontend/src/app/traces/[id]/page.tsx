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

  if (loading) return <div className="p-8 text-zinc-400 font-mono text-sm">loading trace...</div>;
  if (error) return <div className="p-8 text-red-400 font-mono text-sm">error: {error}</div>;
  if (!trace) return null;

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-6">
        <Link href="/traces" className="text-zinc-500 hover:text-zinc-300 font-mono text-sm">
          &larr; back to traces
        </Link>
      </div>

      <div className="border border-zinc-800 rounded-md p-6 mb-6">
        <h1 className="text-lg font-semibold mb-4 font-mono">Trace {trace.trace_id}</h1>
        <dl className="grid grid-cols-2 gap-4 text-sm font-mono">
          <div>
            <dt className="text-zinc-500 text-xs uppercase tracking-wider mb-1">Model</dt>
            <dd className="text-zinc-200">{trace.model}</dd>
          </div>
          <div>
            <dt className="text-zinc-500 text-xs uppercase tracking-wider mb-1">Status</dt>
            <dd>
              <span
                className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                  trace.status === "completed"
                    ? "bg-emerald-900/50 text-emerald-300"
                    : trace.status === "failed"
                      ? "bg-red-900/50 text-red-300"
                      : "bg-zinc-800 text-zinc-400"
                }`}
              >
                {trace.status}
              </span>
            </dd>
          </div>
          <div>
            <dt className="text-zinc-500 text-xs uppercase tracking-wider mb-1">Total Tokens</dt>
            <dd className="text-zinc-200">{trace.tokens_total.toLocaleString()}</dd>
          </div>
          <div>
            <dt className="text-zinc-500 text-xs uppercase tracking-wider mb-1">Cost</dt>
            <dd className="text-zinc-200">${trace.cost.toFixed(6)}</dd>
          </div>
          <div>
            <dt className="text-zinc-500 text-xs uppercase tracking-wider mb-1">Latency</dt>
            <dd className="text-zinc-200">{trace.latency_ms}ms</dd>
          </div>
          <div>
            <dt className="text-zinc-500 text-xs uppercase tracking-wider mb-1">Created</dt>
            <dd className="text-zinc-200">{new Date(trace.created_at).toLocaleString()}</dd>
          </div>
        </dl>
      </div>

      <div className="border border-zinc-800 rounded-md p-6 mb-6">
        <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3">Input</h2>
        <pre className="bg-zinc-950 border border-zinc-800 rounded p-4 text-sm text-zinc-300 overflow-x-auto whitespace-pre-wrap font-mono">
          {trace.user_input}
        </pre>
      </div>

      <div className="border border-zinc-800 rounded-md p-6">
        <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3">Output</h2>
        <pre className="bg-zinc-950 border border-zinc-800 rounded p-4 text-sm text-zinc-300 overflow-x-auto whitespace-pre-wrap font-mono">
          {trace.model_output}
        </pre>
      </div>
    </div>
  );
}
