from dataclasses import dataclass
from typing import Optional

@dataclass
class Subscription:
    url: str
    name: str
    last_update: float = 0.0
    auto_update: bool = False
    id: Optional[int] = None
