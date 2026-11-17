#!/usr/bin/env python3
"""Petit client de l'API HTTP Prometheus (utilisé par les scripts bash).

  prom_helper.py targets            -> tableau des cibles, code 1 si une cible est DOWN
  prom_helper.py query "<promql>"   -> valeur(s) de la requête instantanée
  prom_helper.py alerts             -> alertes pending / firing
"""
import json
import os
import sys
import urllib.parse
import urllib.request

PROM = os.environ.get("PROM_URL", "http://localhost:9090")


def get(path, **params):
    url = PROM + path + ("?" + urllib.parse.urlencode(params) if params else "")
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.load(r)["data"]


def cmd_targets():
    targets = get("/api/v1/targets", state="active")["activeTargets"]
    targets.sort(key=lambda t: (t["labels"].get("job", ""), t["labels"].get("instance", "")))
    print(f"{'JOB':<16} {'INSTANCE':<34} {'ETAT':<6} DERNIER ECHEC")
    print("-" * 90)
    down = 0
    for t in targets:
        ok = t["health"] == "up"
        down += 0 if ok else 1
        print(f"{t['labels'].get('job', '?'):<16} {t['labels'].get('instance', '?')[:34]:<34} "
              f"{'UP' if ok else 'DOWN':<6} {t.get('lastError', '')[:60]}")
    print("-" * 90)
    print(f"{len(targets)} cibles, {down} DOWN")
    return 1 if down else 0


def cmd_query(expr):
    res = get("/api/v1/query", query=expr)["result"]
    print(", ".join(x["value"][1] for x in res) if res else "aucune donnée")
    return 0


def cmd_alerts():
    alerts = [a for a in get("/api/v1/alerts")["alerts"] if a["state"] in ("firing", "pending")]
    if not alerts:
        print("  (aucune alerte)")
    for a in alerts:
        print(f"  [{a['state']:<7}] {a['labels']['alertname']:<20} {a['annotations'].get('summary', '')}")
    return 0


if __name__ == "__main__":
    try:
        if len(sys.argv) >= 2 and sys.argv[1] == "targets":
            sys.exit(cmd_targets())
        if len(sys.argv) >= 3 and sys.argv[1] == "query":
            sys.exit(cmd_query(sys.argv[2]))
        if len(sys.argv) >= 2 and sys.argv[1] == "alerts":
            sys.exit(cmd_alerts())
        print(__doc__)
        sys.exit(2)
    except OSError as e:
        print(f"Prometheus injoignable sur {PROM} : {e}")
        sys.exit(3)
