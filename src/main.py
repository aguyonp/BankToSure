import sys
import argparse
from loguru import logger

from .providers.fortuneo import FortuneoProvider
from .destinations.sure import SureDestination
from .notifiers.discord import DiscordNotifier
from .categorizers.groq_categorizer import GroqCategorizer
from .core.orchestrator import SyncOrchestrator
from .config import settings

def main():
    # CLI Arguments
    parser = argparse.ArgumentParser(description="BankToSure: Fortuneo to Sure Synchronization Tool")
    parser.add_argument("--days", type=int, default=settings.fetch_days, help="Number of days to fetch")
    parser.add_argument("--dry-run", action="store_true", help="Simulate sync without pushing to Sure")
    parser.add_argument("--schedule", action="store_true", help="Run in persistent mode")
    parser.add_argument("--time", type=str, default=settings.sync_time, help="Schedule time (HH:MM)")
    args = parser.parse_args()

    # Update settings with CLI override if provided
    settings.sync_time = args.time

    # Redaction filter for sensitive values
    def redact_secrets(record):
        secrets = [
            settings.fortuneo_pwd.get_secret_value(),
            settings.sure_api_key.get_secret_value(),
        ]
        if settings.discord_webhook_url:
            secrets.append(settings.discord_webhook_url.get_secret_value())
        if settings.groq_api_key:
            secrets.append(settings.groq_api_key.get_secret_value())
            
        for secret in secrets:
            if secret and len(secret) > 5:
                record["message"] = record["message"].replace(secret, "********")
        return True

    # Configure Loguru
    logger.remove()
    logger.add(
        sys.stderr, 
        level="INFO", 
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
        backtrace=False,
        diagnose=False,
        filter=redact_secrets
    )
    logger.add(
        "logs/app.log", 
        rotation="1 week", 
        level="DEBUG",
        backtrace=True,
        diagnose=False,
        filter=redact_secrets
    )

    # Initialize components
    provider = FortuneoProvider()
    destination = SureDestination()
    notifier = DiscordNotifier()
    categorizer = GroqCategorizer() if settings.groq_api_key else None

    # Run orchestration
    orchestrator = SyncOrchestrator(
        provider=provider,
        destination=destination,
        notifier=notifier,
        categorizer=categorizer
    )
    
    if args.schedule:
        orchestrator.run_scheduled(days=args.days)
    else:
        orchestrator.run(days=args.days, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
