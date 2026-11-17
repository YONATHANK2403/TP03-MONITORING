#!/usr/bin/env bash
# Démarre la stack de supervision et vérifie que tout répond.
set -euo pipefail
cd "$(dirname "$0")/.."

command -v docker >/dev/null || { echo "Docker n'est pas installé."; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "Docker Compose v2 requis (docker compose)."; exit 1; }

COMPOSE_FILES=(-f docker-compose.yml)
if [[ "${DOCKER_DESKTOP:-0}" == "1" ]]; then
  COMPOSE_FILES+=(-f docker-compose.desktop.yml)
  echo ">> Mode Docker Desktop activé"
fi

echo ">> Validation de la configuration Prometheus..."
docker run --rm --entrypoint promtool -v "$PWD/prometheus:/etc/prometheus:ro" \
  prom/prometheus:v2.55.1 check config /etc/prometheus/prometheus.yml

echo ">> Démarrage de la stack..."
docker compose "${COMPOSE_FILES[@]}" up -d

PROM="http://localhost:${PROMETHEUS_PORT:-9090}"
GRAFANA="http://localhost:${GRAFANA_PORT:-3000}"

echo -n ">> Attente de Prometheus"
for _ in $(seq 1 30); do curl -fs "$PROM/-/ready" >/dev/null 2>&1 && break; echo -n "."; sleep 2; done
echo
echo -n ">> Attente de Grafana"
for _ in $(seq 1 30); do curl -fs "$GRAFANA/api/health" >/dev/null 2>&1 && break; echo -n "."; sleep 2; done
echo

echo ">> Première collecte (20 s)..."
sleep 20
"$(dirname "$0")/check-targets.sh" || true

cat <<MSG

  Prometheus : $PROM
  Grafana    : $GRAFANA   (identifiants : ${GRAFANA_ADMIN_USER:-admin} / ${GRAFANA_ADMIN_PASSWORD:-admin})
  cAdvisor   : http://localhost:${CADVISOR_PORT:-8081}
  Blackbox   : http://localhost:${BLACKBOX_PORT:-9115}

MSG
