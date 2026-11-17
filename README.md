# TP03 - Supervision et observabilité

Plateforme de supervision **autonome** (aucune dépendance aux TP01 / TP02) :
Prometheus collecte, Node Exporter / cAdvisor / Blackbox exposent les métriques,
Grafana les affiche dans 4 dashboards provisionnés automatiquement.

```
                       ┌────────────────── réseau Docker « monitoring » ──────────────────┐
 Hôte Linux            │                                                                  │
 ┌───────────────┐     │  ┌────────────┐  scrape   ┌──────────────┐   ┌─────────────┐     │
 │ node-exporter │◄────┼──┤            ├──────────►│  cAdvisor    │   │ demo-web    │◄─┐  │
 │ (network host)│     │  │ Prometheus │           └──────────────┘   │ demo-redis  │  │  │
 └───────────────┘     │  │   :9090    │  scrape   ┌──────────────┐   └─────────────┘  │  │
                       │  │            ├──────────►│  Blackbox    ├────── sondes ──────┘  │
                       │  └─────┬──────┘           └──────────────┘                       │
                       │        │ PromQL                                                 │
                       │  ┌─────▼──────┐                                                 │
                       │  │  Grafana   │  :3000  → 4 dashboards                          │
                       │  └────────────┘                                                 │
                       └──────────────────────────────────────────────────────────────────┘
```

## Arborescence

```
TP03-MONITORING/
├── docker-compose.yml            # stack complète
├── docker-compose.desktop.yml    # surcharge Docker Desktop (Windows/macOS)
├── .env.example                  # ports, mot de passe Grafana, rétention
├── prometheus/
│   ├── prometheus.yml            # cibles + intervalles de collecte
│   ├── rules/alerts.yml          # règles d'alerte
│   └── targets/{http,tcp}.yml    # services sondés (rechargés à chaud)
├── grafana/
│   ├── provisioning/             # datasource Prometheus + chargement des dashboards
│   └── dashboards/               # 01-systeme, 02-cpu-ram, 03-reseau, 04-disponibilite (JSON)
├── exporters/                    # config Blackbox + exemples d'exporters applicatifs
├── scripts/                      # start, check-targets, test-supervision, stress-cpu, générateur
├── reports/                      # modèle de rapport + journaux de tests + captures
└── README.md
```

## Prérequis
- Docker Engine + Docker Compose v2 (`docker compose version`)
- Un hôte **Linux** (VM, serveur, WSL2 avec Docker Engine). Ports libres : 3000, 9090, 8081, 9115, 9100.
- Scripts en bash : Linux, WSL ou Git Bash.

## Démarrage

```bash
cp .env.example .env          # optionnel : changer le mot de passe Grafana
./scripts/start.sh            # valide la config, lance la stack, affiche l'état des cibles
```

Docker Desktop (Windows/macOS) : `DOCKER_DESKTOP=1 ./scripts/start.sh`
(les métriques décrivent alors la VM Docker et non la machine physique).

| Service | URL | Identifiants |
|---|---|---|
| Grafana | http://localhost:3000 | `admin` / `admin` (ou valeur du `.env`) |
| Prometheus | http://localhost:9090 (menus *Status > Targets*, *Alerts*) | - |
| cAdvisor | http://localhost:8081 | - |
| Blackbox | http://localhost:9115 | - |

Arrêt : `docker compose down` · Remise à zéro (supprime les données) : `docker compose down -v`

## Ce qui est configuré, étape par étape

**Étape 1 - Prometheus** (`prometheus/prometheus.yml`) : collecte toutes les 15 s
(30 s pour cAdvisor, plus coûteux), évaluation des règles toutes les 15 s, rétention 15 jours.
Cibles : `prometheus`, `node-exporter`, `cadvisor`, `grafana`, `blackbox`, plus les sondes
`blackbox-http` et `blackbox-tcp` alimentées par `prometheus/targets/*.yml`.

**Étape 2 - Node Exporter** : déployé en `network_mode: host` et `pid: host` avec `/` monté en lecture seule,
afin de lire les vrais compteurs de l'hôte : CPU (`node_cpu_seconds_total`), RAM (`node_memory_*`),
disque (`node_filesystem_*`, `node_disk_*`), réseau (`node_network_*`), disponibilité (`up`, `node_boot_time_seconds`),
ressources système (`node_load*`, `node_procs_*`, `node_filefd_*`).

