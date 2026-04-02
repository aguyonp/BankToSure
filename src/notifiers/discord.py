import requests
from datetime import datetime
from loguru import logger

from ..core.base import BaseNotifier
from ..config import settings

class DiscordNotifier(BaseNotifier):
    """Notifier for Discord Webhooks."""

    def notify(self, message: str, is_error: bool = False):
        if not settings.discord_webhook_url:
            logger.warning("Discord webhook URL not configured, skipping notification")
            return

        color = 15158332 if is_error else 3066993
        title = "❌ Fortuneo Sync Error" if is_error else "✅ Fortuneo Sync Success"
        
        payload = {
            "embeds": [{
                "title": title,
                "description": message,
                "color": color,
                "timestamp": datetime.now().isoformat()
            }]
        }
        
        try:
            res = requests.post(settings.discord_webhook_url, json=payload)
            res.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
