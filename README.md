# 🛡️ Restore-Drill

> An automated Site Reliability Engineering (SRE) disaster recovery engine that extracts backup snapshots, measures RTO/RPO SLAs, executes integrity smoke tests, and dispatches dynamic runbooks via Discord.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg?style=flat-square&logo=python&logoColor=white)
![Backup](https://img.shields.io/badge/Backup-Restic-17A2B8.svg?style=flat-square&logo=linux&logoColor=white)
![Database](https://img.shields.io/badge/Database-DuckDB-FDED01.svg?style=flat-square&logo=duckduckgo&logoColor=black)
![Alerts](https://img.shields.io/badge/Alerts-Discord-5865F2.svg?style=flat-square&logo=discord&logoColor=white)

---

## 🎯 Overview

**Restore-Drill** transforms disaster recovery from a neglected, theoretical manual task into a fully automated CI/CD-style pipeline. Operating flawlessly in the background, it extracts live backups into an ephemeral sandbox, evaluates the state against strict Service Level Agreements (SLAs), logs telemetry to a local database, and pages on-call engineers strictly when failures occur.

---

## 🏗️ System Architecture

```text
[ Systemd Timer (2 AM Sunday) / Manual Trigger ]
        │
        ▼
[ Restic Adapter ] (Extracts snapshot to ephemeral sandbox)
        │
        ▼
[ Verification Engine ] (Checks critical paths & executes SQLite PRAGMA tests)
        │
        ▼
[ Scoring & Analytics ] (Calculates RTO/RPO, Grades A-F, logs to DuckDB)
        │
        ▼
[ Discord Webhook ] (Dispatches runbook UI alerts exclusively on SLA failure)

```

---

## 🛠️ Tech Stack

* **CLI & TUI Framework:** Python (`Typer`, `Rich`)
* **Backup Engine Interface:** Restic
* **Data Analytics & Storage:** DuckDB, SQLite
* **Notifications:** Discord Embed API (via native `urllib`)
* **Automation:** Systemd User Timers

---

## 📂 Project Structure

```text
restore-drill/
├── cli/
│   └── main.py              # Rich TUI dashboard & CLI entry point
├── drill/
│   ├── adapters/restic.py   # Restic backup extraction module
│   ├── analytics/storage.py # DuckDB historical ledger & anomaly detection
│   ├── notify/discord.py    # Zero-dependency Discord embed webhook
│   ├── scoring/grader.py    # RTO/RPO SLA grading logic
│   └── verify/checker.py    # Critical path checks & SQLite smoke testing
├── systemd/
│   ├── restore-drill.service
│   └── restore-drill.timer  # Background automation daemon configs
└── drill.example.yml        # Config for SLAs and critical path targets

```

---

## 🚀 Key Features

* **Automated RTO & RPO Analytics:** Precisely calculates Recovery Time Objective (extraction speed) and Recovery Point Objective (snapshot freshness) against configured SLA thresholds.
* **Database Smoke Testing:** Executes active `PRAGMA integrity_check` validations directly against restored SQLite databases to catch silent disk and write corruption.
* **File Drop Anomaly Detection:** Uses an embedded **DuckDB** analytics engine to track historical restore file counts, triggering warnings for accidental `--exclude` misconfigurations.
* **Dynamic Grading Engine:** Scores backup resilience from **A to F** based on missing files, broken databases, and RTO/RPO violations.
* **Discord Incident Runbooks:** If an incident occurs, it dispatches a rich dashboard-style alert containing exact CLI troubleshooting steps (e.g., `restic prune`, `PRAGMA journal_mode=WAL`).

---

## ⚙️ Custom Tweaks & Architecture Decisions

* **Alert Fatigue Prevention:** The system is explicitly configured (`alert_on: ["C", "D", "F"]`) to remain completely silent during successful Grade A runs, ensuring engineers are only interrupted for real, actionable incidents.
* **Zero-Dependency Notifier:** The Discord module relies purely on Python's native `urllib.request`. This keeps the tool lightweight and removes external `requests` library vulnerabilities.
* **Systemd Background Execution:** Packaged natively for Arch Linux/Ubuntu using user-level systemd timers (`systemctl --user`), enabling true "set-and-forget" infrastructure monitoring.

---

## 🛠️ System Tweaks & Troubleshooting

* **Discord API `403 Forbidden` Error:** Discord aggressively blocks automated requests originating from default Python web libraries. The `urllib` request dynamically injects a custom header (`User-Agent: RestoreDrill/2.0`) to bypass this and ensure payload delivery.
* **Restic Repository Not Found (`Fatal`):** If running manually, `restic` requires exact environment variables. Always ensure `RESTIC_PASSWORD` and `RESTIC_REPOSITORY` are exported in the terminal session before running `python -m cli.main run`.
* **Systemd Variable Isolation:** Systemd does not inherit shell environment variables. The Discord Webhook URL and Restic password must be hardcoded strictly within `~/.config/systemd/user/restore-drill.service`.

---

**Author:** [Braveen R](https://braveenr.linklee.in/)

---

## ✌️ Wrapping Up

You now have a fully functional, production-ready, zero-cost disaster recovery telemetry engine. Break your database, watch your systemd timer fire up, and see your live incident runbook instantly reflect in your Discord channel! 🚀 

See you in the terminal!
