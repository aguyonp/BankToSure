import time
import requests
from typing import List, Set, Tuple
from loguru import logger

from ..core.base import BaseDestination
from ..core.models import Transaction
from ..config import settings

class SureDestination(BaseDestination):
    """Destination for Sure Finance Tool."""

    def __init__(self):
        self.headers = {
            "X-Api-Key": settings.sure_api_key,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def get_existing_fingerprints(self) -> Set[Tuple[str, str, int]]:
        logger.info("Scanning Sure account for existing transactions...")
        fingerprints = set()
        page = 1
        
        while True:
            params = {"account_id": settings.sure_account_id, "per_page": 100, "page": page}
            try:
                response = requests.get(f"{settings.sure_url}/api/v1/transactions", headers=self.headers, params=params)
                if response.status_code != 200: break
                
                data = response.json()
                txs = data.get('transactions', [])
                if not txs: break
                
                for tx in txs:
                    # Fingerprint uses absolute cents value
                    fingerprints.add((
                        tx.get('date'),
                        tx.get('name'),
                        abs(tx.get('amount_cents', 0))
                    ))
                
                pagination = data.get('pagination', {})
                if page >= pagination.get('total_pages', 1): break
                page += 1
            except Exception as e:
                logger.error(f"Failed to scan Sure history: {e}")
                break
                
        logger.info(f"Loaded {len(fingerprints)} fingerprints from Sure")
        return fingerprints

    def push_transactions(self, transactions: List[Transaction]) -> Tuple[int, int, int]:
        existing = self.get_existing_fingerprints()
        success, errors, duplicates = 0, 0, 0
        
        logger.info(f"Analyzing {len(transactions)} candidate transactions...")
        
        for tx in transactions:
            # Check for duplicate using absolute cents
            if (tx.date_iso, tx.description, tx.cents_abs) in existing:
                logger.trace(f"Skipping duplicate: {tx.description}")
                duplicates += 1
                continue

            # Sure Inversion: flip sign for API injection
            # Debit (neg) becomes positive expense, Credit (pos) becomes negative income
            payload = {
                "transaction": {
                    "account_id": settings.sure_account_id,
                    "date": tx.date_iso,
                    "description": tx.description,
                    "amount": -tx.amount
                }
            }

            try:
                res = requests.post(f"{settings.sure_url}/api/v1/transactions", headers=self.headers, json=payload)
                if res.status_code in [200, 201]:
                    logger.debug(f"Injected: {tx.description} ({tx.amount}€)")
                    success += 1
                    # Add to local set to avoid duplicates within same run
                    existing.add((tx.date_iso, tx.description, tx.cents_abs))
                else:
                    logger.error(f"API Error for {tx.description}: {res.status_code}")
                    errors += 1
            except Exception as e:
                logger.error(f"Connection error for {tx.description}: {e}")
                errors += 1
            
            time.sleep(0.05) # Small throttle

        return success, errors, duplicates
