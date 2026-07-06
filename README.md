# RAG-basic-implementation

A Retrieval-Augmented Generation application built as three independent services
plus infrastructure, fully runnable with one command.

- **Ingestion service** (FastAPI, `:8002`) — PDF upload, docling hierarchical
  extraction, parent-child chunking, embeddings into Qdrant.
- **RAG service** (FastAPI + LangGraph, `:8001`) — chat sessions with grounded,
  cited answers and persistent conversation memory.
- **Frontend** (React + Vite behind nginx, `:3000`) — chat and upload pages.
- **Infra** — Postgres 16, Qdrant, docker compose orchestration.

API and schema contracts live in [`docs/CONTRACTS.md`](docs/CONTRACTS.md).

## Quick start

1. **Configure environment**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and set `GROQ_API_KEY` (required for chat; get one at
   https://console.groq.com). All other defaults work out of the box.

2. **Start the stack**

   ```bash
   ./run.sh start
   ```

   > **Note:** the first boot downloads the ~2.2 GB
   > `intfloat/multilingual-e5-large` embedding model into the shared
   > `hf_cache` volume. It can take a couple of minutes before the
   > `ingestion` and `rag` services report healthy. Watch progress with
   > `./run.sh logs ingestion`.

3. **Use the app**

   Open <http://localhost:3000>:

   - **Upload page** — drop in a PDF and watch its status go
     `pending → processing → completed`.
   - **Chat page** — create a session and ask questions about your uploaded
     documents. Answers include numbered citations with filename, heading
     path, and page numbers.

## run.sh commands

| Command                  | What it does                                          |
| ------------------------ | ----------------------------------------------------- |
| `./run.sh start`         | Build (if needed) and start the full stack detached   |
| `./run.sh stop`          | Stop and remove all containers                        |
| `./run.sh restart [svc]` | Restart the whole stack or a single service           |
| `./run.sh status`        | Show container status                                 |
| `./run.sh logs [svc]`    | Follow logs (last 100 lines) for all or one service   |

Service names: `postgres`, `qdrant`, `ingestion`, `rag`, `frontend`.

## Service ports

| Service   | Host port | Notes                                        |
| --------- | --------- | -------------------------------------------- |
| frontend  | 3000      | nginx; proxies `/api/ingest/` and `/api/rag/` |
| rag       | 8001      | FastAPI + LangGraph                          |
| ingestion | 8002      | FastAPI                                      |
| qdrant    | 6333      | Vector store HTTP API                        |
| postgres  | 5432      | Internal to the compose network              |

## End-to-end smoke test

With the stack running (`./run.sh start`, wait for services to be healthy):

```bash
./scripts/e2e_smoke.sh
```

The script uploads `scripts/sample/sample.pdf`, polls until ingestion
completes, verifies parent/child chunks and Qdrant points exist, then runs a
cited chat exchange plus an in-session memory follow-up. It exits non-zero on
any failed assertion. Requires `curl` and `jq` on the host.

## Repository layout

```
docker-compose.yml       # 5-service stack definition
run.sh                   # single control file (start|stop|restart|status|logs)
docs/CONTRACTS.md        # frozen API/schema contracts
infra/postgres/init.sql  # relational schema, applied on first postgres boot
services/ingestion/      # ingestion service source
services/rag/            # RAG service source
frontend/                # React frontend + nginx
scripts/e2e_smoke.sh     # end-to-end smoke test
scripts/sample/          # sample PDF used by the smoke test
```
