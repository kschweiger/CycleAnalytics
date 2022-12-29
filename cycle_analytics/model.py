from dataclasses import dataclass
from datetime import date
from typing import Dict, Optional


@dataclass
class LastRide:
    date: date
    data: Dict[str, str]
    thumbnails: Optional[list[str]]
