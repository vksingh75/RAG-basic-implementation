import { useCallback, useEffect, useRef, useState } from "react";
import { deleteDocument, listDocuments } from "../api/ingest";
import type { DocumentOut } from "../types";

const POLL_INTERVAL_MS = 3000;

interface DocumentTableProps {
  refreshToken: number;
}

export default function DocumentTable({ refreshToken }: DocumentTableProps) {
  const [documents, setDocuments] = useState<DocumentOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    try {
      const docs = await listDocuments();
      setDocuments(docs);
      setError(null);
      return docs;
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      return [];
    }
  }, []);

  // Initial load + reload when an upload completes.
  useEffect(() => {
    void refresh();
  }, [refresh, refreshToken]);

  // Poll every ~3s while any document is pending/processing; stop otherwise.
  const anyInFlight = documents.some(
    (d) => d.status === "pending" || d.status === "processing",
  );

  useEffect(() => {
    if (anyInFlight && timerRef.current === null) {
      timerRef.current = setInterval(() => {
        void refresh();
      }, POLL_INTERVAL_MS);
    }
    if (!anyInFlight && timerRef.current !== null) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    return () => {
      if (timerRef.current !== null) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [anyInFlight, refresh]);

  async function handleDelete(id: string) {
    setError(null);
    try {
      await deleteDocument(id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div className="document-table-wrap">
      {error && <div className="error-banner">{error}</div>}
      <table className="document-table">
        <thead>
          <tr>
            <th>Filename</th>
            <th>Status</th>
            <th>Pages</th>
            <th>Parents</th>
            <th>Children</th>
            <th>Error</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {documents.length === 0 && (
            <tr>
              <td colSpan={7} className="table-empty">
                No documents uploaded yet
              </td>
            </tr>
          )}
          {documents.map((d) => (
            <tr key={d.id}>
              <td className="cell-filename">{d.filename}</td>
              <td>
                <span className={`status status-${d.status}`}>{d.status}</span>
              </td>
              <td>{d.num_pages ?? "—"}</td>
              <td>{d.num_parents ?? "—"}</td>
              <td>{d.num_children ?? "—"}</td>
              <td className="cell-error">{d.error ?? ""}</td>
              <td>
                <button
                  className="btn-icon"
                  aria-label={`Delete ${d.filename}`}
                  title="Delete document"
                  onClick={() => void handleDelete(d.id)}
                >
                  ✕
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
