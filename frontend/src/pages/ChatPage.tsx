import { useCallback, useEffect, useState } from "react";
import {
  createSession,
  deleteSession,
  getMessages,
  listSessions,
  sendChat,
} from "../api/rag";
import type { MessageOut, SessionOut } from "../types";
import SessionSidebar from "../components/SessionSidebar";
import MessageList from "../components/MessageList";
import ChatInput from "../components/ChatInput";

export default function ChatPage() {
  const [sessions, setSessions] = useState<SessionOut[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageOut[]>([]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshSessions = useCallback(async () => {
    try {
      setSessions(await listSessions());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    void refreshSessions();
  }, [refreshSessions]);

  async function handleSelect(id: string) {
    setActiveSessionId(id);
    setError(null);
    try {
      setMessages(await getMessages(id));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setMessages([]);
    }
  }

  async function handleNewChat() {
    setError(null);
    try {
      const session = await createSession();
      setSessions((prev) => [session, ...prev]);
      setActiveSessionId(session.id);
      setMessages([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleDelete(id: string) {
    setError(null);
    try {
      await deleteSession(id);
      if (id === activeSessionId) {
        setActiveSessionId(null);
        setMessages([]);
      }
      await refreshSessions();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleSend(message: string) {
    setError(null);
    let sessionId = activeSessionId;
    setSending(true);
    try {
      // Auto-create a session on first message if none is active.
      if (!sessionId) {
        const session = await createSession();
        setSessions((prev) => [session, ...prev]);
        setActiveSessionId(session.id);
        sessionId = session.id;
      }

      // Optimistically append the user message.
      const optimistic: MessageOut = {
        id: `optimistic-${Date.now()}`,
        session_id: sessionId,
        role: "user",
        content: message,
        citations: null,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, optimistic]);

      const res = await sendChat({
        session_id: sessionId,
        message,
        top_k: 8,
      });

      const assistant: MessageOut = {
        id: `assistant-${Date.now()}`,
        session_id: res.session_id,
        role: "assistant",
        content: res.answer,
        citations: res.citations,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistant]);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="chat-page">
      <SessionSidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onNewChat={() => void handleNewChat()}
        onSelect={(id) => void handleSelect(id)}
        onDelete={(id) => void handleDelete(id)}
      />
      <section className="chat-main">
        {error && <div className="error-banner">{error}</div>}
        <MessageList messages={messages} loading={sending} />
        <ChatInput disabled={sending} onSend={(m) => void handleSend(m)} />
      </section>
    </div>
  );
}
