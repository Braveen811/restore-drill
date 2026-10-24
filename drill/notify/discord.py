import json
import urllib.request
from typing import List

class DiscordNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_alert(self, drill_id: str, grade: str, score: int, anomaly_msg: str, penalties: List[str]):
        # Green for A/B, Orange for C, Red for D/F
        color = 65280 if grade in ["A", "B"] else (16753920 if grade == "C" else 16711680)
        
        description = f"**Recovery Score:** {score}/100\n\n"
        
        if anomaly_msg:
            description += f"⚠️ **Anomaly Detected:**\n> {anomaly_msg}\n\n"
            
        if penalties:
            description += "🚨 **Failures & Penalties:**\n"
            for p in penalties:
                description += f"- {p}\n"

        payload = {
            "username": "Restore Drill Engine",
            "embeds": [{
                "title": f"Backup Recovery Drill: Grade {grade}",
                "description": description,
                "color": color,
                "footer": {"text": f"Drill ID: {drill_id}"}
            }]
        }
        
        req = urllib.request.Request(
            self.webhook_url, 
            data=json.dumps(payload).encode(), 
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        try:
            urllib.request.urlopen(req)
            return True
        except Exception as e:
            return False
