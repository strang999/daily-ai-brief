import logging
from datetime import datetime
from typing import List

from playwright.async_api import async_playwright

from .base import NewsItem

logger = logging.getLogger(__name__)


async def fetch() -> List[NewsItem]:
    """
    layoffs.fyi embeds an Airtable iframe. We launch a headless browser,
    wait for the grid to hydrate, and scrape table rows from any frame.
    Returns empty list gracefully if the site structure changes.
    """
    items: List[NewsItem] = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
            )
            page = await browser.new_page(
                user_agent=(
                    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
            )
            try:
                await page.goto('https://layoffs.fyi/', wait_until='networkidle', timeout=45000)
                await page.wait_for_timeout(5000)

                # Try main page + all iframes
                all_frames = [page, *page.frames]
                for frame in all_frames:
                    try:
                        rows = await frame.query_selector_all('tr')
                        if len(rows) < 2:
                            continue
                        for row in rows[1:16]:
                            try:
                                tds = await row.query_selector_all('td')
                                if not tds:
                                    continue
                                texts = [await td.inner_text() for td in tds[:6]]
                                texts = [t.strip() for t in texts if t.strip()]
                                if len(texts) < 2:
                                    continue
                                company = texts[0]
                                count = texts[1] if len(texts) > 1 else '?'
                                items.append(NewsItem(
                                    url='https://layoffs.fyi/',
                                    title=f'Layoff: {company} cuts {count} employees',
                                    summary=' | '.join(texts),
                                    source='layoffs.fyi',
                                    date=datetime.utcnow(),
                                ))
                            except Exception:
                                continue
                        if items:
                            break
                    except Exception:
                        continue
            except Exception as e:
                logger.warning('layoffs.fyi page error: %s', e)
            finally:
                await browser.close()
    except Exception as e:
        logger.error('layoffs.fyi fetch failed: %s', e)

    logger.info('layoffs.fyi: %d items', len(items))
    return items
