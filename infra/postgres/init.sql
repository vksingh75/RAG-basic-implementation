-- RAG-basic-implementation relational schema
-- Executed once on first Postgres boot (docker-entrypoint-initdb.d).
-- NOTE: LangGraph checkpoint tables are NOT created here — the RAG service's
-- AsyncPostgresSaver checkpointer.setup() creates them at startup.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE documents (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    filename     text NOT NULL,
    content_type text,
    status       text NOT NULL DEFAULT 'pending'
                 CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    error        text,
    num_pages    int,
    num_parents  int,
    num_children int,
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE parent_chunks (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id  uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    parent_index int NOT NULL,
    heading_path text[] NOT NULL DEFAULT '{}',
    content      text NOT NULL,
    page_start   int,
    page_end     int,
    token_count  int,
    UNIQUE (document_id, parent_index)
);

-- chat_sessions.id IS the langgraph thread_id
CREATE TABLE chat_sessions (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title      text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE chat_messages (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role       text NOT NULL CHECK (role IN ('user', 'assistant')),
    content    text NOT NULL,
    citations  jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_parent_chunks_document_id ON parent_chunks (document_id);
CREATE INDEX idx_chat_messages_session_created ON chat_messages (session_id, created_at);
