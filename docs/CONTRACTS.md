# CONTRACTS — RAG-basic-implementation

> **FROZEN — do not edit during wave 2.** Downstream services must conform to this document; report drift to the integration plan.

This is the single source of truth for every endpoint, port, model shape, payload schema, and env var name shared across the parallel workstreams (WS-R=retrieval, WS-C=chat, WS-I=infra). Wave-2 plans read this file verbatim and never edit it.

---

## Ports & Proxy

| Service    | Container port | Host port | Compose service name |
| ---------- | -------------- | --------- | -------------------- |
| Ingestion  | 8002           | 8002      | `ingestion`          |
| Retrieval  | 8003           | 8003      | `retrieval`          |
| Chat Agent | 8001           | 8001      | `chat`               |
| Frontend   | 80 (nginx)     | 3000      | `frontend`           |

Retrieval service listens on 8003, internal only — NOT routed through nginx (host port 8003 published for dev/debug).

- Ingestion service listens on **8002**; Chat Agent service on **8001**; frontend nginx on **3000** (container 80).
- nginx reverse-proxies (trailing slash on both sides, **no CORS**):
  - `/api/ingest/` → `http://ingestion:8002/`
  - `/api/rag/` → `http://chat:8001/` (frontend proxy path stays `/api/rag/` — unchanged for the frontend; only the upstream container name changes)

---

## Ingestion Endpoints (`:8002`, proxied at `/api/ingest/`)

| Method   | Path              | Request                     | Response                                                        |
| -------- | ----------------- | --------------------------- | --------------------------------------------------------------- |
| `POST`   | `/documents`      | multipart form field `file` | `202` with `DocumentOut` (`status=pending`)                     |
| `GET`    | `/documents`      | —                           | `list[DocumentOut]`                                             |
| `GET`    | `/documents/{id}` | —                           | `DocumentOut` (`404` if missing)                                |
| `DELETE` | `/documents/{id}` | —                           | `204`; deletes Postgres rows + Qdrant points for that `doc_id`  |
| `GET`    | `/health`         | —                           | `{"status":"ok"}`                                               |

---

## Chat Agent Endpoints (`:8001`, proxied at `/api/rag/`)

| Method   | Path                      | Request                                                | Response                                                            |
| -------- | ------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------- |
| `POST`   | `/sessions`               | body `{title?: string}`                                | `SessionOut`                                                        |
| `GET`    | `/sessions`               | —                                                      | `list[SessionOut]`                                                  |
| `GET`    | `/sessions/{id}/messages` | —                                                      | `list[MessageOut]`                                                  |
| `DELETE` | `/sessions/{id}`          | —                                                      | `204`; deletes session rows **and** the langgraph checkpoint thread |
| `POST`   | `/chat`                   | `ChatRequest {session_id: uuid, message: string, top_k: int = 8}` | `ChatResponse {session_id, answer, citations: list[Citation]}` |
| `GET`    | `/health`                 | —                                                      | `{"status":"ok"}`                                                   |

The /chat retrieve step now calls the Retrieval service over HTTP; a non-200 from Retrieval surfaces as a 500 from /chat (acceptable for v1.1).

---

## Retrieval Endpoints (`:8003`, internal — no nginx route)

| Method | Path        | Request                                          | Response                                        |
| ------ | ----------- | ------------------------------------------------ | ----------------------------------------------- |
| `POST` | `/retrieve` | `RetrieveRequest {query: string, top_k: int = 8}` | `RetrieveResponse {parents: list[ParentContext]}` |
| `GET`  | `/health`   | —                                                | `{"status":"ok"}`                               |

---

## Pydantic Model Shapes

Field names and types are **frozen**. Both services and the frontend `types.ts` mirror these exactly.

### DocumentOut

| Field          | Type                                                    |
| -------------- | ------------------------------------------------------- |
| `id`           | uuid str                                                |
| `filename`     | str                                                     |
| `content_type` | str                                                     |
| `status`       | `"pending"` \| `"processing"` \| `"completed"` \| `"failed"` |
| `error`        | str \| null                                             |
| `num_pages`    | int \| null                                             |
| `num_parents`  | int \| null                                             |
| `num_children` | int \| null                                             |
| `created_at`   | iso str                                                 |
| `updated_at`   | iso str                                                 |

