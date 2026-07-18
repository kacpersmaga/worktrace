import type { Analysis, Demo, Explanation, Job } from "./types";

// Requests go to /api on the same origin; next.config.ts proxies them to the Python service.
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, { cache: "no-store", ...init });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  demos: () => request<Demo[]>("/demos"),
  openDemo: (key: string) => request<Job>(`/demos/${key}`, { method: "POST" }),
  recent: () => request<Job[]>("/analyses"),
  status: (id: string) => request<Job>(`/analyses/${id}/status`),
  analysis: (id: string) => request<Analysis>(`/analyses/${id}`),
  upload: (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<Job>("/analyses", { method: "POST", body });
  },
  explain: (id: string, kind: string, index: number) =>
    request<Explanation>(`/analyses/${id}/explain`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind, index }),
    }),
  bpmnUrl: (id: string) => `/api/analyses/${id}/bpmn`,
};
