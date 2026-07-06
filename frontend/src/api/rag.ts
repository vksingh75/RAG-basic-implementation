import type {
  ChatRequest,
  ChatResponse,
  MessageOut,
  SessionOut,
} from "../types";

// Proxied by nginx (prod) / vite dev proxy: /api/rag/ -> rag service :8001
const BASE = "/api/rag";

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`RAG API ${res.status}: ${text || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export async function createSession(title?: string): Promise<SessionOut> {
  const res = await fetch(`${BASE}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(title !== undefined ? { title } : {}),
  });
  return handle<SessionOut>(res);
}

export async function listSessions(): Promise<SessionOut[]> {
  const res = await fetch(`${BASE}/sessions`);
  return handle<SessionOut[]>(res);
}

export async function getMessages(sessionId: string): Promise<MessageOut[]> {
  const res = await fetch(`${BASE}/sessions/${sessionId}/messages`);
  return handle<MessageOut[]>(res);
}

export async function deleteSession(id: string): Promise<void> {
  const res = await fetch(`${BASE}/sessions/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`RAG API ${res.status}: ${text || res.statusText}`);
  }
}

export async function sendChat(req: ChatRequest): Promise<ChatResponse> {
  const res = await fetch(`${BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  return handle<ChatResponse>(res);
}
