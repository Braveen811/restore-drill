import sqlite3
from pathlib import Path

class VerificationEngine:
    def __init__(self, target_root: str):
        self.root = Path(target_root)

    def check_critical_paths(self, critical_paths: list[str]) -> dict:
        results = {}
        for rel_path in critical_paths:
            normalized = rel_path.lstrip("/")
            full_path = self.root / normalized
            exists = full_path.exists() and full_path.stat().st_size > 0
            results[rel_path] = exists
        return results

    def verify_sqlite_db(self, rel_path: str, table_name: str = "users") -> dict:
        db_path = self.root / rel_path.lstrip("/")
        if not db_path.exists():
            return {"status": "FAIL", "message": "Database file not found"}

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            integrity_result = cursor.fetchone()[0]

            cursor.execute(f"SELECT count(*) FROM {table_name};")
            count = cursor.fetchone()[0]
            conn.close()

            if integrity_result.lower() == "ok":
                return {"status": "PASS", "records": count, "message": "OK"}
            return {"status": "FAIL", "message": f"PRAGMA failed: {integrity_result}"}
        except Exception as e:
            return {"status": "FAIL", "message": str(e)}
