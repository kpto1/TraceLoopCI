"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listTraces, type Trace } from "@/lib/api";

export default function TracesPage() {
  const [traces, setTraces] = useState<Trace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listTraces()
      .then((res) => setTraces(res.items))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="muted mono text-sm" style={{ padding: 32 }}>loading traces...</div>;
  if (error) return <div className="text-sm" style={{ padding: 32, color: "#fca5a5" }}>error: {error}</div>;

  return (
    <div style={{ maxWidth: 1152, margin: "0 auto", padding: 24 }}>
      <div className="flex items-center mb-4" style={{ justifyContent: "space-between" }}>
        <h1 style={{ fontSize: 20, fontWeight: 600 }}>Traces</h1>
        <span className="muted mono text-sm">{traces.length} traces</span>
      </div>
      <div style={{ overflowX: "auto", border: "1px solid var(--border)", borderRadius: 8 }}>
        <table className="mono text-sm">
          <thead>
            <tr style={{ background: "#18181b", color: "var(--muted)", textTransform: "uppercase", fontSize: 11 }}>
              <th style={{ textAlign: "left", padding: "12px 16px", fontWeight: 500 }}>ID</th>
              <th style={{ textAlign: "left", padding: "12px 16px", fontWeight: 500 }}>Model</th>
              <th style={{ textAlign: "left", padding: "12px 16px", fontWeight: 500 }}>Input</th>
              <th style={{ textAlign: "right", padding: "12px 16px", fontWeight: 500 }}>Tokens</th>
              <th style={{ textAlign: "right", padding: "12px 16px", fontWeight: 500 }}>Latency</th>
              <th style={{ textAlign: "right", padding: "12px 16px", fontWeight: 500 }}>Cost</th>
              <th style={{ textAlign: "left", padding: "12px 16px", fontWeight: 500 }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {traces.map((t) => (
              <tr key={t.trace_id}>
                <td style={{ padding: "12px 16px" }}>
                  <Link href={`/traces/${t.trace_id}`} style={{ color: "var(--accent)" }}>
                    {t.trace_id.slice(0, 12)}...
                  </Link>
                </td>
                <td style={{ padding: "12px 16px" }}>{t.model}</td>
                <td className="muted" style={{ padding: "12px 16px", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {t.user_input}
                </td>
                <td style={{ padding: "12px 16px", textAlign: "right" }}>{t.tokens_total.toLocaleString()}</td>
                <td style={{ padding: "12px 16px", textAlign: "right" }}>{t.latency_ms}ms</td>
                <td style={{ padding: "12px 16px", textAlign: "right" }}>${t.cost.toFixed(4)}</td>
                <td style={{ padding: "12px 16px" }}>
                  <span className={`badge ${t.status === "success" ? "badge-success" : t.status === "error" ? "badge-error" : ""}`}>
                    {t.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
