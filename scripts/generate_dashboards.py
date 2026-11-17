#!/usr/bin/env python3
"""
Génère les 4 dashboards Grafana du TP03 dans grafana/dashboards/.

Les JSON sont versionnés dans le dépôt : ce script n'est PAS nécessaire pour
déployer la stack. Il sert à regénérer / faire évoluer les dashboards proprement
(ajouter un panneau = ajouter une ligne ici, puis `python3 scripts/generate_dashboards.py`).
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "grafana" / "dashboards"
DS = {"type": "prometheus", "uid": "prometheus"}

# Jetons remplacés dans les requêtes PromQL (évite de doubler les accolades)
FS_EXCLUDE = "tmpfs|overlay|squashfs|ramfs|devtmpfs|nsfs|proc|sysfs|fuse.*|cgroup.*"
TOKENS = {
    "@I@": 'instance=~"$instance"',
    "@D@": 'device=~"$device"',
    "@F@": f'fstype!~"{FS_EXCLUDE}"',
}


def q(expr: str) -> str:
    for k, v in TOKENS.items():
        expr = expr.replace(k, v)
    return expr


# ----------------------------------------------------------------- briques
_pid = 0


def _next() -> int:
    global _pid
    _pid += 1
    return _pid


def thr(*steps):
    """thr((None,'green'),(70,'orange'),(90,'red'))"""
    return {"mode": "absolute", "steps": [{"color": c, "value": v} for v, c in steps]}


GREEN_ORANGE_RED = thr((None, "green"), (70, "orange"), (90, "red"))
UPDOWN = [{
    "type": "value",
    "options": {
        "0": {"text": "DOWN", "color": "red", "index": 0},
        "1": {"text": "UP", "color": "green", "index": 1},
    },
}]


def targets(*items):
    """items : (expr, legend) ou (expr, legend, {instant/table})"""
    out = []
    for i, it in enumerate(items):
        expr, legend = it[0], it[1]
        opts = it[2] if len(it) > 2 else {}
        t = {"datasource": DS, "editorMode": "code", "expr": q(expr),
             "legendFormat": legend, "refId": chr(65 + i)}
        if opts.get("instant"):
            t.update(instant=True, range=False)
        if opts.get("table"):
            t["format"] = "table"
        out.append(t)
    return out


def _panel(ptype, title, x, y, w, h, tg, desc, fc, opts, extra=None):
    p = {"id": _next(), "type": ptype, "title": title, "description": desc,
         "datasource": DS, "gridPos": {"x": x, "y": y, "w": w, "h": h},
         "targets": tg, "fieldConfig": fc, "options": opts}
    if extra:
        p.update(extra)
    return p


def row(title, y):
    return {"id": _next(), "type": "row", "title": title, "collapsed": False,
            "gridPos": {"x": 0, "y": y, "w": 24, "h": 1}, "panels": []}


def ts(title, x, y, w, h, tg, unit="short", desc="", stack=False, fill=10,
       vmin=None, vmax=None, thresholds=None):
    d = {"unit": unit, "color": {"mode": "palette-classic"},
         "custom": {"drawStyle": "line", "lineWidth": 1, "fillOpacity": fill,
                    "showPoints": "never", "spanNulls": False,
                    "stacking": {"mode": "normal" if stack else "none", "group": "A"}}}
    if vmin is not None:
        d["min"] = vmin
    if vmax is not None:
        d["max"] = vmax
    if thresholds:
        d["thresholds"] = thresholds
    opts = {"legend": {"showLegend": True, "displayMode": "table", "placement": "bottom",
                       "calcs": ["mean", "max", "lastNotNull"]},
            "tooltip": {"mode": "multi", "sort": "desc"}}
    return _panel("timeseries", title, x, y, w, h, tg, desc,
                  {"defaults": d, "overrides": []}, opts)


def stat(title, x, y, w, h, tg, unit="none", thresholds=None, desc="", mappings=None,
         gauge=False, vmin=None, vmax=None, color_mode="background", no_value=None,
         graph="area", text_size=None):
    d = {"unit": unit, "color": {"mode": "thresholds"},
         "thresholds": thresholds or thr((None, "blue"))}
    if mappings:
        d["mappings"] = mappings
    if vmin is not None:
        d["min"] = vmin
    if vmax is not None:
        d["max"] = vmax
    if no_value is not None:
        d["noValue"] = no_value
    reduce = {"calcs": ["lastNotNull"], "fields": "", "values": False}
    if gauge:
        opts = {"reduceOptions": reduce, "showThresholdLabels": False,
                "showThresholdMarkers": True, "orientation": "auto"}
        return _panel("gauge", title, x, y, w, h, tg, desc,
                      {"defaults": d, "overrides": []}, opts)
    opts = {"reduceOptions": reduce, "colorMode": color_mode, "graphMode": graph,
            "textMode": "auto", "justifyMode": "auto", "orientation": "auto"}
    if text_size:
        opts["text"] = {"valueSize": text_size}
    return _panel("stat", title, x, y, w, h, tg, desc,
                  {"defaults": d, "overrides": []}, opts)


def bargauge(title, x, y, w, h, tg, unit="percent", thresholds=None, desc="",
             vmin=0, vmax=100):
    d = {"unit": unit, "color": {"mode": "thresholds"},
         "thresholds": thresholds or GREEN_ORANGE_RED}
    if vmin is not None:
        d["min"] = vmin
    if vmax is not None:
        d["max"] = vmax
    opts = {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "orientation": "horizontal", "displayMode": "gradient", "showUnfilled": True,
            "valueMode": "color"}
    return _panel("bargauge", title, x, y, w, h, tg, desc,
                  {"defaults": d, "overrides": []}, opts)


def state_timeline(title, x, y, w, h, tg, desc=""):
    d = {"mappings": UPDOWN, "color": {"mode": "thresholds"},
         "thresholds": thr((None, "red"), (1, "green")),
         "custom": {"fillOpacity": 80, "lineWidth": 0}}
    opts = {"mergeValues": True, "showValue": "never", "alignValue": "center",
            "rowHeight": 0.8, "legend": {"showLegend": False},
            "tooltip": {"mode": "single", "sort": "none"}}
    return _panel("state-timeline", title, x, y, w, h, tg, desc,
                  {"defaults": d, "overrides": []}, opts)


def table(title, x, y, w, h, tg, exclude=(), desc="", rename=None):
    excl = {k: True for k in ("Time", "Value", "__name__", *exclude)}
    tr = [{"id": "organize", "options": {"excludeByName": excl,
                                         "renameByName": rename or {}}}]
    return _panel("table", title, x, y, w, h, tg, desc,
                  {"defaults": {"custom": {"align": "auto"}}, "overrides": []},
                  {"showHeader": True, "cellHeight": "sm"},
                  {"transformations": tr})


# ------------------------------------------------------------- variables
def qvar(name, label, query, regex=""):
    return {"name": name, "label": label, "type": "query", "datasource": DS,
            "definition": query, "query": {"query": query, "refId": "StandardVariableQuery"},
            "refresh": 2, "sort": 1, "multi": True, "includeAll": True, "allValue": ".*",
            "current": {"selected": True, "text": ["All"], "value": ["$__all"]},
            "regex": regex, "hide": 0, "options": []}


VAR_INSTANCE = qvar("instance", "Hôte", "label_values(node_uname_info, instance)")
VAR_DEVICE = qvar("device", "Interface",
                  'label_values(node_network_receive_bytes_total{instance=~"$instance"}, device)',
                  regex="/^(?!lo$|veth|br-|docker).*/")


def dashboard(uid, title, desc, panels, variables=()):
    return {
        "uid": uid, "title": title, "description": desc,
        "tags": ["tp03", "supervision"], "timezone": "browser",
        "schemaVersion": 39, "version": 1, "editable": True, "graphTooltip": 1,
        "refresh": "15s", "time": {"from": "now-1h", "to": "now"},
        "templating": {"list": list(variables)},
        "annotations": {"list": [{
            "builtIn": 1, "datasource": {"type": "grafana", "uid": "-- Grafana --"},
            "enable": True, "hide": True, "iconColor": "rgba(0, 211, 255, 1)",
            "name": "Annotations & Alerts", "type": "dashboard"}]},
        "links": [{"type": "dashboards", "title": "Dashboards TP03", "tags": ["tp03"],
                   "asDropdown": True, "includeVars": True, "keepTime": True,
                   "icon": "external link", "targetBlank": False}],
        "panels": panels,
    }


def save(name, dash):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(dash, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")
    print(f"  écrit : {name}  ({len(dash['panels'])} éléments)")


# Expressions réutilisées
CPU_PCT = '100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle",@I@}[$__rate_interval])) * 100)'
MEM_PCT = '(1 - node_memory_MemAvailable_bytes{@I@} / node_memory_MemTotal_bytes{@I@}) * 100'
DISK_PCT = ('100 - (node_filesystem_avail_bytes{@I@,@F@} '
            '/ node_filesystem_size_bytes{@I@,@F@} * 100)')


# =========================================================================
# 1. Dashboard SYSTÈME
# =========================================================================
def dash_systeme():
    global _pid
    _pid = 0
    p = []
    p += [
        stat("Uptime", 0, 0, 4, 4,
             targets(("time() - node_boot_time_seconds{@I@}", "{{instance}}")),
             unit="s", graph="none", desc="Durée depuis le dernier démarrage du serveur."),
        stat("CPU", 4, 0, 4, 4, targets((CPU_PCT, "{{instance}}")), unit="percent",
             thresholds=GREEN_ORANGE_RED, gauge=True, vmin=0, vmax=100),
        stat("RAM", 8, 0, 4, 4, targets((MEM_PCT, "{{instance}}")), unit="percent",
             thresholds=GREEN_ORANGE_RED, gauge=True, vmin=0, vmax=100),
        stat("Disque /", 12, 0, 4, 4,
             targets(('100 - (node_filesystem_avail_bytes{@I@,mountpoint="/"} '
                      '/ node_filesystem_size_bytes{@I@,mountpoint="/"} * 100)', "{{instance}}")),
             unit="percent", thresholds=thr((None, "green"), (75, "orange"), (90, "red")),
             gauge=True, vmin=0, vmax=100),
        stat("Swap", 16, 0, 4, 4,
             targets(('(1 - node_memory_SwapFree_bytes{@I@} / node_memory_SwapTotal_bytes{@I@}) * 100 '
                      'and node_memory_SwapTotal_bytes{@I@} > 0', "{{instance}}")),
             unit="percent", thresholds=thr((None, "green"), (30, "orange"), (60, "red")),
             gauge=True, vmin=0, vmax=100, no_value="0 (pas de swap)"),
        stat("Charge / cœur (5 min)", 20, 0, 4, 4,
             targets(('node_load5{@I@} / on (instance) count by (instance) '
                      '(node_cpu_seconds_total{mode="idle",@I@})', "{{instance}}")),
             thresholds=thr((None, "green"), (0.7, "orange"), (1, "red")), graph="area",
             desc="Load average 5 min divisé par le nombre de cœurs. > 1 = saturation."),
    ]
    p += [
        ts("Utilisation CPU", 0, 4, 12, 8, targets((CPU_PCT, "{{instance}}")),
           unit="percent", vmin=0, vmax=100, thresholds=GREEN_ORANGE_RED),
        ts("Utilisation RAM", 12, 4, 12, 8, targets((MEM_PCT, "{{instance}}")),
           unit="percent", vmin=0, vmax=100, thresholds=GREEN_ORANGE_RED),
        bargauge("Occupation disque par point de montage", 0, 12, 12, 8,
                 targets((DISK_PCT, "{{mountpoint}} ({{device}})", {"instant": True})),
                 thresholds=thr((None, "green"), (75, "orange"), (90, "red"))),
        ts("Débit disque (lecture / écriture)", 12, 12, 12, 8,
           targets(("sum by (instance) (rate(node_disk_read_bytes_total{@I@}[$__rate_interval]))",
                    "lecture {{instance}}"),
                   ("sum by (instance) (rate(node_disk_written_bytes_total{@I@}[$__rate_interval]))",
                    "écriture {{instance}}")), unit="Bps"),
        ts("Processus", 0, 20, 8, 8,
           targets(("node_procs_running{@I@}", "en cours {{instance}}"),
                   ("node_procs_blocked{@I@}", "bloqués {{instance}}"))),
        ts("Descripteurs de fichiers ouverts", 8, 20, 8, 8,
           targets(("node_filefd_allocated{@I@}", "alloués {{instance}}"),
                   ("node_filefd_maximum{@I@}", "maximum {{instance}}"))),
        ts("Changements de contexte & interruptions / s", 16, 20, 8, 8,
           targets(("rate(node_context_switches_total{@I@}[$__rate_interval])", "contexte {{instance}}"),
                   ("rate(node_intr_total{@I@}[$__rate_interval])", "interruptions {{instance}}")),
           unit="ops"),
        table("Informations système", 0, 28, 24, 5,
              targets(("node_uname_info{@I@}", "", {"instant": True, "table": True})),
              exclude=("job", "domainname", "service"),
              desc="Noyau, architecture et nom d'hôte (node_uname_info)."),
    ]
    return dashboard("tp03-systeme", "01 - Système (vue d'ensemble)",
                     "État global du serveur : CPU, RAM, disque, charge, processus.",
                     p, [VAR_INSTANCE])


# =========================================================================
# 2. Dashboard CPU / RAM
# =========================================================================
def dash_cpu_ram():
    global _pid
    _pid = 0
    p = []
    p += [
        stat("CPU", 0, 0, 6, 5, targets((CPU_PCT, "{{instance}}")), unit="percent",
             thresholds=GREEN_ORANGE_RED, gauge=True, vmin=0, vmax=100),
        stat("RAM utilisée", 6, 0, 6, 5, targets((MEM_PCT, "{{instance}}")), unit="percent",
             thresholds=GREEN_ORANGE_RED, gauge=True, vmin=0, vmax=100),
        stat("RAM disponible", 12, 0, 6, 5,
             targets(("node_memory_MemAvailable_bytes{@I@}", "{{instance}}")), unit="bytes",
             thresholds=thr((None, "red"), (500e6, "orange"), (1e9, "green")), graph="area"),
        stat("RAM totale", 18, 0, 6, 5,
             targets(("node_memory_MemTotal_bytes{@I@}", "{{instance}}")), unit="bytes",
             graph="none"),
    ]
    p.append(row("CPU", 5))
    p += [
        ts("CPU par mode (moyenne sur les cœurs)", 0, 6, 12, 8,
           targets(('avg by (mode) (rate(node_cpu_seconds_total{mode!="idle",@I@}[$__rate_interval])) * 100',
                    "{{mode}}")), unit="percent", stack=True, fill=30, vmin=0,
           desc="user = applications, system = noyau, iowait = attente disque, steal = hyperviseur."),
        ts("CPU par cœur", 12, 6, 12, 8,
           targets(('100 - avg by (cpu) (rate(node_cpu_seconds_total{mode="idle",@I@}[$__rate_interval])) * 100',
                    "cœur {{cpu}}")), unit="percent", vmin=0, vmax=100),
        ts("Load average (1 / 5 / 15 min)", 0, 14, 12, 7,
           targets(("node_load1{@I@}", "1 min"), ("node_load5{@I@}", "5 min"),
                   ("node_load15{@I@}", "15 min"),
                   ('count(node_cpu_seconds_total{mode="idle",@I@})', "nb cœurs")),
           desc="Une charge durablement supérieure au nombre de cœurs indique une saturation."),
        ts("Pression CPU : changements de contexte", 12, 14, 12, 7,
           targets(("rate(node_context_switches_total{@I@}[$__rate_interval])", "{{instance}}")),
           unit="ops"),
    ]
    p.append(row("Mémoire", 21))
    mem_used = ("node_memory_MemTotal_bytes{@I@} - node_memory_MemFree_bytes{@I@} "
                "- node_memory_Buffers_bytes{@I@} - node_memory_Cached_bytes{@I@} "
                "- node_memory_SReclaimable_bytes{@I@}")
    p += [
        ts("Répartition de la mémoire", 0, 22, 16, 8,
           targets((mem_used, "Utilisée"), ("node_memory_Buffers_bytes{@I@}", "Buffers"),
                   ("node_memory_Cached_bytes{@I@} + node_memory_SReclaimable_bytes{@I@}", "Cache"),
                   ("node_memory_MemFree_bytes{@I@}", "Libre")),
           unit="bytes", stack=True, fill=40, vmin=0),
        ts("Swap", 16, 22, 8, 8,
           targets(("node_memory_SwapTotal_bytes{@I@} - node_memory_SwapFree_bytes{@I@}", "Swap utilisé"),
                   ("rate(node_vmstat_pswpin{@I@}[$__rate_interval]) * 4096", "Swap in (o/s)"),
                   ("rate(node_vmstat_pswpout{@I@}[$__rate_interval]) * 4096", "Swap out (o/s)")),
           unit="bytes"),
    ]
    p.append(row("Conteneurs Docker (cAdvisor)", 30))
    p += [
        ts("CPU par conteneur (100 % = 1 cœur)", 0, 31, 12, 8,
           targets(('sum by (name) (rate(container_cpu_usage_seconds_total{name!=""}[$__rate_interval])) * 100',
                    "{{name}}")), unit="percent", vmin=0),
        ts("Mémoire par conteneur", 12, 31, 12, 8,
           targets(('container_memory_working_set_bytes{name!=""}', "{{name}}")), unit="bytes",
           vmin=0),
    ]
    return dashboard("tp03-cpu-ram", "02 - Ressources CPU / RAM",
                     "Analyse détaillée du CPU et de la mémoire, de l'hôte et des conteneurs.",
                     p, [VAR_INSTANCE])


# =========================================================================
# 3. Dashboard RÉSEAU
# =========================================================================
def dash_reseau():
    global _pid
    _pid = 0
    p = []
    rx = "rate(node_network_receive_bytes_total{@I@,@D@}[$__rate_interval])"
    tx = "rate(node_network_transmit_bytes_total{@I@,@D@}[$__rate_interval])"
    p += [
        stat("Débit entrant total", 0, 0, 6, 4, targets((f"sum({rx})", "RX")), unit="Bps",
             thresholds=thr((None, "green"))),
        stat("Débit sortant total", 6, 0, 6, 4, targets((f"sum({tx})", "TX")), unit="Bps",
             thresholds=thr((None, "blue"))),
        stat("Connexions TCP établies", 12, 0, 6, 4,
             targets(("sum(node_netstat_Tcp_CurrEstab{@I@})", "ESTABLISHED")),
             thresholds=thr((None, "green"))),
        stat("Erreurs + paquets perdus / s", 18, 0, 6, 4,
             targets(("sum(rate(node_network_receive_errs_total{@I@,@D@}[$__rate_interval]) "
                      "+ rate(node_network_transmit_errs_total{@I@,@D@}[$__rate_interval]) "
                      "+ rate(node_network_receive_drop_total{@I@,@D@}[$__rate_interval]) "
                      "+ rate(node_network_transmit_drop_total{@I@,@D@}[$__rate_interval]))", "erreurs")),
             unit="ops", thresholds=thr((None, "green"), (0.01, "orange"), (1, "red")),
             no_value="0"),
    ]
    p += [
        ts("Trafic reçu par interface", 0, 4, 12, 8, targets((rx, "{{device}}")), unit="Bps", fill=20),
        ts("Trafic émis par interface", 12, 4, 12, 8, targets((tx, "{{device}}")), unit="Bps", fill=20),
        ts("Paquets par seconde", 0, 12, 12, 8,
           targets(("rate(node_network_receive_packets_total{@I@,@D@}[$__rate_interval])", "RX {{device}}"),
                   ("rate(node_network_transmit_packets_total{@I@,@D@}[$__rate_interval])", "TX {{device}}")),
           unit="pps"),
        ts("Erreurs et paquets perdus", 12, 12, 12, 8,
           targets(("rate(node_network_receive_errs_total{@I@,@D@}[$__rate_interval])", "erreurs RX {{device}}"),
                   ("rate(node_network_transmit_errs_total{@I@,@D@}[$__rate_interval])", "erreurs TX {{device}}"),
                   ("rate(node_network_receive_drop_total{@I@,@D@}[$__rate_interval])", "drops RX {{device}}"),
                   ("rate(node_network_transmit_drop_total{@I@,@D@}[$__rate_interval])", "drops TX {{device}}")),
           unit="pps"),
    ]
    p.append(row("TCP", 20))
    p += [
        ts("Connexions TCP", 0, 21, 12, 8,
           targets(("node_netstat_Tcp_CurrEstab{@I@}", "établies"),
                   ("node_sockstat_TCP_inuse{@I@}", "en cours d'usage"),
                   ("node_sockstat_TCP_tw{@I@}", "TIME_WAIT"),
                   ("node_sockstat_TCP_alloc{@I@}", "allouées"))),
        ts("Ouvertures de connexions et retransmissions / s", 12, 21, 12, 8,
           targets(("rate(node_netstat_Tcp_ActiveOpens{@I@}[$__rate_interval])", "ouvertes (sortantes)"),
                   ("rate(node_netstat_Tcp_PassiveOpens{@I@}[$__rate_interval])", "acceptées (entrantes)"),
                   ("rate(node_netstat_Tcp_RetransSegs{@I@}[$__rate_interval])", "segments retransmis")),
           unit="ops", desc="Beaucoup de retransmissions = réseau dégradé ou saturé."),
    ]
    p.append(row("Interfaces et conteneurs", 29))
    p += [
        stat("État des interfaces", 0, 30, 8, 7,
             targets(("node_network_up{@I@,@D@}", "{{device}}")), mappings=UPDOWN,
             thresholds=thr((None, "red"), (1, "green")), graph="none"),
        ts("Réseau par conteneur - reçu", 8, 30, 8, 7,
           targets(('sum by (name) (rate(container_network_receive_bytes_total{name!=""}[$__rate_interval]))',
                    "{{name}}")), unit="Bps"),
        ts("Réseau par conteneur - émis", 16, 30, 8, 7,
           targets(('sum by (name) (rate(container_network_transmit_bytes_total{name!=""}[$__rate_interval]))',
                    "{{name}}")), unit="Bps"),
    ]
    return dashboard("tp03-reseau", "03 - Réseau",
                     "Trafic, paquets, erreurs, connexions TCP et conteneurs.",
                     p, [VAR_INSTANCE, VAR_DEVICE])


# =========================================================================
# 4. Dashboard DISPONIBILITÉ
# =========================================================================
def dash_disponibilite():
    global _pid
    _pid = 0
    p = []
    p += [
        stat("Cibles UP", 0, 0, 4, 4, targets(("count(up == 1) or vector(0)", "UP")),
             thresholds=thr((None, "green")), graph="none"),
        stat("Cibles DOWN", 4, 0, 4, 4, targets(("count(up == 0) or vector(0)", "DOWN")),
             thresholds=thr((None, "green"), (1, "red")), graph="none"),
        stat("Sondes OK", 8, 0, 4, 4, targets(("count(probe_success == 1) or vector(0)", "OK")),
             thresholds=thr((None, "green")), graph="none"),
        stat("Sondes en échec", 12, 0, 4, 4, targets(("count(probe_success == 0) or vector(0)", "KO")),
             thresholds=thr((None, "green"), (1, "red")), graph="none"),
        stat("Alertes actives", 16, 0, 4, 4,
             targets(('count(ALERTS{alertstate="firing"}) or vector(0)', "firing")),
             thresholds=thr((None, "green"), (1, "red")), graph="none"),
        stat("Conteneurs en marche", 20, 0, 4, 4,
             targets(('count(time() - container_last_seen{name!=""} < 60) or vector(0)', "conteneurs")),
             thresholds=thr((None, "blue")), graph="none",
             desc="Conteneurs vus par cAdvisor au cours de la dernière minute."),
    ]
    p.append(row("État courant des services (sondes Blackbox)", 4))
    p += [
        stat("Services", 0, 5, 24, 5,
             targets(("probe_success", "{{service}}")), mappings=UPDOWN,
             thresholds=thr((None, "red"), (1, "green")), graph="none", text_size=28,
             desc="Une tuile par service sondé (HTTP et TCP)."),
    ]
    p.append(row("Historique de disponibilité", 10))
    p += [
        state_timeline("Cibles Prometheus (up)", 0, 11, 12, 9,
                       targets(("up", "{{job}} · {{service}}")),
                       desc="up = 1 si Prometheus réussit à collecter la cible."),
        state_timeline("Sondes de service (probe_success)", 12, 11, 12, 9,
                       targets(("probe_success", "{{service}} ({{job}})")),
                       desc="Arrêter un conteneur doit faire passer sa barre au rouge."),
        bargauge("Disponibilité sur la période affichée", 0, 20, 12, 8,
                 targets(("avg_over_time(probe_success[$__range]) * 100", "{{service}}",
                          {"instant": True})),
                 thresholds=thr((None, "red"), (95, "orange"), (99, "green")),
                 desc="Moyenne de probe_success sur la plage de temps sélectionnée."),
        ts("Temps de réponse des sondes", 12, 20, 12, 8,
           targets(("probe_duration_seconds", "{{service}}")), unit="s"),
    ]
    p.append(row("Détails", 28))
    p += [
        ts("Code HTTP retourné", 0, 29, 8, 8,
           targets(("probe_http_status_code", "{{service}}")), thresholds=None,
           desc="200 attendu. 0 = pas de réponse."),
        ts("Durée de collecte par job (scrape_duration_seconds)", 8, 29, 8, 8,
           targets(("scrape_duration_seconds", "{{job}}")), unit="s"),
        bargauge("Uptime des conteneurs", 16, 29, 8, 8,
                 targets(('time() - container_start_time_seconds{name!=""}', "{{name}}",
                          {"instant": True})),
                 unit="s", thresholds=thr((None, "orange"), (300, "green")), vmin=0, vmax=None,
                 desc="Un uptime qui retombe à zéro = conteneur redémarré."),
        table("Alertes en cours", 0, 37, 24, 6,
              targets(('ALERTS{alertstate="firing"}', "", {"instant": True, "table": True})),
              exclude=("alertstate",),
              desc="Alertes définies dans prometheus/rules/alerts.yml (aussi visibles sur :9090/alerts)."),
    ]
    return dashboard("tp03-disponibilite", "04 - Disponibilité des services",
                     "Statut des cibles Prometheus, sondes HTTP/TCP, alertes, conteneurs.", p)


if __name__ == "__main__":
    print(f"Génération des dashboards dans {OUT}")
    save("01-systeme.json", dash_systeme())
    save("02-cpu-ram.json", dash_cpu_ram())
    save("03-reseau.json", dash_reseau())
    save("04-disponibilite.json", dash_disponibilite())
