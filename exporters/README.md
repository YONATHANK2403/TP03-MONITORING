# Exporters et sondes

| Exporter | Où | Rôle |
|---|---|---|
| Node Exporter | `docker-compose.yml` (hôte, `network_mode: host`) | CPU, RAM, disque, réseau, uptime de l'hôte |
| cAdvisor | `docker-compose.yml` | CPU / RAM / réseau par conteneur |
| Blackbox Exporter | `docker-compose.yml` + `blackbox/blackbox.yml` | Sondes HTTP et TCP : disponibilité des services |

## Ajouter un service à surveiller (sans exporter)

Éditer `prometheus/targets/http.yml` (HTTP) ou `prometheus/targets/tcp.yml` (port TCP) :

```yaml
- targets: ["http://mon-app:8080/health"]
  labels: { service: mon-app, tier: application }
```

Prometheus relit ces fichiers toutes les 30 s : aucun redémarrage. Le service apparaît
automatiquement dans le dashboard « 04 - Disponibilité des services ».

## Ajouter un exporter applicatif (métriques internes)

1. Copier le bloc voulu depuis `examples/docker-compose.exporters.example.yml`
   (Nginx, Redis, PostgreSQL, MySQL).
2. Déclarer le scrape dans `prometheus/prometheus.yml` :
   ```yaml
   - job_name: redis
     static_configs:
       - targets: ["redis-exporter:9121"]
         labels: { service: demo-redis }
   ```
3. Recharger sans redémarrer : `curl -X POST http://localhost:9090/-/reload`

## Superviser des services d'un autre projet Docker

Le réseau `monitoring` a un nom fixe. Dans l'autre projet :

```yaml
services:
  mon-app:
    networks: [monitoring]
networks:
  monitoring:
    external: true
```

Puis ajouter `http://mon-app:<port>` dans `prometheus/targets/http.yml`.
