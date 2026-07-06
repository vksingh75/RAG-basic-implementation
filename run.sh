#!/usr/bin/env bash
# RAG-basic-implementation — single control file for the docker compose stack.
# Usage: ./run.sh {start|stop|restart|status|logs} [service]
set -euo pipefail

cd "$(dirname "$0")"

usage() {
  echo "Usage: ./run.sh {start|stop|restart|status|logs} [service]"
  echo ""
  echo "  start            Build (if needed) and start the full stack detached"
  echo "  stop             Stop and remove all containers"
  echo "  restart [svc]    Restart the whole stack or a single service"
  echo "  status           Show container status"
  echo "  logs [svc]       Follow logs (last 100 lines) for all or one service"
  echo ""
  echo "Services: postgres qdrant ingestion retrieval chat frontend"
}

cmd="${1:-}"

case "$cmd" in
  start)
    docker compose up -d --build
    ;;
  stop)
    docker compose down
    ;;
  restart)
    shift
    docker compose restart "$@"
    ;;
  status)
    docker compose ps
    ;;
  logs)
    shift
    docker compose logs -f --tail=100 "$@"
    ;;
  *)
    usage
    exit 1
    ;;
esac
