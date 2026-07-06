#!/usr/bin/env bash
# RAG-basic-implementation — end-to-end smoke test.
#
# Exercises the full pipeline: upload sample PDF -> poll ingestion until
# completed -> assert parent/child chunks -> assert Qdrant points -> hit the
# retrieval service directly (/health + /retrieve) -> create a chat session ->
# ask a question grounded in the PDF (expect citations) -> in-session memory
# follow-up.
#
# We hit the ingestion (8002), retrieval (8003), and chat (8001) service ports
# directly rather than the nginx proxy at :3000 — that keeps the smoke test
# independent of the frontend container and makes failures easier to attribute.
#
# NOTE: the checkpoint-restart test (docker compose restart chat, then ask
# "what was my first question?") lives in the integration plan (Z), not here.
#
# Requires: curl, jq. The stack must already be running (./run.sh start).
set -euo pipefail

INGEST_BASE="http://localhost:${INGESTION_PORT:-8002}"
RAG_BASE="http://localhost:${RAG_PORT:-8001}"
RETRIEVAL_BASE="http://localhost:${RETRIEVAL_PORT:-8003}"
QDRANT_BASE="http://localhost:6333"
SAMPLE_PDF="$(dirname "$0")/sample/sample.pdf"
POLL_TIMEOUT_SECS=180
POLL_INTERVAL_SECS=3

PASS_COUNT=0
FAIL_COUNT=0

pass() {
  PASS_COUNT=$((PASS_COUNT + 1))
  echo "  PASS: $1"
}

fail() {
  FAIL_COUNT=$((FAIL_COUNT + 1))
  echo "  FAIL: $1" >&2
}

die() {
  echo "FATAL: $1" >&2
  echo ""
  echo "=== SMOKE TEST FAILED ==="
  exit 1
}

command -v curl >/dev/null || die "curl is required"
command -v jq >/dev/null || die "jq is required"
[ -f "$SAMPLE_PDF" ] || die "sample PDF not found at $SAMPLE_PDF"

echo "=== RAG-basic-implementation e2e smoke test ==="
echo "ingestion: $INGEST_BASE | retrieval: $RETRIEVAL_BASE | chat: $RAG_BASE | qdrant: $QDRANT_BASE"
echo ""

# --- 1. Upload sample PDF ---------------------------------------------------
echo "[1/8] Uploading sample PDF..."
UPLOAD_RESP=$(curl -fsS -X POST "$INGEST_BASE/documents" \
  -F "file=@${SAMPLE_PDF};type=application/pdf") \
  || die "upload request to $INGEST_BASE/documents failed"
DOC_ID=$(echo "$UPLOAD_RESP" | jq -r '.id // empty')
[ -n "$DOC_ID" ] || die "upload response missing document id: $UPLOAD_RESP"
pass "uploaded sample.pdf -> document_id=$DOC_ID"

# --- 2. Poll until status == completed ---------------------------------------
echo "[2/8] Polling document status (timeout ${POLL_TIMEOUT_SECS}s)..."
DEADLINE=$(( $(date +%s) + POLL_TIMEOUT_SECS ))
STATUS=""
DOC_JSON=""
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  DOC_JSON=$(curl -fsS "$INGEST_BASE/documents/$DOC_ID") \
    || die "GET /documents/$DOC_ID failed"
  STATUS=$(echo "$DOC_JSON" | jq -r '.status')
  case "$STATUS" in
    completed)
      break
      ;;
    failed)
      echo "$DOC_JSON" | jq . >&2
      die "ingestion failed: $(echo "$DOC_JSON" | jq -r '.error // "unknown error"')"
      ;;
    *)
      sleep "$POLL_INTERVAL_SECS"
      ;;
  esac
done
[ "$STATUS" = "completed" ] || die "timed out waiting for status=completed (last status: $STATUS)"
pass "document status=completed"

# --- 3. Assert parent/child counts -------------------------------------------
echo "[3/8] Checking chunk counts..."
NUM_PARENTS=$(echo "$DOC_JSON" | jq -r '.num_parents // 0')
NUM_CHILDREN=$(echo "$DOC_JSON" | jq -r '.num_children // 0')
if [ "$NUM_PARENTS" -gt 0 ]; then
  pass "num_parents=$NUM_PARENTS (> 0)"
else
  fail "num_parents=$NUM_PARENTS (expected > 0)"
fi
if [ "$NUM_CHILDREN" -gt 0 ]; then
  pass "num_children=$NUM_CHILDREN (> 0)"
else
  fail "num_children=$NUM_CHILDREN (expected > 0)"
fi

# --- 4. Assert Qdrant points --------------------------------------------------
echo "[4/8] Checking Qdrant collection rag_children..."
POINTS=$(curl -fsS "$QDRANT_BASE/collections/rag_children" \
  | jq -r '.result.points_count // 0') \
  || die "GET $QDRANT_BASE/collections/rag_children failed"
