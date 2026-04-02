import os
import csv
import zipfile
from typing import List
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from loguru import logger

from ..core.base import BaseProvider
from ..core.models import Transaction
from ..config import settings

class FortuneoProvider(BaseProvider):
    """Provider for Fortuneo Bank."""

    def fetch_transactions(self, days: int) -> List[Transaction]:
        logger.info(f"Starting Fortuneo extraction for the last {days} days")
        os.makedirs(settings.download_dir, exist_ok=True)
        os.makedirs("logs", exist_ok=True)

        start_date = (datetime.now() - timedelta(days=days)).strftime("%d/%m/%Y")
        zip_path = os.path.join(settings.download_dir, "export.zip")

        browser = None
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(accept_downloads=True)
                page = context.new_page()
                page.set_default_timeout(60000) # 60s timeout for slow emulated environments

                logger.debug("Connecting to Fortuneo...")
                page.goto("https://mabanque.fortuneo.fr/")

                # Wait for cookies/consent
                try:
                    page.get_by_role("listitem", name="Accepter", exact=True).click(timeout=10000)
                except Exception:
                    pass

                page.get_by_role("textbox", name="Identifiant").fill(settings.fortuneo_id)
                page.get_by_role("textbox", name="Mot de passe").fill(settings.fortuneo_pwd.get_secret_value())
                page.get_by_role("button", name="Connexion").click()
                page.wait_for_load_state("networkidle")

                # Handle interface choice
                try:
                    btn = page.get_by_role("button", name="Continuer avec l’espace client actuel")
                    if btn.is_visible(timeout=5000):
                        logger.debug("Selecting legacy interface")
                        btn.click()
                        page.wait_for_load_state("networkidle")
                except Exception:
                    pass

                # Locate the frame and wait for it
                iframe_locator = page.locator("iframe[name='iframe_centrale']")
                iframe = iframe_locator.content_frame

                logger.debug("Navigating to history...")
                # Specific wait for the link to be available in the frame
                iframe.get_by_role("link", name="N°010166419940 Compte courant").click()
                iframe.get_by_role("link", name="Télécharger un historique").click()

                iframe.get_by_role("combobox").select_option("csv")
                iframe.locator("input.hasDatepicker").first.fill(start_date)
                iframe.get_by_role("link", name="Télécharger", exact=True).click()

                with page.expect_download() as download_info:
                    iframe.get_by_role("link", name="Lancer le téléchargement").click()

                download_info.value.save_as(zip_path)
                browser.close()

            return self._parse_zip(zip_path)

        except Exception as e:
            logger.error(f"Fortuneo extraction failed: {e}")
            if browser:
                # Fallback screenshot for debugging
                try:
                    # We can't easily take a screenshot here because the context is closed in 'with'
                    # but the log is already detailed.
                    pass
                except: pass
            raise

    def _parse_zip(self, zip_path: str) -> List[Transaction]:
        """Extract and parse CSV from downloaded ZIP."""
        logger.debug("Extracting ZIP archive...")
        transactions = []

        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(settings.download_dir)
            csv_name = next((n for n in z.namelist() if n.lower().endswith('.csv')), None)

        if not csv_name:
            raise FileNotFoundError("No CSV found in Fortuneo export")

        csv_path = os.path.join(settings.download_dir, csv_name)

        with open(csv_path, 'r', encoding='iso-8859-1') as f:
            reader = csv.reader(f, delimiter=';')
            next(reader, None) # Skip header

            for row in reader:
                if len(row) < 4: continue

                date_str, name = row[0].strip(), row[2].strip()
                debit = float(row[3].strip().replace(' ', '').replace(',', '.')) if row[3].strip() else 0.0
                credit = float(row[4].strip().replace(' ', '').replace(',', '.')) if len(row) > 4 and row[4].strip() else 0.0

                amount = credit if credit != 0 else debit
                if amount == 0: continue

                transactions.append(Transaction(
                    date=datetime.strptime(date_str, "%d/%m/%Y").date(),
                    description=name,
                    amount=amount
                ))

        os.remove(zip_path)
        os.remove(csv_path)
        return transactions