### ChatRequest

| Field        | Type              |
| ------------ | ----------------- |
| `session_id` | uuid str          |
| `message`    | str               |
| `top_k`      | int (default `8`) |

### Citation

| Field          | Type          |
| -------------- | ------------- |
| `index`        | int (1-based) |
| `doc_id`       | uuid str      |
| `filename`     | str           |
| `parent_id`    | uuid str      |
| `heading_path` | list[str]     |
| `page_start`   | int \| null   |
| `page_end`     | int \| null   |

### ParentContext

Retrieval response element (`RetrieveResponse.parents`); the chat service maps it to `Citation` via `build_numbered_context`.

| Field          | Type        |
| -------------- | ----------- |
| `parent_id`    | uuid str    |
| `doc_id`       | uuid str    |
| `filename`     | str         |
| `heading_path` | list[str]   |
| `content`      | str         |
| `page_start`   | int \| null |
| `page_end`     | int \| null |
| `score`        | float       |

### ChatResponse

| Field        | Type             |
| ------------ | ---------------- |
| `session_id` | uuid str         |
| `answer`     | str              |
| `citations`  | list[Citation]   |

### SessionOut

| Field        | Type        |
| ------------ | ----------- |
| `id`         | uuid str    |
| `title`      | str \| null |
| `created_at` | iso str     |
| `updated_at` | iso str     |

### MessageOut

| Field        | Type                        |
| ------------ | --------------------------- |
| `id`         | uuid str                    |
| `session_id` | uuid str                    |
| `role`       | `"user"` \| `"assistant"`   |
| `content`    | str                         |
| `citations`  | list[Citation] \| null      |
| `created_at` | iso str                     |

---

## Qdrant Payload Schema

- Collection: **`rag_children`**
- `VectorParams`: `size=1024`, `distance=COSINE`

Payload per child point:

| Field          | Type        |
| -------------- | ----------- |
| `parent_id`    | str         |
| `doc_id`       | str         |
| `filename`     | str         |
| `text`         | str         |
| `heading_path` | list[str]   |
| `page_no`      | int \| null |
| `pages`        | list[int]   |
| `child_index`  | int         |

Payload indexes: `doc_id` (KEYWORD), `parent_id` (KEYWORD).

---

## Embedding Convention (critical)

- Model: `intfloat/multilingual-e5-large` — **1024-dim, cosine, L2-normalized**.
- Prefix indexed child text with `"passage: "`.
- Prefix query text with `"query: "`.
- Both services fail fast if `EMBEDDING_DIM != model.get_sentence_embedding_dimension()`.

---

## Env Var Names (canonical list, see `.env.example`)

| Name                | Purpose                                          |
| ------------------- | ------------------------------------------------ |
| `POSTGRES_USER`     | Postgres user                                    |
| `POSTGRES_PASSWORD` | Postgres password                                |
| `POSTGRES_DB`       | Postgres database name                           |
| `DATABASE_URL`      | Full Postgres DSN (host = compose service `postgres`) |
| `QDRANT_URL`        | Qdrant HTTP URL                                  |
| `QDRANT_COLLECTION` | Qdrant collection name (`rag_children`)          |
| `EMBEDDING_MODEL`   | SentenceTransformers model id                    |
| `EMBEDDING_DIM`     | Embedding dimension (`1024`)                     |
| `LLM_MODEL`         | `init_chat_model` model string                   |
| `GROQ_API_KEY`      | Groq API key (required for chat)                 |
| `INGESTION_PORT`    | Ingestion service port (`8002`)                  |
| `RETRIEVAL_PORT`    | Retrieval service port (`8003`)                  |
| `RETRIEVAL_URL`     | Retrieval service base URL (`http://retrieval:8003`, used by chat) |
| `CHAT_PORT`         | Chat Agent service port (`8001`)                 |
| `FRONTEND_PORT`     | Frontend host port (`3000`)                      |
