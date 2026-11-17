#!/usr/bin/env bash
# Génère une charge CPU pour valider le dashboard 02 (CPU/RAM).
# Usage : ./stress-cpu.sh [secondes=60] [workers=nb_cœurs]
set -euo pipefail
DURATION="${1:-60}"
WORKERS="${2:-$(nproc 2>/dev/null || echo 2)}"
echo "Charge CPU : $WORKERS processus pendant ${DURATION}s (Ctrl+C pour arrêter)"
docker run --rm --name tp03-stress alpine:3.20 sh -c '
  for i in $(seq '"$WORKERS"'); do
    timeout '"$DURATION"' sh -c "while :; do :; done" &
  done
  wait'
echo "Terminé."
