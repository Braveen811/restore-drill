import os
import yaml
from datetime import datetime, timezone
from rich.console import Console
from rich.table import Table

from drill.adapters.restic import ResticAdapter
from drill.verify.checker import VerificationEngine

console = Console()

with open("drill.yml") as f:
    cfg = yaml.safe_load(f)

repo = cfg["backup"]["repository"]
password = os.environ.get(cfg["backup"]["password_env"], "testpass123")
dest = cfg["restore"]["destination"]

console.print("[bold cyan]=== EXECUTING RECOVERY DRILL ===[/bold cyan]")

adapter = ResticAdapter(repo, password, dest)
snap = adapter.get_latest_snapshot()
snap_time = datetime.fromisoformat(snap["time"].replace("Z", "+00:00"))
age_hours = round((datetime.now(timezone.utc) - snap_time).total_seconds() / 3600, 2)

console.print(f"Snapshot ID: [yellow]{snap['short_id']}[/yellow]")
console.print(f"Snapshot Age: [yellow]{age_hours}h[/yellow]")

res = adapter.execute_restore(snap["id"])
console.print(f"Restore Duration: [green]{res['duration_seconds']}s[/green]")
console.print(f"Restored Files: [green]{res['restored_files_count']}[/green]")

verifier = VerificationEngine(dest)
paths = verifier.check_critical_paths(cfg["checks"]["critical_paths"])

table = Table(title="Path Verification")
table.add_column("Path", style="cyan")
table.add_column("Status", style="bold")
for p, ok in paths.items():
    table.add_row(p, "[green]PASS[/green]" if ok else "[red]FAIL[/red]")
console.print(table)

if cfg["checks"]["sqlite_smoke_test"]["enabled"]:
    db_res = verifier.verify_sqlite_db(
        cfg["checks"]["sqlite_smoke_test"]["path"],
        cfg["checks"]["sqlite_smoke_test"].get("table", "users")
    )
    col = "green" if db_res["status"] == "PASS" else "red"
    console.print(f"SQLite PRAGMA Check: [{col}]{db_res['status']}[/{col}] (Rows: {db_res.get('records', 0)})")
