const incoming = new URLSearchParams(window.location.hash.slice(1)).get("token");
if (incoming) {
  sessionStorage.setItem("repopilot-session", incoming);
  history.replaceState(null, "", window.location.pathname);
}
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {...init, headers: {
    "Content-Type": "application/json", "X-RepoPilot-Token": sessionStorage.getItem("repopilot-session") ?? "", ...init?.headers,
  }, credentials: "same-origin"});
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    if (response.status === 401) {
      throw new Error("Local session expired. Reopen RepoPilot with launch.bat.");
    }
    throw new Error(typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? response.status));
  }
  return response.json() as Promise<T>;
}
export async function downloadReport(id: string) {
  const response = await fetch(`/api/tasks/${id}/report`, {headers: {"X-RepoPilot-Token": sessionStorage.getItem("repopilot-session") ?? ""}, credentials: "same-origin"});
  if (!response.ok) {
    if (response.status === 401) throw new Error("Local session expired. Reopen RepoPilot with launch.bat.");
    throw new Error("Report download failed");
  }
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url; link.download = `${id}.md`; link.click(); URL.revokeObjectURL(url);
}
