import { useEffect, useRef } from "react";
import type { Citation, MessageOut } from "../types";

interface MessageListProps {
  messages: MessageOut[];
  loading: boolean;
}

function formatPages(c: Citation): string {
  if (c.page_start == null && c.page_end == null) return "";
  if (c.page_start != null && c.page_end != null) {
    return c.page_start === c.page_end
      ? `p. ${c.page_start}`
      : `pp. ${c.page_start}-${c.page_end}`;
  }
  return `p. ${c.page_start ?? c.page_end}`;
}

function CitationFootnotes({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) return null;
  return (
    <ol className="citations">
      {citations.map((c) => (
        <li key={c.index} className="citation" value={c.index}>
          <span className="citation-marker">[{c.index}]</span>{" "}
          <span className="citation-filename">{c.filename}</span>
          {c.heading_path.length > 0 && (
            <>
              {" — "}
              <span className="citation-heading">
                {c.heading_path.join(" > ")}
              </span>
            </>
          )}
          {formatPages(c) && (
            <>
              {" — "}
              <span className="citation-pages">{formatPages(c)}</span>
            </>
          )}
        </li>
      ))}
    </ol>
  );
}

export default function MessageList({ messages, loading }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  return (
    <div className="message-list">
      {messages.length === 0 && !loading && (
        <p className="messages-empty">
          Ask a question about your uploaded documents.
        </p>
      )}
      {messages.map((m) => (
        <div key={m.id} className={`message message-${m.role}`}>
          <div className="bubble">
            <p className="message-content">{m.content}</p>
            {m.role === "assistant" && m.citations && (
              <CitationFootnotes citations={m.citations} />
            )}
          </div>
        </div>
      ))}
      {loading && (
        <div className="message message-assistant">
          <div className="bubble bubble-loading">Thinking…</div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
