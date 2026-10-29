"use client";
import { useEffect, useState } from "react";

type Dataset = { id: number; name: string };
type Case = { id: number; input_text: string; expected_keywords: string[]; must_cite_docs: string[] };
type Run = { id: number; is_baseline: boolean; overall_score: number; status: string };

async function api(path: string, body?: unknown) {
  const response = await fetch(`/api/backend/v1/${path}`, body === undefined ? { cache: "no-store" } : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail));
  return data;
}

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selected, setSelected] = useState(0);
  const [cases, setCases] = useState<Case[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [name, setName] = useState("");
  const [draft, setDraft] = useState('{"input_text":"退款政策是什么？","expected_keywords":["退款","7天"],"forbidden_keywords":[],"must_cite_docs":[]}');
  const [traceId, setTraceId] = useState("");
  const [model, setModel] = useState("mock");
  const [revision, setRevision] = useState("");
  const [baseline, setBaseline] = useState(0);
  const [isBaseline, setIsBaseline] = useState(false);
  const [realJudge, setRealJudge] = useState(true);
  const [report, setReport] = useState<unknown>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function refresh(id: number) {
    setDatasets((await api("datasets")).items);
    if (id) {
      setCases((await api(`datasets/${id}`)).cases);
      setRuns((await api(`eval/runs?dataset_id=${id}`)).items);
    }
  }
  useEffect(() => { refresh(0).catch(e => setError(String(e))); }, []);
  async function action(fn: () => Promise<void>) {
    setBusy(true); setError("");
    try { await fn(); } catch (e) { setError(String(e)); } finally { setBusy(false); }
  }
  return <div style={{ maxWidth: 1000, margin: "auto", padding: 24 }}>
    <h1>数据集与评测</h1>
    <p>从 Trace 建立用例，保存基线，再比较候选版本。PR 应用代码评测使用仓库 CLI；这里调用服务配置的模型端点。</p>
    {error && <p role="alert" style={{ color: "#fca5a5" }}>{error}</p>}
    <fieldset disabled={busy} className="card">
      <legend>数据集</legend>
      <label>名称 <input value={name} onChange={e => setName(e.target.value)} /></label>
      <button onClick={() => action(async () => { const ds = await api("datasets", { name }); setSelected(ds.id); await refresh(ds.id); })}>创建数据集</button>
      <label>选择数据集 <select value={selected} onChange={e => action(async () => { const id = Number(e.target.value); setSelected(id); setBaseline(0); setReport(null); await refresh(id); })}>
        <option value={0}>请选择</option>{datasets.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
      </select></label>
    </fieldset>
    {selected > 0 && <>
      <fieldset disabled={busy} className="card"><legend>添加用例</legend>
        <label>用例 JSON<textarea rows={7} style={{ width: "100%" }} value={draft} onChange={e => setDraft(e.target.value)} /></label>
        <label>来源 Trace ID（可选）<input value={traceId} onChange={e => setTraceId(e.target.value)} /></label>
        <button onClick={() => action(async () => { const data = JSON.parse(draft); if (traceId) delete data.input_text; await api(`datasets/${selected}/cases${traceId ? `/from-trace/${encodeURIComponent(traceId)}` : ""}`, data); await refresh(selected); })}>保存用例</button>
        <ul>{cases.map(c => <li key={c.id}>#{c.id} {c.input_text} · 必须包含：{c.expected_keywords.join("、")}</li>)}</ul>
      </fieldset>
      <fieldset disabled={busy} className="card"><legend>运行评测</legend>
        <label>模型 <input value={model} onChange={e => setModel(e.target.value)} /></label>
        <label>版本标识 <input value={revision} onChange={e => setRevision(e.target.value)} placeholder="commit / prompt version" /></label>
        <label><input type="checkbox" checked={realJudge} onChange={e => setRealJudge(e.target.checked)} />要求真实裁判（关闭仅用于演示）</label>
        <label><input type="checkbox" checked={isBaseline} onChange={e => setIsBaseline(e.target.checked)} />保存为基线</label>
        <label>比较基线 <select value={baseline} onChange={e => setBaseline(Number(e.target.value))}><option value={0}>不比较</option>{runs.filter(r => r.is_baseline).map(r => <option key={r.id} value={r.id}>#{r.id} · {r.overall_score}%</option>)}</select></label>
        <button onClick={() => action(async () => { setReport(await api("eval/run", { dataset_id: selected, model, revision, is_baseline: isBaseline, baseline_run_id: baseline || null, require_real_judge: realJudge })); await refresh(selected); })}>{busy ? "评测中…" : "开始评测"}</button>
      </fieldset>
      <section className="card"><h2>历史报告</h2>{runs.map(r => <button key={r.id} onClick={() => action(async () => { const data = await api(`eval/runs/${r.id}`); setReport(data.summary?.report || data); })}>#{r.id} · {r.status} · {r.overall_score}%</button>)}</section>
    </>}
    {report !== null && <section className="card"><h2>评测报告与基线差异</h2><pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{JSON.stringify(report, null, 2)}</pre></section>}
  </div>;
}
