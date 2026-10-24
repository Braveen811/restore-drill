import os
import json
import time
import shutil
import subprocess
from pathlib import Path

class ResticAdapter:
    def __init__(self, repository: str, password: str, destination: str):
        self.repository = str(Path(repository).resolve())
        self.password = password
        self.destination = Path(destination)
        self.env = {
            **os.environ,
            "RESTIC_PASSWORD": self.password,
            "RESTIC_REPOSITORY": self.repository,
        }

    def get_latest_snapshot(self) -> dict:
        cmd = ["restic", "snapshots", "--json", "--latest", "1"]
        result = subprocess.run(cmd, env=self.env, capture_output=True, text=True, check=True)
        snapshots = json.loads(result.stdout)
        if not snapshots:
            raise RuntimeError("No snapshots found in repository.")
        return snapshots[0]

    def execute_restore(self, snapshot_id: str = "latest") -> dict:
        if self.destination.exists():
            shutil.rmtree(self.destination)
        self.destination.mkdir(parents=True, exist_ok=True)

        start_time = time.perf_counter()
        cmd = ["restic", "restore", snapshot_id, "--target", str(self.destination)]
        
        proc = subprocess.run(cmd, env=self.env, capture_output=True, text=True)
        duration_seconds = time.perf_counter() - start_time

        if proc.returncode != 0:
            raise RuntimeError(f"Restic restore failed: {proc.stderr}")

        total_files = sum(1 for p in self.destination.rglob('*') if p.is_file())

        return {
            "duration_seconds": round(duration_seconds, 2),
            "restored_files_count": total_files,
            "target_path": str(self.destination)
        }
