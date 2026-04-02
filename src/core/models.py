from pydantic import BaseModel
from datetime import date
from typing import Optional

class Transaction(BaseModel):
    """Universal transaction model."""
    date: date
    description: str
    amount: float
    
    @property
    def cents_abs(self) -> int:
        """Absolute value in cents for deduplication."""
        return int(round(abs(self.amount) * 100))

    @property
    def date_iso(self) -> str:
        """ISO format string."""
        return self.date.strftime("%Y-%m-%d")
