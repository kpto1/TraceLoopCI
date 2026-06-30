import Link from "next/link";

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <div className="max-w-lg text-center">
        <h1 style={{ fontSize: 36, fontWeight: 700, marginBottom: 12 }}>
          TraceLoop CI
        </h1>
        <p className="muted mb-4" style={{ fontSize: 18 }}>
          LLM behavioral regression testing platform.
          Catch prompt regressions before production.
        </p>
        <Link href="/traces" className="btn">
          View Traces →
        </Link>
      </div>
    </div>
  );
}
