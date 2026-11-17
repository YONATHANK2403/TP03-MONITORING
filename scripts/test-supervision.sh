#!/usr/bin/env bash
# Étape 5 du TP : arrêter un service, constater l'indisponibilité, le relancer.
# Usage : ./test-supervision.sh [service]      (défaut : demo-web)
#   service : demo-web | demo-redis | grafana | node-exporter | cadvisor | blackbox-exporter
# Variables : WAIT=60 (secondes d'attente)  NONINTERACTIVE=1 (pas de pause manuelle)
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROM="${PROM_URL:-http://localhost:9090}"
SERVICE="${1:-demo-web}"
WAIT="${WAIT:-60}"
LOG="$ROOT/reports/test-supervision-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1

query()  { python3 "$ROOT/scripts/prom_helper.py" query "$1"; }
status_expr="min(probe_success{service=\"$SERVICE\"} or up{service=\"$SERVICE\"})"
firing() { python3 "$ROOT/scripts/prom_helper.py" alerts; }
countdown() { for ((i=$1; i>0; i--)); do printf "\r  attente %2ds " "$i"; sleep 1; done; printf "\r%20s\r" ""; }

restore() { docker start "$SERVICE" >/dev/null 2>&1 || true; }
trap restore EXIT

echo "=============================================================="
echo " TEST DE SUPERVISION - service : $SERVICE - $(date '+%F %T')"
echo "=============================================================="

echo; echo "[1/5] État initial (1 = UP, 0 = DOWN)"
echo "  statut de $SERVICE : $(query "$status_expr")"
"$ROOT/scripts/check-targets.sh" || true

echo; echo "[2/5] Arrêt du service : docker stop $SERVICE"
docker stop "$SERVICE" >/dev/null && echo "  conteneur arrêté à $(date +%T)"

echo; echo "[3/5] Attente de $WAIT s (collecte 15 s + règle 'for: 30s')"
countdown "$WAIT"

echo "[4/5] Constat de l'indisponibilité"
echo "  statut de $SERVICE : $(query "$status_expr")   <- attendu : 0"
echo "  alertes :"; firing
"$ROOT/scripts/check-targets.sh" || true
echo
echo "  >> Ouvrir Grafana : dashboard '04 - Disponibilité des services'"
echo "     (tuile rouge, barre rouge dans l'historique, alerte dans la table)"
echo "  >> Ouvrir Prometheus : $PROM/targets  et  $PROM/alerts"
[[ "${NONINTERACTIVE:-0}" == "1" ]] || read -rp "  Faites vos captures d'écran puis appuyez sur Entrée pour redémarrer le service... "

echo; echo "[5/5] Redémarrage : docker start $SERVICE"
docker start "$SERVICE" >/dev/null && echo "  conteneur relancé à $(date +%T)"
countdown "$WAIT"
echo "  statut de $SERVICE : $(query "$status_expr")   <- attendu : 1"
echo "  alertes :"; firing
echo; echo "Journal enregistré : $LOG"
