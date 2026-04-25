#!/bin/bash
cd /home/telematica/EdgeHunter
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git ls-remote origin HEAD | cut -f1)

if [ "$LOCAL" != "$REMOTE" ]; then
    echo "[$(date)] Nova versão detectada — iniciando deploy"
    /home/telematica/EdgeHunter/deploy/server/deploy.sh
fi
