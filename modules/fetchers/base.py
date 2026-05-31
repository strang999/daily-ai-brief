from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class NewsItem:
    url: str
    title: str
    summary: str
    source: str
    date: datetime
    score: Optional[float] = None
