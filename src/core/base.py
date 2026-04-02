from abc import ABC, abstractmethod
from typing import List, Set, Tuple
from .models import Transaction

class BaseProvider(ABC):
    """Abstract base for transaction sources."""
    @abstractmethod
    def fetch_transactions(self, days: int) -> List[Transaction]:
        """Fetch transactions from the source."""
        pass

class BaseDestination(ABC):
    """Abstract base for transaction targets."""
    @abstractmethod
    def get_existing_fingerprints(self) -> Set[Tuple[str, str, int]]:
        """Fetch existing transaction fingerprints to avoid duplicates."""
        pass

    @abstractmethod
    def push_transactions(self, transactions: List[Transaction]) -> Tuple[int, int, int]:
        """
        Push new transactions to the destination.
        Returns: (success_count, error_count, duplicate_count)
        """
        pass

class BaseNotifier(ABC):
    """Abstract base for alert systems."""
    @abstractmethod
    def notify(self, message: str, is_error: bool = False):
        """Send a notification."""
        pass
