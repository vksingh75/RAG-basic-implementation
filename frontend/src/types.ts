// TypeScript mirrors of the frozen Pydantic model shapes in docs/CONTRACTS.md.
// Field names and optionality match the contract EXACTLY — do not drift.

export type DocumentStatus = "pending" | "processing" | "completed" | "failed";

export interface DocumentOut {
  id: string;
  filename: string;
  content_type: string;
  status: DocumentStatus;
  error: string | null;
  num_pages: number | null;
  num_parents: number | null;
  num_children: number | null;
  created_at: string;
  updated_at: string;
}

export interface ChatRequest {
  session_id: string;
  message: string;
  top_k?: number; // server default: 8
}

export interface Citation {
  index: number; // 1-based
  doc_id: string;
  filename: string;
  parent_id: string;
  heading_path: string[];
  page_start: number | null;
  page_end: number | null;
}

export interface ChatResponse {
  session_id: string;
  answer: string;
  citations: Citation[];
}

export interface SessionOut {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface MessageOut {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[] | null;
  created_at: string;
}
