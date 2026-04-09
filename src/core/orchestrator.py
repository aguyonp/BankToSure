import time
import schedule
from loguru import logger
from .base import BaseProvider, BaseDestination, BaseNotifier

class SyncOrchestrator:
    """Main application orchestrator."""

    def __init__(self, provider: BaseProvider, destination: BaseDestination, notifier: BaseNotifier, categorizer=None):
        self.provider = provider
        self.destination = destination
        self.notifier = notifier
        self.categorizer = categorizer

    def run(self, days: int, dry_run: bool = False):
        """Execute a single sync process."""
        mode_str = " [DRY RUN]" if dry_run else ""
        logger.info(f"--- Starting Synchronization Job{mode_str} ---")
        
        try:
            transactions = self.provider.fetch_transactions(days=days)
            
            if not transactions:
                msg = "No transactions found at source."
                logger.info(msg)
                if not dry_run:
                    self.notifier.notify(msg)
                return

            if dry_run:
                existing = self.destination.get_existing_fingerprints()
                success, errors, duplicates = 0, 0, 0
                for tx in transactions:
                    if (tx.date_iso, tx.description, tx.cents_abs) in existing:
                        duplicates += 1
                    else:
                        logger.info(f"[DRY-RUN] Would inject: {tx.description} ({tx.amount}€)")
                        success += 1
            else:
                success, errors, duplicates = self.destination.push_transactions(transactions)
            
            # Lancement de l'IA après le push
            cat_msg = ""
            if not dry_run and success > 0 and self.categorizer:
                categorized_count = self.categorizer.run()
                cat_msg = f"\n🤖 **{categorized_count}** transactions auto-catégorisées."

            result_msg = (
                f"Sync completed{mode_str}.\n"
                f"✅ **{success}** transactions processed.\n"
                f"⏭️ **{duplicates}** duplicates ignored.\n"
                f"⚠️ **{errors}** errors."
                f"{cat_msg}"
            )
            logger.info(f"Results: {success} handled, {duplicates} skipped, {errors} errors")
            
            if not dry_run:
                self.notifier.notify(result_msg)

        except Exception as e:
            error_msg = f"Process failed: {str(e)}"
            logger.exception(error_msg)
            if not dry_run:
                self.notifier.notify(error_msg, is_error=True)
        
        logger.info(f"--- Synchronization Job Finished{mode_str} ---")

    def run_scheduled(self, days: int):
        """Run in persistent mode, executing daily at configured time."""
        from ..config import settings
        logger.info(f"Entering Scheduled Mode (Daily at {settings.sync_time})")
        
        # Schedule the job
        schedule.every().day.at(settings.sync_time).do(self.run, days=days)
        
        # Run immediately on start to ensure data is fresh
        self.run(days=days)

        while True:
            schedule.run_pending()
            time.sleep(60)
