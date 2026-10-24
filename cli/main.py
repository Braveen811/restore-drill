import typer
import yaml
import os
from pathlib import Path
from datetime import datetime, timezone
from rich.console import Console, Group
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from drill.adapters.restic import ResticAdapter
from drill.verify.checker import VerificationEngine
from drill.scoring.grader import RecoveryGrader
from drill.analytics.storage import DrillAnalytics
from drill.notify.discord import DiscordNotifier

app = typer.Typer(help="restore-drill: Automated Backup Recovery & Integrity Testing Engine")
console = Console()

def load_config(config_path: str = "drill.yml") -> dict:
    path = Path(config_path)
    if not path.exists():
        console.print(f"[bold red]Config file '{config_path}' not found![/bold red]")
        raise typer.Exit(1)
    with open(path) as f:
        return yaml.safe_load(f)

@app.command()
def run(config: str = "drill.yml"):
    """Execute an automated recovery drill, grade the results, and log to DuckDB."""
    cfg = load_config(config)
    repo = cfg["backup"]["repository"]
    pwd_env = cfg["backup"].get("password_env", "RESTIC_PASSWORD")
    password = os.environ.get(pwd_env, "testpass123")
    dest = cfg["restore"]["destination"]

    console.print(Panel("[bold cyan]RECOVERY DRILL CONTROL PLANE[/bold cyan]\n[dim]Restoring snapshot to sandbox & calculating resilience score...[/dim]", border_style="cyan"))

    # 1. Extraction
    adapter = ResticAdapter(repo, password, dest)
    snap = adapter.get_latest_snapshot()
    snap_time = datetime.fromisoformat(snap["time"].replace("Z", "+00:00"))
    age_hours = round((datetime.now(timezone.utc) - snap_time).total_seconds() / 3600, 2)
    restore_res = adapter.execute_restore(snap["id"])

    # 2. Verification
    verifier = VerificationEngine(dest)
    paths_status = verifier.check_critical_paths(cfg["checks"]["critical_paths"])
    all_paths_passed = all(paths_status.values())

    smoke_status = "SKIPPED"
    if cfg["checks"].get("sqlite_smoke_test", {}).get("enabled", False):
        db_chk = verifier.verify_sqlite_db(
            cfg["checks"]["sqlite_smoke_test"]["path"],
            cfg["checks"]["sqlite_smoke_test"].get("table", "users")
        )
        smoke_status = db_chk["status"]

    # 3. Grading
    grader = RecoveryGrader(
        max_rto_seconds=cfg["scoring"].get("max_restore_seconds", 60),
        max_rpo_hours=cfg["scoring"].get("max_snapshot_age_hours", 24)
    )
    grade_data = grader.calculate_grade(
        rto_seconds=restore_res["duration_seconds"],
        rpo_hours=age_hours,
        critical_checks=paths_status,
        smoke_status=smoke_status
    )

    # 4. Analytics
    analytics = DrillAnalytics()
    anomaly = analytics.detect_file_drop_anomaly(restore_res["restored_files_count"])
    drill_id = analytics.record_drill(
        snapshot_id=snap["short_id"],
        age_hours=age_hours,
        duration_sec=restore_res["duration_seconds"],
        file_count=restore_res["restored_files_count"],
        paths_passed=all_paths_passed,
        smoke_status=smoke_status,
        score=grade_data["score"],
        grade=grade_data["grade"]
    )

    # ==========================================
    # 5. TERMINAL UI DASHBOARD RENDERING
    # ==========================================
    color_map = {"A": "green", "B": "cyan", "C": "yellow", "D": "red", "F": "bold red"}
    grade_color = color_map.get(grade_data["grade"], "white")

    # UI Component: Core Metrics
    metrics_grid = Table.grid(padding=(0, 2))
    metrics_grid.add_column(style="bold cyan", justify="right")
    metrics_grid.add_column()
    metrics_grid.add_row("Drill ID:", drill_id)
    metrics_grid.add_row("Target Snapshot:", f"{snap['short_id']} ({age_hours}h old)")
    metrics_grid.add_row("Restore Time (RTO):", f"{restore_res['duration_seconds']}s")
    metrics_grid.add_row("Restored Files:", str(restore_res['restored_files_count']))
    metrics_grid.add_row("Recovery Grade:", f"[{grade_color}]{grade_data['grade']} ({grade_data['score']}/100)[/{grade_color}]")
    
    console.print()
    console.print(Panel(metrics_grid, title="[bold white]Core Execution Metrics[/bold white]", border_style=grade_color))

    # UI Component: Path Verification Table
    path_table = Table(show_header=True, header_style="bold magenta", expand=True)
    path_table.add_column("Critical Path Monitored", style="dim")
    path_table.add_column("Status", justify="right")
    for p, ok in paths_status.items():
        status_text = "[bold green]✔ FOUND[/]" if ok else "[bold red]✖ MISSING[/]"
        path_table.add_row(p, status_text)
    
    console.print(path_table)

    # UI Component: Alerts & Penalties Panel
    alerts = []
    if smoke_status != "SKIPPED":
        smk_color = "green" if smoke_status == "PASS" else "red"
        icon = "✔" if smoke_status == "PASS" else "✖"
        alerts.append(Text.from_markup(f"[{smk_color}]{icon} Database Smoke Test: {smoke_status}[/]"))

    if anomaly["is_anomaly"]:
        alerts.append(Text.from_markup(f"[bold yellow]⚠️ ANOMALY:[/bold yellow] {anomaly['message']}"))
    
    for p in grade_data["penalties"]:
        alerts.append(Text.from_markup(f"[red]🚨 PENALTY:[/] {p}"))

    if alerts:
        console.print(Panel(Group(*alerts), title="[bold red]System Diagnostics & Faults[/]", border_style="red"))

    # --- Notifications ---
    webhook_url = os.environ.get(cfg.get("notifications", {}).get("discord_webhook_env", ""))
    alert_thresholds = cfg.get("notifications", {}).get("alert_on", ["C", "D", "F"])
    
    if webhook_url and grade_data["grade"] in alert_thresholds:
        console.print("\n[dim]Dispatching Discord alert...[/dim]")
        notifier = DiscordNotifier(webhook_url)
        success = notifier.send_alert(drill_id, grade_data["grade"], grade_data["score"], anomaly["message"] if anomaly["is_anomaly"] else "", grade_data["penalties"])
        if success:
            console.print("[bold green]✔ Alert sent to Discord[/bold green]")
        else:
            console.print("[bold red]✖ Failed to send Discord alert[/bold red]")

@app.command()
def report(limit: int = 5):
    """View historical recovery drills and grades recorded in DuckDB."""
    analytics = DrillAnalytics()
    rows = analytics.get_summary_report(limit)

    table = Table(title=f"Historical Recovery Drills (DuckDB) - Last {limit}", border_style="cyan")
    table.add_column("Snapshot", style="yellow")
    table.add_column("Grade", style="bold")
    table.add_column("Score", style="cyan")
    table.add_column("RTO (s)", style="green")
    table.add_column("Files", style="magenta")
    table.add_column("Timestamp", style="dim")

    color_map = {"A": "green", "B": "cyan", "C": "yellow", "D": "red", "F": "bold red"}

    for r in rows:
        g = r[1]
        col = color_map.get(g, "white")
        table.add_row(r[0], f"[{col}]{g}[/{col}]", str(r[2]), f"{r[3]}s", str(r[4]), str(r[5])[:19])

    console.print(table)

if __name__ == "__main__":
    app()
