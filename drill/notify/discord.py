import json
import urllib.request
from typing import List
from datetime import datetime, timezone

class DiscordNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_alert(self, drill_id: str, grade: str, score: int, anomaly_msg: str, penalties: List[str]):
        # Dynamic Styling based on Grade
        if grade in ["A", "B"]:
            color = 5763719 # Vibrant Green
            status_icon = "✅"
            thumb_url = "https://cdn-icons-png.flaticon.com/512/1904/1904118.png" # Shield icon
        elif grade == "C":
            color = 16753920 # Warning Orange
            status_icon = "⚠️"
            thumb_url = "https://cdn-icons-png.flaticon.com/512/4201/4201973.png" # Warning icon
        else:
            color = 15548997 # Critical Red
            status_icon = "🚨"
            thumb_url = "https://cdn-icons-png.flaticon.com/512/1055/1055273.png" # Siren icon

        fields = [
            {
                "name": f"{status_icon} Resilience Score",
                "value": f"**{score}/100** (Grade {grade})",
                "inline": True
            },
            {
                "name": "🆔 Execution ID",
                "value": f"`{drill_id}`",
                "inline": True
            }
        ]

        # Faults Section (Formatted with Markdown Blockquotes)
        faults_text = ""
        if anomaly_msg:
            faults_text += f"**Anomaly:** {anomaly_msg}\n"
        for p in penalties:
            faults_text += f"• {p}\n"
        
        if faults_text:
            fields.append({
                "name": "🔥 Detected Incidents",
                "value": f">>> {faults_text}",
                "inline": False
            })
        else:
            fields.append({
                "name": "✨ System Status",
                "value": ">>> All recovery metrics nominal. Backup is healthy.",
                "inline": False
            })

        # ==========================================
        # ENTERPRISE RUNBOOK (Step-by-Step Solutions)
        # ==========================================
        p_str = str(penalties).lower()
        
        if "missing" in p_str or (anomaly_msg and "dropped" in anomaly_msg.lower()):
            fields.append({
                "name": "🛠️ Runbook: Missing Data / File Drops",
                "value": "**Step 1:** Run `restic ls latest` to verify if the missing files physically exist in the snapshot.\n**Step 2:** Check your backup cron job for rogue `--exclude` flags or a misconfigured `.gitignore`.\n**Step 3:** Ensure the system user running the backup has `read` permissions for the missing directories.",
                "inline": False
            })
            
        if "smoke test" in p_str:
            fields.append({
                "name": "🛠️ Runbook: Database Corruption",
                "value": "**Step 1:** Ensure SQLite isn't being actively written to during the backup. Enable WAL mode via `PRAGMA journal_mode=WAL;` on your production app.\n**Step 2:** Alternatively, implement a pre-backup script to run `sqlite3 db.sqlite \".backup backup.sq3\"` and backup *that* safe file instead of the live DB.\n**Step 3:** Verify the host disk doesn't have silent hardware corruption (`dmesg` or `fsck`).",
                "inline": False
            })
            
        if "rto" in p_str:
            fields.append({
                "name": "🛠️ Runbook: Slow Recovery (RTO Exceeded)",
                "value": "**Step 1:** Check if the backup repository is highly fragmented. Run `restic prune` to optimize and repack the data.\n**Step 2:** Monitor network bandwidth between the host and the backup storage location.\n**Step 3:** Allocate more CPU/RAM to the restore environment to speed up decryption.",
                "inline": False
            })
            
        if "rpo" in p_str:
            fields.append({
                "name": "🛠️ Runbook: Stale Snapshot (RPO Exceeded)",
                "value": "**Step 1:** Check the production backup server logs (`journalctl -u restic-backup`) for execution failures.\n**Step 2:** Verify the backup destination disk isn't 100% full (`df -h`).\n**Step 3:** Check for stuck lock files (`restic unlock`) that might be preventing new snapshots from saving.",
                "inline": False
            })

        # Assemble the final rich embed payload
        payload = {
            "username": "SRE Recovery Engine",
            "avatar_url": "https://cdn-icons-png.flaticon.com/512/8666/8666579.png",
            "embeds": [{
                "author": {
                    "name": "Automated Disaster Recovery Monitor",
                    "icon_url": "https://cdn-icons-png.flaticon.com/512/3233/3233483.png"
                },
                "title": f"System Drill Report: Grade {grade}",
                "color": color,
                "thumbnail": {"url": thumb_url},
                "fields": fields,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "footer": {
                    "text": "restore-drill • DuckDB Analytics",
                    "icon_url": "https://cdn-icons-png.flaticon.com/512/2905/2905206.png"
                }
            }]
        }
        
        req = urllib.request.Request(
            self.webhook_url, 
            data=json.dumps(payload).encode(), 
            headers={'Content-Type': 'application/json', 'User-Agent': 'RestoreDrill/2.0'},
            method='POST'
        )
        try:
            urllib.request.urlopen(req)
            return True
        except Exception as e:
            print(f"Discord API Error: {e}")
            return False
