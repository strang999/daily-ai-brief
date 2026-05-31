import argparse
import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
from modules.fetchers import rss, hackernews, layoffs
from modules.ranker import rank_items
from modules.screenshot import take_screenshot
from modules.generator import generate_commentary
from modules.telegram_sender import send_brief


def setup_logging() -> None:
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(name)-24s %(levelname)s %(message)s',
        handlers=[
            logging.FileHandler(config.LOGS_DIR / 'app.log', encoding='utf-8'),
            logging.StreamHandler(),
        ],
    )


async def run_pipeline() -> None:
    log = logging.getLogger('pipeline')
    today = datetime.utcnow().strftime('%Y%m%d')
    config.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    log.info('=== Pipeline start ===')

    # 1. Fetch all sources in parallel
    fetch_results = await asyncio.gather(
        rss.fetch(),
        hackernews.fetch(),
        layoffs.fetch(),
        return_exceptions=True,
    )

    all_items = []
    for name, result in zip(('TechCrunch', 'HackerNews', 'layoffs.fyi'), fetch_results):
        if isinstance(result, Exception):
            log.error('%s fetcher raised: %s', name, result)
        else:
            log.info('%s: %d items', name, len(result))
            all_items.extend(result)

    if not all_items:
        log.error('No items from any source — aborting pipeline')
        return

    # 2. Rank via Claude
    log.info('Ranking %d items via Claude...', len(all_items))
    top3 = await rank_items(all_items)
    log.info('%d items selected', len(top3))

    # 3. Process each top item
    for n, item in enumerate(top3, 1):
        log.info('Item %d: %s', n, item.title[:70])

        # Screenshot + commentary in parallel (independent operations)
        results = await asyncio.gather(
            take_screenshot(item.url, f'{today}_{n}.png'),
            generate_commentary(item),
            return_exceptions=True,
        )

        screenshot_path: str | None = None
        if isinstance(results[0], Exception):
            log.error('Screenshot failed for item %d: %s', n, results[0])
        else:
            screenshot_path = results[0]

        if isinstance(results[1], Exception):
            log.error('Commentary failed for item %d: %s — skipping send', n, results[1])
            continue

        await send_brief(n, item, results[1], screenshot_path)

    log.info('=== Pipeline complete ===')


async def main() -> None:
    parser = argparse.ArgumentParser(description='Daily AI News Brief Bot')
    parser.add_argument('--now', action='store_true', help='Run pipeline immediately (testing)')
    args = parser.parse_args()

    setup_logging()
    config.validate()
    log = logging.getLogger('main')

    if args.now:
        await run_pipeline()
    else:
        scheduler = AsyncIOScheduler(timezone='UTC')
        scheduler.add_job(run_pipeline, 'cron', hour=7, minute=30)
        scheduler.start()
        log.info('Scheduler started — daily run at 07:30 UTC (09:30 Kyiv)')
        try:
            await asyncio.Event().wait()
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()
            log.info('Scheduler stopped')


if __name__ == '__main__':
    asyncio.run(main())
