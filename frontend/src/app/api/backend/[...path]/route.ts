import { NextRequest } from "next/server";

// Server-side credential only. Deploy this single-workspace UI behind access control.
async function forward(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const suffix = path.join("/");
  if (!/^v1\/(traces|datasets|eval)(\/|$)/.test(suffix) || path.some(p => p === "." || p === ".." || p.includes("/"))) {
    return Response.json({ detail: "Not found" }, { status: 404 });
  }
  const origin = request.headers.get("origin");
  if (request.method !== "GET" && origin && origin !== request.nextUrl.origin) {
    return Response.json({ detail: "Invalid origin" }, { status: 403 });
  }
  const base = process.env.TRACELOOP_API_URL || "http://127.0.0.1:8000";
  const body = request.method === "GET" ? undefined : await request.text();
  if (body && Buffer.byteLength(body) > 1048576) {
    return Response.json({ detail: "Request too large" }, { status: 413 });
  }
  try {
    const upstream = await fetch(`${base}/${suffix}${request.nextUrl.search}`, {
      method: request.method, body,
      headers: { "Content-Type": "application/json", "X-API-Key": process.env.TRACELOOP_API_KEY || "dev-api-key-change-in-production" },
      cache: "no-store", signal: AbortSignal.timeout(600000),
    });
    return new Response(upstream.body, { status: upstream.status, headers: { "Content-Type": "application/json", "Cache-Control": "no-store" } });
  } catch {
    return Response.json({ detail: "Backend unavailable or timed out" }, { status: 502 });
  }
}
export const GET = forward;
export const POST = forward;
export const DELETE = forward;