**Étape 3 - Grafana** : la datasource Prometheus (uid `prometheus`) et les dashboards sont
**provisionnés** : aucune configuration manuelle, tout est reproductible.

**Étape 4 - Dashboards** (dossier « Supervision TP03 », menu *Dashboards TP03* en haut de chaque page) :

| # | Dashboard | Contenu |
|---|---|---|
| 01 | Système | uptime, jauges CPU/RAM/disque/swap, charge par cœur, débit disque, processus, descripteurs, infos noyau |
| 02 | Ressources CPU / RAM | CPU par mode et par cœur, load average, répartition mémoire, swap, CPU/RAM par conteneur |
| 03 | Réseau | débits RX/TX par interface, paquets, erreurs/drops, connexions TCP, retransmissions, réseau par conteneur |
| 04 | Disponibilité des services | cibles UP/DOWN, tuile par service, historique (state timeline), % de disponibilité, latence, code HTTP, alertes actives, uptime des conteneurs |

**Étape 5 - Tests** : voir ci-dessous.

## Étape 5 - Tester la supervision

```bash
./scripts/check-targets.sh                 # toutes les cibles doivent être UP
./scripts/test-supervision.sh demo-web     # arrête demo-web, attend, constate, redémarre
./scripts/test-supervision.sh demo-redis   # idem pour la sonde TCP
./scripts/test-supervision.sh node-exporter# teste la perte d'une source de métriques (up = 0)
./scripts/stress-cpu.sh 60                 # charge CPU 60 s pour le dashboard 02
```

Le script `test-supervision.sh` enregistre un journal dans `reports/`. Pendant la pause, observer :

1. **Grafana > 04 - Disponibilité** : tuile du service en rouge, barre rouge dans l'historique,
   alerte `ServiceProbeFailed` dans le tableau (≈ 45 s après l'arrêt).
2. **Prometheus > Status > Targets** : sonde en état `DOWN` ; **Alerts** : `pending` puis `firing`.
3. **Prometheus > Graph** : `probe_success{service="demo-web"}` passe à `0` ;
   `up{job="node-exporter"}` à `0` si l'on arrête Node Exporter.

À la relance, `probe_success` repasse à `1` et l'alerte se résout. Les captures vont dans `reports/captures/`.

## Intégrer d'autres services plus tard

Tout se fait sans toucher au cœur de la stack : ajouter une ligne dans `prometheus/targets/http.yml`
ou `tcp.yml` (prise en compte en 30 s), ou ajouter un exporter applicatif.
Détails dans [`exporters/README.md`](exporters/README.md). Le réseau Docker `monitoring` est rattachable depuis un autre projet.

## Dépannage

| Symptôme | Cause probable / solution |
|---|---|
| `node-exporter` DOWN sur Linux | Pare-feu (ufw/firewalld) bloquant le port 9100 depuis le pont Docker : `sudo ufw allow from 172.16.0.0/12 to any port 9100` |
| Erreur `path / is mounted on / but it is not a shared or slave mount` | Docker Desktop : utiliser `DOCKER_DESKTOP=1 ./scripts/start.sh` |
| Panneaux « conteneurs » vides | cAdvisor n'a pas accès à Docker : vérifier les volumes et `docker logs cadvisor` |
| Dashboards vides juste après le démarrage | Attendre 1-2 min (il faut au moins 2 points de collecte pour un `rate()`) |
| Modification de `prometheus.yml` | `curl -X POST localhost:9090/-/reload` ou `docker compose restart prometheus` |
| Valider la config avant de lancer | `docker run --rm --entrypoint promtool -v "$PWD/prometheus:/etc/prometheus:ro" prom/prometheus:v2.55.1 check config /etc/prometheus/prometheus.yml` |
| Modifier un dashboard « pour de bon » | Éditer `scripts/generate_dashboards.py`, relancer `python3 scripts/generate_dashboards.py` |

## Checklist de validation TP03

- [ ] `docker compose ps` : tous les conteneurs `Up` (Prometheus et Grafana `healthy`)
- [ ] Prometheus > Targets : toutes les cibles `UP`
- [ ] Grafana : les 4 dashboards sont présents dans « Supervision TP03 » et affichent des données
- [ ] Arrêt de `demo-web` : indisponibilité visible dans Grafana et Prometheus, alerte déclenchée
- [ ] Redémarrage : retour à la normale
- [ ] `reports/` contient le rapport complété, les captures et les journaux de test
# TP03-MONITORING
