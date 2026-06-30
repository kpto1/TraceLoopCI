import Link from "next/link";

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[80vh] px-4">
      <div className="max-w-lg text-center">
        <h1 className="text-4xl font-bold tracking-tight mb-3">TraceLoop CI</h1>
        <p className="text-zinc-400 text-lg mb-8">
          LLM behavioral regression testing platform.
          Detect regressions in model outputs across deployments.
        </p>
        <Link
          href="/traces"
          className="inline-block px-6 py-3 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 rounded-md text-sm font-mono transition-colors"
        >
          View Traces
        </Link>
      </div>
    </div>
  );
}
