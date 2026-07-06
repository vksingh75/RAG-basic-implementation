import type { DocumentOut } from "../types";

// Proxied by nginx (prod) / vite dev proxy: /api/ingest/ -> ingestion service :8002
const BASE = "/api/ingest";

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Ingest API ${res.status}: ${text || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export async function uploadDocument(file: File): Promise<DocumentOut> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/documents`, {
    method: "POST",
    body: form,
  });
  return handle<DocumentOut>(res);
}

export async function listDocuments(): Promise<DocumentOut[]> {
  const res = await fetch(`${BASE}/documents`);
  return handle<DocumentOut[]>(res);
}

export async function getDocument(id: string): Promise<DocumentOut> {
  const res = await fetch(`${BASE}/documents/${id}`);
  return handle<DocumentOut>(res);
}

export async function deleteDocument(id: string): Promise<void> {
  const res = await fetch(`${BASE}/documents/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Ingest API ${res.status}: ${text || res.statusText}`);
  }
}
