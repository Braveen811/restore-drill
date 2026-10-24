import duckdb
from pathlib import Path
from datetime import datetime, timezone

class DrillAnalytics:
    def __init__(self, db_path: str = "drills.duckdb"):
        self.db_path = str(Path(db_path).resolve())
        self._init_db()

    def _init_db(self):
        conn = duckdb.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS drill_history (
                id VARCHAR,
                timestamp TIMESTAMP,
                snapshot_id VARCHAR,
                snapshot_age_hours DOUBLE,
                restore_duration_sec DOUBLE,
                restored_files_count BIGINT,
                critical_paths_passed BOOLEAN,
                smoke_test_status VARCHAR,
                score INTEGER,
                grade VARCHAR
            )
        """)
        conn.close()

    def detect_file_drop_anomaly(self, current_file_count: int) -> dict:
        conn = duckdb.connect(self.db_path)
        res = conn.execute("""
            SELECT AVG(restored_files_count)
            FROM (
                SELECT restored_files_count
                FROM drill_history
                ORDER BY timestamp DESC
                LIMIT 5
            ) recent
        """).fetchone()
        conn.close()

        if res and res[0] is not None:
            avg_count = res[0]
            if avg_count > 0 and current_file_count < (avg_count * 0.8):
                drop_pct = round(((avg_count - current_file_count) / avg_count) * 100, 1)
                return {
                    "is_anomaly": True,
                    "message": f"Restored file count dropped {drop_pct}% vs recent average ({current_file_count} vs {avg_count:.1f})"
                }
        return {"is_anomaly": False, "message": "File count consistent"}

    def record_drill(self, 
                     snapshot_id: str, 
                     age_hours: float, 
                     duration_sec: float, 
                     file_count: int, 
                     paths_passed: bool, 
                     smoke_status: str, 
                     score: int, 
                     grade: str) -> str:
        conn = duckdb.connect(self.db_path)
        drill_id = f"drill_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        conn.execute("""
            INSERT INTO drill_history VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            drill_id,
            datetime.now(timezone.utc),
            snapshot_id,
            age_hours,
            duration_sec,
            file_count,
            paths_passed,
            smoke_status,
            score,
            grade
        ))
        conn.close()
        return drill_id

    def get_summary_report(self, limit: int = 5):
        conn = duckdb.connect(self.db_path)
        rows = conn.execute(f"""
            SELECT snapshot_id, grade, score, restore_duration_sec, restored_files_count, timestamp
            FROM drill_history 
            ORDER BY timestamp DESC LIMIT {limit}
        """).fetchall()
        conn.close()
        return rows
