from dataclasses import dataclass
from datetime import date
from typing import Dict


@dataclass
class LastRide:
    date: date
    data: Dict[str, str]
    thumbnails: list[str]
