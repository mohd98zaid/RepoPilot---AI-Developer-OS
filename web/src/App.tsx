import { FormEvent, useEffect, useState } from "react";
import { api, downloadReport } from "./api";
import { Explorer } from "./Explorer";

type Repository = {
  id: string;
  display_name: string;
  local_path: string;
  branch: string;
  current_commit: string;
  dirty: boolean;
  index_status: string;
  indexed_file_count: number;
};

type Evidence = {
  path: string;
  line_start: number;
  line_end: number;
  excerpt: string;
};

type Task = {
  id: string;
  task_type: string;
  request: string;
  status: string;
  answer: string | null;
  created_at: string;
  diff_text?: string | null;
  diff_hash?: string | null;
  approval_status?: string;
  error?: string;
  evidence?: Evidence[];
  plan?: {action: string; query?: string}[];
  hypotheses?: {statement: string; distinguishing_check: string}[];
  verification?: object;
};

export default function App() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [path, setPath] = useState("");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [message, setMessage] = useState("Ready");
  const [error, setError] = useState("");
  const [taskRequest, setTaskRequest] = useState("");
  const [taskType, setTaskType] = useState<"explain" | "investigate" | "patch">("investigate");
  const [patchPath, setPatchPath] = useState("");
  const [patchContent, setPatchContent] = useState("");
  const [task, setTask] = useState<Task | null>(null);
  const [history, setHistory] = useState<Task[]>([]);
  const [settings, setSettings] = useState<{provider: string; model: string; remote: boolean; instructions: string} | null>(null);
  const [allowRemote, setAllowRemote] = useState(false);
  const [clarification, setClarification] = useState("");
  const [command, setCommand] = useState("python -m pytest");
  const [testBusy, setTestBusy] = useState(false);
  const [events, setEvents] = useState<{sequence: number; event_type: string}[]>([]);
  const [modelHealth, setModelHealth] = useState("");
  const [indexingId, setIndexingId] = useState("");
  const busy = task?.status === "running" || task?.status === "testing";

  const refresh = async () => {
    try {
      setRepositories(await api<Repository[]>("/api/repositories"));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to reach the API");
    }
  };

  useEffect(() => {
    void refresh();
    void api<typeof settings>("/api/settings").then(setSettings).catch((cause) => setError(String(cause)));
  }, []);

  useEffect(() => { setEvidence([]); setTask(null); setEvents([]); }, [selectedId]);

  useEffect(() => {
    if (!task?.id) return;
    let active = true;
    const update = async () => {
      try {
        const result = await api<Task>(`/api/tasks/${task.id}`);
        const log = await api<typeof events>(`/api/tasks/${task.id}/events`);
        if (!active) return;
        setTask(result); setEvents(log); setEvidence(result.evidence ?? []); setMessage(result.status);
        if (result.error) setError(result.error);
      } catch (cause) { if (active) setError(String(cause)); }
    };
    void update();
    const timer = busy ? window.setInterval(() => void update(), 700) : undefined;
    return () => { active = false; if (timer) window.clearInterval(timer); };
  }, [task?.id, busy]);

  const register = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setMessage("Registering repository…");
    try {
      const repository = await api<Repository>("/api/repositories", {
        method: "POST",
        body: JSON.stringify({ local_path: path }),
      });
      setPath("");
      setSelectedId(repository.id);
      await refresh();
      setMessage(`Registered ${repository.display_name}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Registration failed");
      setMessage("Registration failed");
    }
  };

  const index = async (repository: Repository) => {
    if (indexingId) return;
    setIndexingId(repository.id);
    setError("");
    setMessage(`Indexing ${repository.display_name}…`);
    try {
      await api(
        `/api/repositories/${repository.id}/index?background=true`,
        { method: "POST" },
      );
      let result: {index_status: string; indexed_file_count: number; index_error?: string} | null = null;
      for (let attempt = 0; attempt < 600; attempt++) {
        await new Promise((resolve) => window.setTimeout(resolve, 500));
        result = await api(`/api/repositories/${repository.id}/index-status`);
        if (result?.index_status !== "indexing") break;
      }
      if (result?.index_status !== "ready") throw new Error(result?.index_error ?? "Indexing is still running; inspect repository status");
      await refresh();
      setSelectedId(repository.id);
      setMessage(`Indexed ${result.indexed_file_count} files`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Indexing failed");
      setMessage("Indexing failed");
    }
    finally { setIndexingId(""); }
  };

  const search = async (event: FormEvent) => {
    event.preventDefault();
    if (!selectedId || !query.trim()) return;
    setError("");
    setMessage("Searching indexed evidence…");
    try {
      const result = await api<{ evidence: Evidence[] }>(
        `/api/repositories/${selectedId}/search`,
        { method: "POST", body: JSON.stringify({ query }) },
      );
      setEvidence(result.evidence);
      setMessage(`${result.evidence.length} evidence result(s)`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Search failed");
      setMessage("Search failed");
    }
  };

  const ask = async (event: FormEvent) => {
    event.preventDefault();
    if (!selectedId || !taskRequest.trim()) return;
    setError("");
    setMessage("Investigating repository evidence…");
    try {
      const result = await api<Task>("/api/tasks", {
        method: "POST",
        body: JSON.stringify({
          repository_id: selectedId,
          task_type: taskType,
          request: taskRequest,
          changes: taskType === "patch" && patchPath.trim() ? [{ path: patchPath, content: patchContent }] : [],
          background: true,
          allow_remote: allowRemote,
        }),
      });
      setTask(result);
      setTaskRequest("");
      setHistory((current) => [result, ...current.filter((item) => item.id !== result.id)].slice(0, 8));
      setMessage(result.status === "completed" ? "Investigation complete" : result.status);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Task failed");
      setMessage("Task failed");
    }
  };

  const decidePatch = async (decision: "approved" | "rejected") => {
    if (!task?.id || !task.diff_hash) return;
    try {
      const result = await api<Task>(`/api/tasks/${task.id}/approval`, {
        method: "POST",
        body: JSON.stringify({ action_hash: task.diff_hash, decision }),
      });
      setTask(result);
      setMessage(`Patch ${decision}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Approval failed");
    }
  };

  const taskAction = async (action: string, body: object = {}) => {
    if (!task) return;
    setError("");
    try {
      const result = await api<Task>(`/api/tasks/${task.id}/${action}`, {method: "POST", body: JSON.stringify(body)});
      setTask(result); setMessage(result.status);
    } catch (cause) { setError(String(cause)); }
  };

  const runTests = async () => {
    if (!task) return;
    setTestBusy(true); setError(""); setTask({...task, status: "testing"});
    try {
      await api(`/api/tasks/${task.id}/tests`, {method: "POST", body: JSON.stringify({command, compare_baseline: true})});
      setTask(await api<Task>(`/api/tasks/${task.id}`));
    } catch (cause) { setError(String(cause)); }
    finally { setTestBusy(false); }
  };

  const loadHistory = async (repositoryId: string) => {
    try {
      setHistory(await api<Task[]>(`/api/tasks?repository_id=${encodeURIComponent(repositoryId)}`));
    } catch {
      // The repository panel remains useful if history is unavailable.
    }
  };

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">LOCAL-FIRST DEVELOPER OS</p>
          <h1>RepoPilot</h1>
        </div>
        <span className="status" role="status"><i /> {message}</span>
      </header>

      <section className="hero">
        <div>
          <p className="eyebrow">REPOSITORY INTELLIGENCE</p>
          <h2>Understand the code before changing it.</h2>
          <p className="subtitle">
            Register a Git repository, build a safe local index, and search with line-numbered evidence.
          </p>
        </div>
        <div className="hero-mark" aria-hidden="true">⌘</div>
      </section>

      <details className="panel settings-panel">
        <summary>Model settings · {settings?.provider ?? "connecting"} / {settings?.model ?? "mock"}</summary>
        <p>{settings?.instructions}</p>
        <button onClick={() => { void api("/api/model/health").then((result) => setModelHealth(JSON.stringify(result))).catch((cause) => setError(String(cause))); }}>Check model connection</button>
        <pre>{modelHealth}</pre>
      </details>
      {settings?.remote && <label className="remote-consent"><input type="checkbox" checked={allowRemote} onChange={(event) => setAllowRemote(event.target.checked)} /> Allow requests and retrieved code excerpts to be sent to the configured remote provider.</label>}
      <section className="grid">
        <article className="panel">
          <div className="panel-heading">
            <div><p className="eyebrow">01 / WORKSPACE</p><h3>Repositories</h3></div>
            <span className="count">{repositories.length}</span>
          </div>
          <form className="register" onSubmit={register}>
            <label htmlFor="repository-path">Local repository path</label>
            <div className="input-row">
              <input id="repository-path" value={path} onChange={(event) => setPath(event.target.value)} placeholder="C:\\projects\\my-repository" required />
              <button type="submit">Register</button>
            </div>
          </form>
          {indexingId && <button onClick={() => {void api(`/api/repositories/${indexingId}/index/cancel`, {method: "POST"}).catch((cause) => setError(String(cause)));}}>Cancel indexing</button>}
          <div className="repo-list">
            {repositories.length === 0 && <p className="empty">No repositories registered yet.</p>}
            {repositories.map((repository) => (
              <div className={`repo-card ${selectedId === repository.id ? "selected" : ""}`} key={repository.id}>
                <button className="repo-select" onClick={() => { setSelectedId(repository.id); void loadHistory(repository.id); }}>
                <span className="repo-icon">{repository.display_name.slice(0, 1).toUpperCase()}</span>
                <span className="repo-info"><strong>{repository.display_name}</strong><small>{repository.branch} · {repository.dirty ? "dirty" : "clean"}</small></span>
                <span className={`pill ${repository.index_status}`}>{repository.index_status}</span>
                </button>
                <button className="repo-action" aria-label={`Index ${repository.display_name}`} onClick={() => void index(repository)}>Index</button>
              </div>
            ))}
          </div>
        </article>

        <article className="panel evidence-panel">
          <div className="panel-heading">
            <div><p className="eyebrow">02 / EVIDENCE</p><h3>Search the index</h3></div>
            <span className="live-dot">FTS5 LIVE</span>
          </div>
          <form className="search-form" onSubmit={search}>
            <input aria-label="Search repository" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search a symbol, error, or configuration key…" disabled={!selectedId} />
            <button type="submit" disabled={!selectedId}>Search</button>
          </form>
          <div className="evidence-list">
            {evidence.length === 0 && <p className="empty">Index a repository and search to see grounded file references.</p>}
            {evidence.map((item) => (
              <article className="evidence" key={`${item.path}-${item.line_start}`}>
                <div className="evidence-meta"><strong>{item.path}</strong><span>lines {item.line_start}–{item.line_end}</span></div>
                <pre>{item.excerpt}</pre>
              </article>
            ))}
          </div>
        </article>
      </section>

      {selectedId && <Explorer key={`${selectedId}-${repositories.find((r) => r.id === selectedId)?.indexed_file_count}`} repositoryId={selectedId} />}
      <section className="task-grid">
        <article className="panel task-panel">
          <div className="panel-heading">
            <div><p className="eyebrow">03 / INVESTIGATION</p><h3>Ask RepoPilot</h3></div>
            <span className="live-dot">{taskType === "patch" ? "ISOLATED PATCH" : "READ ONLY"}</span>
          </div>
          <form className="task-form" onSubmit={ask}>
            <div className="task-controls">
              <select aria-label="Task type" value={taskType} onChange={(event) => setTaskType(event.target.value as "explain" | "investigate" | "patch")} disabled={!selectedId || busy}>
                <option value="investigate">Investigate issue</option>
                <option value="explain">Explain architecture</option>
                <option value="patch">Propose patch</option>
              </select>
              <button type="submit" disabled={!selectedId || !taskRequest.trim() || busy || (settings?.remote && !allowRemote)}>Run task</button>
            </div>
            <textarea aria-label="Task request" value={taskRequest} onChange={(event) => setTaskRequest(event.target.value)} disabled={!selectedId || busy} placeholder="Where is authentication implemented? What could cause this error?" rows={3} />
            {taskType === "patch" && <details className="patch-fields"><summary>Optional manual change (leave blank for AI generation)</summary><input aria-label="Patch path" value={patchPath} onChange={(event) => setPatchPath(event.target.value)} placeholder="Relative file path, e.g. src/auth.py" disabled={!selectedId} /><textarea aria-label="Patch content" value={patchContent} onChange={(event) => setPatchContent(event.target.value)} placeholder="Complete proposed file content" rows={6} disabled={!selectedId} /></details>}
          </form>
          {busy && <button onClick={() => void taskAction("cancel")}>Cancel task</button>}
          {task?.plan && <details><summary>Investigation plan</summary><ol>{task.plan.map((step, i) => <li key={i}>{step.action} {step.query}</li>)}</ol></details>}
          {task?.answer && <div className="answer"><span className="answer-label">RESPONSE · {task.status}</span><p>{task.answer}</p></div>}
          {task?.status === "awaiting_input" && <form onSubmit={(event) => {event.preventDefault(); void taskAction("resume", {answer: clarification, allow_remote: allowRemote});}}><label htmlFor="clarification">Clarification</label><input id="clarification" value={clarification} onChange={(event) => setClarification(event.target.value)} required /><button>Resume investigation</button></form>}
          {task?.hypotheses?.map((item, i) => <article key={i}><h4>Hypothesis {i + 1}</h4><p>{item.statement}</p><p>Check: {item.distinguishing_check}</p></article>)}
          {task?.diff_text && task.approval_status === "pending" && <div className="patch-review"><span className="answer-label">PATCH REVIEW / {task.diff_hash?.slice(0, 12)}</span><pre>{task.diff_text}</pre><div className="approval-actions"><button onClick={() => void decidePatch("rejected")}>Reject</button><button onClick={() => void decidePatch("approved")}>Approve and apply</button></div></div>}
          {task?.approval_status === "pending" && <div className="task-controls"><select aria-label="Test command" value={command} onChange={(event) => setCommand(event.target.value)}>{["python -m pytest", "npm test", "npm run lint", "npm run build"].map((c) => <option key={c}>{c}</option>)}</select><button disabled={testBusy || busy} onClick={() => void runTests()}>Test baseline + patch</button></div>}
          {task?.verification && <details><summary>Verification and test output</summary><pre>{JSON.stringify(task.verification, null, 2)}</pre></details>}
          {task?.approval_status === "pending" && <button disabled={busy || testBusy} onClick={() => void taskAction("repair", {allow_remote: allowRemote})}>Repair verified regression (maximum 2 attempts)</button>}
          {task && <button onClick={() => void downloadReport(task.id).catch((cause) => setError(String(cause)))}>Export report</button>}
          {events.length > 0 && <details><summary>Workflow events</summary><ol>{events.map((event) => <li key={event.sequence}>{event.event_type}</li>)}</ol></details>}
        </article>
        <aside className="panel history-panel">
          <div className="panel-heading"><div><p className="eyebrow">04 / HISTORY</p><h3>Recent runs</h3></div><span className="count">{history.length}</span></div>
          {history.length === 0 ? <p className="empty">Completed investigations will appear here.</p> : <div className="history-list">{history.map((item) => <button key={item.id} className="history-item" onClick={() => setTask(item)}><span><strong>{item.task_type}</strong><small>{item.request}</small></span><em>{item.status}</em></button>)}</div>}
        </aside>
      </section>

      {error && <aside className="error" role="alert">{error}</aside>}
      <footer>RepoPilot / local repository intelligence / evidence before action</footer>
    </main>
  );
}
