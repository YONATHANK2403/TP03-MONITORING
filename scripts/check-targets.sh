#!/usr/bin/env bash
# Affiche l'état de toutes les cibles Prometheus. Code retour 1 si une cible est DOWN.
exec python3 "$(dirname "$0")/prom_helper.py" targets