if [ "$POINTS" -gt 0 ]; then
  pass "qdrant points_count=$POINTS (> 0)"
else
  fail "qdrant points_count=$POINTS (expected > 0)"
fi

# --- 5. Retrieval service: health + direct /retrieve --------------------------
echo "[5/8] Checking retrieval service (/health + /retrieve)..."
RETRIEVAL_HEALTH=$(curl -fsS "$RETRIEVAL_BASE/health" | jq -r '.status // empty') \
  || die "GET $RETRIEVAL_BASE/health failed"
if [ "$RETRIEVAL_HEALTH" = "ok" ]; then
  pass "retrieval /health status=ok"
else
  fail "retrieval /health status=$RETRIEVAL_HEALTH (expected ok)"
fi

RETRIEVE_RESP=$(curl -fsS -X POST "$RETRIEVAL_BASE/retrieve" \
  -H "Content-Type: application/json" \
  -d '{"query":"At what depth is the Meridian Deep-Sea Observatory located?","top_k":8}') \
  || die "POST $RETRIEVAL_BASE/retrieve failed"
PARENT_COUNT=$(echo "$RETRIEVE_RESP" | jq -r '.parents | length')
if [ "$PARENT_COUNT" -gt 0 ]; then
  pass "retrieve parents count=$PARENT_COUNT (> 0)"
else
  fail "retrieve parents array is empty (expected > 0): $RETRIEVE_RESP"
fi
FIRST_PARENT_ID=$(echo "$RETRIEVE_RESP" | jq -r '.parents[0].parent_id // empty')
FIRST_FILENAME=$(echo "$RETRIEVE_RESP" | jq -r '.parents[0].filename // empty')
HAS_PAGE_START=$(echo "$RETRIEVE_RESP" | jq -r '.parents[0] | has("page_start")')
if [ -n "$FIRST_PARENT_ID" ]; then
  pass "first parent has non-empty parent_id=$FIRST_PARENT_ID"
else
  fail "first parent missing parent_id: $RETRIEVE_RESP"
fi
if [ -n "$FIRST_FILENAME" ]; then
  pass "first parent has non-empty filename=$FIRST_FILENAME"
else
  fail "first parent missing filename: $RETRIEVE_RESP"
fi
if [ "$HAS_PAGE_START" = "true" ]; then
  pass "first parent has page_start field"
else
  fail "first parent missing page_start field: $RETRIEVE_RESP"
fi

# --- 6. Create chat session ---------------------------------------------------
echo "[6/8] Creating chat session..."
SESSION_RESP=$(curl -fsS -X POST "$RAG_BASE/sessions" \
  -H "Content-Type: application/json" \
  -d '{"title": "e2e smoke"}') \
  || die "POST /sessions failed"
SESSION_ID=$(echo "$SESSION_RESP" | jq -r '.id // empty')
[ -n "$SESSION_ID" ] || die "session response missing id: $SESSION_RESP"
pass "created session_id=$SESSION_ID"

# --- 7. Chat with citations ----------------------------------------------------
# Question answerable only from scripts/sample/sample.pdf.
echo "[7/8] Asking a question grounded in the sample PDF..."
CHAT_RESP=$(curl -fsS -X POST "$RAG_BASE/chat" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"At what depth is the Meridian Deep-Sea Observatory located, and how many researchers does it accommodate?\", \"top_k\": 8}") \
  || die "POST /chat failed"
ANSWER=$(echo "$CHAT_RESP" | jq -r '.answer // empty')
CITATION_COUNT=$(echo "$CHAT_RESP" | jq -r '.citations | length')
if [ -n "$ANSWER" ]; then
  pass "chat answer is non-empty"
else
  fail "chat answer is empty: $CHAT_RESP"
fi
if [ "$CITATION_COUNT" -gt 0 ]; then
  pass "citations count=$CITATION_COUNT (> 0)"
else
  fail "citations array is empty (expected > 0)"
fi

# --- 8. Memory follow-up --------------------------------------------------------
echo "[8/8] Testing in-session memory follow-up..."
FOLLOWUP_RESP=$(curl -fsS -X POST "$RAG_BASE/chat" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"Summarize your previous answer in one sentence.\", \"top_k\": 8}") \
  || die "follow-up POST /chat failed"
FOLLOWUP_ANSWER=$(echo "$FOLLOWUP_RESP" | jq -r '.answer // empty')
if [ -n "$FOLLOWUP_ANSWER" ]; then
  pass "memory follow-up answer is non-empty"
else
  fail "memory follow-up answer is empty: $FOLLOWUP_RESP"
fi

# --- Summary --------------------------------------------------------------------
echo ""
echo "=== SUMMARY: $PASS_COUNT passed, $FAIL_COUNT failed ==="
if [ "$FAIL_COUNT" -gt 0 ]; then
  echo "=== SMOKE TEST FAILED ==="
  exit 1
fi
echo "=== SMOKE TEST PASSED ==="
