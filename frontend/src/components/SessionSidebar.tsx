import type { SessionOut } from "../types";

interface SessionSidebarProps {
  sessions: SessionOut[];
  activeSessionId: string | null;
  onNewChat: () => void;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}

export default function SessionSidebar({
  sessions,
  activeSessionId,
  onNewChat,
  onSelect,
  onDelete,
}: SessionSidebarProps) {
  return (
    <aside className="session-sidebar">
      <button className="btn btn-primary new-chat-btn" onClick={onNewChat}>
        + New chat
      </button>
      <ul className="session-list">
        {sessions.length === 0 && (
          <li className="session-empty">No sessions yet</li>
        )}
        {sessions.map((s) => (
          <li
            key={s.id}
            className={
              "session-item" + (s.id === activeSessionId ? " active" : "")
            }
          >
            <button
              className="session-title"
              onClick={() => onSelect(s.id)}
              title={s.title ?? "Untitled session"}
            >
              {s.title || "Untitled session"}
              <span className="session-date">
                {new Date(s.created_at).toLocaleDateString()}
              </span>
            </button>
            <button
              className="btn-icon session-delete"
              aria-label="Delete session"
              title="Delete session"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(s.id);
              }}
            >
              ✕
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
}
