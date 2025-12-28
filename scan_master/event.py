from dataclasses import dataclass
from typing import Any, Optional, Tuple

@dataclass
class ScanEvent:
    coord: Tuple[int, int]
    value: float
    type: str
    tick: int
    meta: Optional[Any] = None

