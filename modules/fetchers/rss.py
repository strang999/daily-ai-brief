import asyncio
import logging
import re
from datetime import datetime
from typing import List

import feedparser

from .base import NewsItem

logger = logging.getLogger(__name__)
RSS_URL = 'https://techcrunch.com/category/artificial-intelligence/feed/'


async def fetch() -> List[NewsItem]:
    return await asyncio.to_thread(_fetch_sync)


def _fetch_sync() -> List[NewsItem]:
    try:
        feed = feedparser.parse(RSS_URL)
        items: List[NewsItem] = []
        for entry in feed.entries[:25]:
            pub_date = (
                datetime(*entry.published_parsed[:6])
                if getattr(entry, 'published_parsed', None)
                else datetime.utcnow()
            )
            summary = re.sub(r'<[^>]+>', '', entry.get('summary', ''))[:500]
            items.append(NewsItem(
                url=entry.link,
                title=entry.title,
                summary=summary,
                source='TechCrunch',
                date=pub_date,
            ))
        logger.info('TechCrunch RSS: %d items', len(items))
        return items
    except Exception as e:
        logger.error('TechCrunch RSS failed: %s', e)
        return []
