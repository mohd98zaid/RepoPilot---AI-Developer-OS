import { useEffect, useState } from "react";
import { api } from "./api";

type Structure = { languages: {language: string; files: number}[]; relationships: {path: string; kind: string; source: string; target: string; line: number}[]; coverage: string };

export function Explorer({repositoryId}: {repositoryId: string}) {
  const [files, setFiles] = useState<string[]>([]);
  const [path, setPath] = useState("");
  const [content, setContent] = useState("");
  const [error, setError] = useState("");
  const [structure, setStructure] = useState<Structure | null>(null);
  useEffect(() => {
    let active = true;
    setFiles([]); setPath(""); setContent(""); setStructure(null); setError("");
    if (repositoryId) {
      void Promise.all([api<{files: string[]}>(`/api/repositories/${repositoryId}/files`), api<Structure>(`/api/repositories/${repositoryId}/structure`)])
        .then(([listing, map]) => { if (active) {setFiles(listing.files); setStructure(map);} })
        .catch((cause) => {if (active) setError(String(cause));});
    }
    return () => {active = false;};
  }, [repositoryId]);
  useEffect(() => {
    let active = true;
    setContent("");
    if (path && repositoryId) void api<{content: string}>(`/api/repositories/${repositoryId}/file?path=${encodeURIComponent(path)}&end_line=500`)
      .then((file) => {if (active) setContent(file.content);})
      .catch((cause) => {if (active) setError(String(cause));});
    return () => {active = false;};
  }, [path, repositoryId]);
  return <details className="panel settings-panel">
    <summary>Repository explorer and structure</summary>
    <label htmlFor="source-file">Source file (first 500 lines)</label>
    <select id="source-file" value={path} onChange={(event) => setPath(event.target.value)}><option value="">Select a file</option>{files.map((file) => <option key={file}>{file}</option>)}</select>
    {content && <pre>{content}</pre>}
    {error && <p role="alert">{error}</p>}
    {structure && <><p>{structure.languages.map((item) => `${item.language}: ${item.files}`).join(" · ")}</p><p>{structure.coverage}</p>
      <details><summary>Imports and call candidates ({structure.relationships.length})</summary><ul>{structure.relationships.map((item, index) => <li key={index}><code>{item.path}:{item.line}</code> — {item.source} → {item.target} ({item.kind})</li>)}</ul></details></>}
  </details>;
}
