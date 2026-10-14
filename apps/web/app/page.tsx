"use client";

import { useEffect, useRef, useState } from "react";

type Item = { title: string; description: string };
type Page = { id: string; title: string; message: string; items: Item[] };
type Outline = {
  cover: { id: "cover"; title: string };
  pages: Page[];
  chapters: { id: string; title: string; page_ids: string[] }[];
};
type Run = {
  id: string; text: string; status: string; stage: string; error: string | null;
  outline: Outline | null; confirmed_outline: Outline | null; trace: unknown[];
  slides: { page_id: string; type: string; layout: { id: string }; copy: { title: string } }[];
};
type Summary = Pick<Run, "id" | "text" | "status" | "stage">;
type Ontology = { types: unknown[]; layouts: { id: string; enabled: boolean }[] };

const labels: Record<string, string> = {
  outline_pending: "개요 생성 중", outline_ready: "개요 편집·확정 대기",
  slides_pending: "슬라이드 생성 중", completed: "완료", failed: "실패",
};

async function api<T>(path: string, method = "GET", body?: unknown): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method, headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body), cache: "no-store",
  });
  const result = await response.json();
  if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : JSON.stringify(result.detail));
  return result;
}

function Slide({ runId, index, title }: { runId: string; index: number; title: string }) {
  const root = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  useEffect(() => {
    const observer = new ResizeObserver(([entry]) => setScale(entry.contentRect.width / 1280));
    if (root.current) observer.observe(root.current);
    return () => observer.disconnect();
  }, []);
  return <div className="slide-frame" ref={root} style={{ height: 720 * scale }}>
    <iframe title={`${index + 1}장: ${title}`} src={`/api/runs/${runId}/slides/${index}`}
      width="1280" height="720" style={{ transform: `scale(${scale})` }} />
  </div>;
}

function OutlineEditor({ outline, onChange, editable }: {
  outline: Outline; onChange: (value: Outline) => void; editable: boolean;
}) {
  function update(action: (copy: Outline) => void) {
    const copy = structuredClone(outline);
    action(copy);
    onChange(copy);
  }
  return <div className="outline">
    <label>표지 제목<input disabled={!editable} value={outline.cover.title}
      onChange={e => update(o => { o.cover.title = e.target.value; })} /></label>
    {outline.chapters.map((chapter, chapterIndex) => <section className="chapter" key={chapter.id}>
      <label>챕터 {chapterIndex + 1} 제목<input disabled={!editable} value={chapter.title}
        onChange={e => update(o => { o.chapters[chapterIndex].title = e.target.value; })} /></label>
      {chapter.page_ids.map(id => {
        const pageIndex = outline.pages.findIndex(page => page.id === id);
        const page = outline.pages[pageIndex];
        return <article className="outline-page" key={id}>
          <h3>{pageIndex + 2}장 · {id}</h3>
          <label>페이지 제목<input disabled={!editable} value={page.title}
            onChange={e => update(o => { o.pages[pageIndex].title = e.target.value; })} /></label>
          <label>핵심 메시지<textarea disabled={!editable} rows={2} value={page.message}
            onChange={e => update(o => { o.pages[pageIndex].message = e.target.value; })} /></label>
          {page.items.map((item, itemIndex) => <div className="item-fields" key={itemIndex}>
            <label>소제목<input disabled={!editable} value={item.title}
              onChange={e => update(o => { o.pages[pageIndex].items[itemIndex].title = e.target.value; })} /></label>
            <label>세부내용<textarea disabled={!editable} rows={2} value={item.description}
              onChange={e => update(o => { o.pages[pageIndex].items[itemIndex].description = e.target.value; })} /></label>
          </div>)}
        </article>;
      })}
    </section>)}
  </div>;
}

