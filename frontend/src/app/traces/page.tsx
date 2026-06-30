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

  if (loading) return <div className="p-8 text-zinc-400 font-mono text-sm">loading traces...</div>;
  if (error) return <div className="p-8 text-red-400 font-mono text-sm">error: {error}</div>;

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold">Traces</h1>
        <span className="text-zinc-500 font-mono text-sm">{traces.length} traces</span>
      </div>
      <div className="overflow-x-auto border border-zinc-800 rounded-md">
        <table className="w-full text-sm font-mono">
          <thead>
            <tr className="bg-zinc-900 text-zinc-400 uppercase tracking-wider text-xs">
              <th className="text-left px-4 py-3 font-medium">ID</th>
              <th className="text-left px-4 py-3 font-medium">Model</th>
              <th className="text-left px-4 py-3 font-medium">Input</th>
              <th className="text-right px-4 py-3 font-medium">Tokens</th>
              <th className="text-right px-4 py-3 font-medium">Latency</th>
              <th className="text-right px-4 py-3 font-medium">Cost</th>
              <th className="text-left px-4 py-3 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {traces.map((t) => (
              <tr
                key={t.trace_id}
                className="border-t border-zinc-800 hover:bg-zinc-900/50 transition-colors"
              >
                <td className="px-4 py-3">
                  <Link
                    href={`/traces/${t.trace_id}`}
                    className="text-blue-400 hover:text-blue-300"
                  >
                    {t.trace_id.slice(0, 12)}...
                  </Link>
                </td>
                <td className="px-4 py-3 text-zinc-300">{t.model}</td>
                <td className="px-4 py-3 text-zinc-400 max-w-[200px] truncate">
                  {t.user_input}
                </td>
                <td className="px-4 py-3 text-right text-zinc-300">
                  {t.tokens_total.toLocaleString()}
                </td>
                <td className="px-4 py-3 text-right text-zinc-300">
                  {t.latency_ms}ms
                </td>
                <td className="px-4 py-3 text-right text-zinc-300">
                  ${t.cost.toFixed(4)}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                      t.status === "completed"
                        ? "bg-emerald-900/50 text-emerald-300"
                        : t.status === "failed"
                          ? "bg-red-900/50 text-red-300"
                          : "bg-zinc-800 text-zinc-400"
                    }`}
                  >
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
