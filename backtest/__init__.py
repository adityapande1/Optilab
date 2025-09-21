from dataclasses import dataclass
from strategy import Action
import pandas as pd
import hashlib

@dataclass
class Order:
    action: Action
    timestamp: pd.Timestamp
    status: str = "pending"   # e.g. pending, filled, cancelled, rejected

    def __post_init__(self):
        assert isinstance(self.action, Action), "action must be an Action instance"
        assert self.action.num_lots == 1, "Order must be created with exactly 1 lot"
        assert isinstance(self.timestamp, pd.Timestamp), "timestamp must be a pandas Timestamp"
        assert self.status in ("pending", "filled", "cancelled", "rejected"), "invalid status"

        # Build unique hash
        order_key = f"{self.action.key}__{self.timestamp}"
        self.hash = self._generate_positive_hash(order_key)

    def _generate_positive_hash(self, s: str) -> int:
        h = hashlib.sha256(s.encode("utf-8")).digest()
        # Take first 8 bytes (64 bits) and make it an integer
        return int.from_bytes(h[:8], "big", signed=False)

    def update_status(self, new_status: str):
        assert new_status in ("pending", "filled", "cancelled", "rejected"), "invalid status"
        self.status = new_status
