#!/usr/bin/env bash
set -euo pipefail

SERVICE_DIR="$HOME/.config/systemd/user"
SOURCE_DIR="$HOME/EdgeHunter/scripts/systemd"

mkdir -p "$SERVICE_DIR"

ln -sf "$SOURCE_DIR/edgehunter-radar.service" "$SERVICE_DIR/edgehunter-radar.service"
ln -sf "$SOURCE_DIR/edgehunter-worker.service" "$SERVICE_DIR/edgehunter-worker.service"

systemctl --user daemon-reload
systemctl --user enable edgehunter-radar.service edgehunter-worker.service
systemctl --user start edgehunter-radar.service edgehunter-worker.service
