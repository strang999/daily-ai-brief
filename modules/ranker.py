import json
import logging
from typing import List

from anthropic import AsyncAnthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from modules.fetchers.base import NewsItem

logger = logging.getLogger(__name__)
_client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

_PROMPT = """You are a content curator for Anton Shumeiko — Ukrainian Senior AI Engineer creating TikTok/Threads content about the AI industry.

Rank these news items by "vibility" for a Ukrainian senior developer audience transitioning into AI engineering.
Score 1–10 based on:
- Direct AI/ML industry impact (model releases, moves by OpenAI/Anthropic/Google/Meta)
- Career relevance (hiring, layoffs, salary data, skill demand shifts)
- Controversy / surprise factor (things people will argue about)
- Urgency and freshness

Score LOW: generic press releases, puff pieces, academic papers with no business impact.

Return ONLY a valid JSON array (no markdown, no extra text):
[
  {{"index": 0, "score": 8.5, "reason": "one-line reason"}},
  ...
]

NEWS ITEMS:
{items_json}"""


async def rank_items(items: List[NewsItem]) -> List[NewsItem]:
    # Deduplicate by title prefix
    seen: set = set()
    unique: List[NewsItem] = []
    for item in items:
        key = item.title.lower()[:80]
        if key not in seen:
            seen.add(key)
            unique.append(item)

    candidates = unique[:40]
    payload = [
        {
            'index': i,
            'title': item.title,
            'summary': item.summary[:200],
            'source': item.source,
        }
        for i, item in enumerate(candidates)
    ]

    try:
        response = await _client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2048,
            messages=[{
                'role': 'user',
                'content': _PROMPT.format(items_json=json.dumps(payload, ensure_ascii=False)),
            }],
        )
        text = response.content[0].text.strip()
        if '```' in text:
            text = text.split('```')[1].lstrip('json').strip()

        rankings: list = json.loads(text)
        rankings.sort(key=lambda x: x.get('score', 0), reverse=True)

        result: List[NewsItem] = []
        for rank in rankings[:3]:
            idx = rank.get('index', 0)
            if 0 <= idx < len(candidates):
                item = candidates[idx]
                item.score = rank.get('score')
                result.append(item)
                logger.info('  #%d score=%.1f: %s', len(result), item.score or 0, item.title[:60])
        return result

    except Exception as e:
        logger.error('Ranking failed: %s — falling back to first 3 items', e)
        fallback = candidates[:3]
        for item in fallback:
            item.score = 5.0
        return fallback
