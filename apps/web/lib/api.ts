const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/v1";

async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function createNotebook(title: string) {
  return post("/notebooks", { title });
}

export function askNotebook(notebookId: string, query: string) {
  return post(`/notebooks/${notebookId}/ask`, { query });
}

export function solve(content: string, notebookId?: string) {
  return post("/solve", { input_type: "text", content, notebook_id: notebookId });
}

export function generateArtifact(notebookId: string, artifactType: string) {
  return post(`/notebooks/${notebookId}/artifacts/generate`, { artifact_type: artifactType });
}