export default function Home() {
  const [tab, setTab] = useState("presentation");
  const [text, setText] = useState("");
  const [history, setHistory] = useState<Summary[]>([]);
  const [run, setRun] = useState<Run | null>(null);
  const [outline, setOutline] = useState<Outline | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [ontologyText, setOntologyText] = useState("");
  const [checkedText, setCheckedText] = useState("");
  const [notice, setNotice] = useState("");

  async function refreshHistory() { setHistory(await api<Summary[]>("/runs")); }
  useEffect(() => { refreshHistory().catch(e => setError(e.message)); }, []);
  useEffect(() => {
    if (!run || !["outline_pending", "slides_pending"].includes(run.status)) return;
    let active = true;
    const timer = setInterval(() => {
      api<Run>(`/runs/${run.id}`).then(value => {
        if (!active) return;
        setRun(value);
        if (value.status === "outline_ready") setOutline(value.outline);
        if (!["outline_pending", "slides_pending"].includes(value.status)) refreshHistory().catch(e => setError(e.message));
      }).catch(e => { if (active) setError(e.message); });
    }, 1500);
    return () => { active = false; clearInterval(timer); };
  }, [run?.id, run?.status]);

  async function act(action: () => Promise<void>) {
    setBusy(true); setError(""); setNotice("");
    try { await action(); } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }

  async function selectRun(id: string) {
    const value = await api<Run>(`/runs/${id}`);
    setRun(value); setOutline(value.confirmed_outline || value.outline);
  }

  return <main>
    <header><h1>AI 프레젠테이션 PoC</h1><p>Jev 판단 · Workers AI 문구 생성</p></header>
    <nav>
      <button aria-pressed={tab === "presentation"} onClick={() => setTab("presentation")}>프레젠테이션</button>
      <button aria-pressed={tab === "ontology"} onClick={() => {
        setTab("ontology");
        if (!ontologyText) act(async () => setOntologyText(JSON.stringify(await api("/ontology"), null, 2)));
      }}>온톨로지 관리</button>
    </nav>
    {error && <p role="alert" className="error">{error}</p>}
    {notice && <p role="status" className="notice">{notice}</p>}
    {tab === "presentation" ? <>
      <section className="panel">
        <h2>1. 한국어 텍스트 입력</h2>
        <label>발표 주제·요청·원고<textarea rows={6} maxLength={16000} value={text}
          placeholder="발표의 목적, 청중, 주요 내용을 입력하세요." onChange={e => setText(e.target.value)} /></label>
        <button disabled={busy || !text.trim()} onClick={() => act(async () => {
          const created = await api<{ id: string }>("/runs", "POST", { text });
          await selectRun(created.id); await refreshHistory();
        })}>개요 생성</button>
      </section>
      {history.length > 0 && <section className="panel">
        <label>저장된 실행<select value={run?.id || ""} disabled={busy}
          onChange={e => { if (e.target.value) act(() => selectRun(e.target.value)); }}>
          <option value="">실행 선택</option>
          {history.map(item => <option key={item.id} value={item.id}>
            {labels[item.status]} · {item.text.slice(0, 60)} · {item.id.slice(0, 8)}
          </option>)}
        </select></label>
      </section>}
      {run && <section className="panel" aria-live="polite">
        <h2>{labels[run.status]}</h2><p>{run.stage}</p>
        <p className="muted">실행 ID: {run.id}</p>
        {run.error && <p className="error" role="alert">{run.error}</p>}
      </section>}
      {outline && run && <section className="panel">
        <h2>2. 개요 확인{run.status === "outline_ready" && "·편집·확정"}</h2>
        <p>표지 포함 {outline.pages.length + 1}장 · {outline.chapters.length}개 챕터</p>
        <OutlineEditor outline={outline} onChange={setOutline} editable={run.status === "outline_ready" && !busy} />
        {run.status === "outline_ready" && <button disabled={busy} onClick={() => act(async () => {
          await api(`/runs/${run.id}/confirm`, "POST", { outline });
          await selectRun(run.id); await refreshHistory();
        })}>개요 확정 및 슬라이드 생성</button>}
      </section>}
      {run?.status === "completed" && <section className="panel">
        <h2>3. 전체 슬라이드 · {run.slides.length}장</h2>
        {run.slides.map((slide, index) => <article className="result" key={slide.page_id}>
          <h3>{index + 1}장 · 유형 {slide.type} · 레이아웃 {slide.layout.id}</h3>
          <Slide runId={run.id} index={index} title={slide.copy.title} />
        </article>)}
      </section>}
      {run && <details className="panel"><summary>Jev 후보·판단 결과 및 검사 기록 ({run.trace.length})</summary>
        <pre>{JSON.stringify(run.trace, null, 2)}</pre>
      </details>}
    </> : <section className="panel">
      <h2>온톨로지 조회·수정·검수·사용 전환</h2>
      <p>표현 유형과 지원 관계, 슬롯 역할·용량을 JSON으로 편집합니다. 검수 후 적용한 정의는 다음 생성에 반영됩니다.</p>
      <label>온톨로지 JSON<textarea className="json-editor" rows={30} spellCheck={false} value={ontologyText}
        onChange={e => { setOntologyText(e.target.value); setCheckedText(""); setNotice(""); }} /></label>
      <div className="actions">
        <button disabled={busy || !ontologyText} onClick={() => act(async () => {
          await api("/ontology/validate", "POST", JSON.parse(ontologyText));
          setCheckedText(ontologyText); setNotice("검수 통과. 수정 내용과 enabled 값을 확인한 뒤 적용하세요.");
        })}>수정 내용 검수</button>
        <button disabled={busy || !checkedText || checkedText !== ontologyText} onClick={() => act(async () => {
          await api("/ontology", "PUT", JSON.parse(ontologyText));
          setCheckedText(""); setNotice("적용 완료. 다음 슬라이드 생성부터 반영됩니다.");
        })}>검수한 정의·사용 여부 적용</button>
        <button disabled={busy} onClick={() => act(async () => {
          setOntologyText(JSON.stringify(await api<Ontology>("/ontology"), null, 2)); setCheckedText("");
        })}>최신 정의 조회</button>
      </div>
      {checkedText && <details open><summary>검수한 변경 내용 확인</summary><pre>{checkedText}</pre></details>}
    </section>}
  </main>;
}
