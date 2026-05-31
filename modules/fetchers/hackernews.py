import asyncio
import logging
from datetime import datetime
from typing import List

import httpx

from .base import NewsItem

logger = logging.getLogger(__name__)

KEYWORDS = ['AI', 'LLM', 'OpenAI', 'Anthropic', 'layoff', 'hiring', 'GPT',
            'Claude', 'model', 'agent', 'Gemini', 'Mistral', 'inference']
HN_TOP = 'https://hacker-news.firebaseio.com/v0/topstories.json'
HN_ITEM = 'https://hacker-news.firebaseio.com/v0/item/{id}.json'


async def fetch() -> List[NewsItem]:
    return await asyncio.to_thread(_fetch_sync)


def _fetch_sync() -> List[NewsItem]:
    try:
        with httpx.Client(timeout=30) as client:
            ids: list = client.get(HN_TOP).json()[:200]
            items: List[NewsItem] = []
            for sid in ids:
                if len(items) >= 25:
                    break
                try:
                    story = client.get(HN_ITEM.format(id=sid)).json()
                    if not story or story.get('type') != 'story':
                        continue
                    title: str = story.get('title', '')
                    if not any(kw.lower() in title.lower() for kw in KEYWORDS):
                        continue
                    url = story.get('url') or f'https://news.ycombinator.com/item?id={sid}'
                    score = story.get('score', 0)
                    comments = story.get('descendants', 0)
                    items.append(NewsItem(
                        url=url,
                        title=title,
                        summary=f'HN: {score} points, {comments} comments',
                        source='HackerNews',
                        date=datetime.utcfromtimestamp(story.get('time', 0)),
                    ))
                except Exception:
                    continue
        logger.info('HackerNews: %d items', len(items))
        return items
    except Exception as e:
        logger.error('HackerNews fetch failed: %s', e)
        return []
