# Rapport TP03 - Supervision et observabilité

**Nom :** ………………  **Date :** ………………  **Environnement :** (OS, version Docker)………………

## 1. Objectif et architecture
Décrire en quelques lignes la plateforme et reprendre le schéma du README.

## 2. Configuration
| Élément | Choix retenu | Justification |
|---|---|---|
| `scrape_interval` | 15 s (30 s pour cAdvisor) | |
| `evaluation_interval` | 15 s | |
| Rétention | 15 jours | |
| Cibles | node-exporter, cadvisor, grafana, prometheus, blackbox (HTTP/TCP) | |

## 3. Dashboards
Insérer une capture par dashboard (dossier `captures/`).

| Dashboard | Capture | Principaux indicateurs |
|---|---|---|
| 01 - Système | `captures/01-systeme.png` | |
| 02 - CPU / RAM | `captures/02-cpu-ram.png` | |
| 03 - Réseau | `captures/03-reseau.png` | |
| 04 - Disponibilité | `captures/04-disponibilite.png` | |

## 4. Tests de supervision
| # | Scénario | Commande | Résultat attendu | Résultat observé | Capture |
|---|---|---|---|---|---|
| 1 | Cibles Prometheus | `./scripts/check-targets.sh` | Toutes UP | | `captures/targets.png` |
| 2 | Arrêt de `demo-web` | `./scripts/test-supervision.sh demo-web` | `probe_success=0`, alerte `ServiceProbeFailed` | | |
| 3 | Redémarrage | (fin du script) | `probe_success=1`, alerte résolue | | |
| 4 | Arrêt de `demo-redis` | `./scripts/test-supervision.sh demo-redis` | Sonde TCP à 0 | | |
| 5 | Arrêt de `node-exporter` | `./scripts/test-supervision.sh node-exporter` | `up=0`, alerte `TargetDown` après 1 min | | |
| 6 | Charge CPU | `./scripts/stress-cpu.sh 60` | Pic CPU visible dans le dashboard 02 | | |

Joindre les journaux `reports/test-supervision-*.log`.

## 5. Difficultés rencontrées et solutions

## 6. Pistes d'amélioration
(Alertmanager, notifications, rétention longue durée, supervision des applications des TP01/TP02…)

## 7. Conclusion
