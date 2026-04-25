#!/bin/bash
set -Eeuo pipefail

log() {
  echo "[Deploy] $1"
}

DEPLOY_DIR="/home/telematica/EdgeHunter"
BRANCH="main"

docker_compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  else
    docker-compose "$@"
  fi
}

log "Iniciando as $(date '+%Y-%m-%d %H:%M:%S')"
cd "$DEPLOY_DIR"

CURRENT_HEAD="$(git rev-parse HEAD)"
git fetch --prune origin
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"
NEW_HEAD="$(git rev-parse HEAD)"
log "Git pull OK: ${CURRENT_HEAD:0:7} -> ${NEW_HEAD:0:7}"

if git diff --name-only "$CURRENT_HEAD" "$NEW_HEAD" | grep -Eq '(^|/)(requirements\.txt|Dockerfile|docker-compose\.yml|\.py)$'; then
  log "Codigo ou dependencias mudaram; rebuild do backend"
  docker_compose build backend
  docker_compose up -d --remove-orphans backend
else
  log "Sem mudanca estrutural; restart do backend"
  docker_compose restart backend
fi

for attempt in {1..12}; do
  if curl -fsS http://localhost:5000/api/health >/dev/null; then
    log "Sistema saudavel"
    exit 0
  fi

  log "Health check falhou (tentativa $attempt/12), aguardando..."
  sleep 10
done

log "Health check falhou apos 120s"
docker_compose logs --tail=80 backend || true
exit 1
