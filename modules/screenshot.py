import logging
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.async_api import async_playwright

from config import SCREENSHOTS_DIR

logger = logging.getLogger(__name__)

W, H = 1080, 1920
BORDER = 5
BORDER_COLOR = (18, 18, 18)

_POPUP_SELECTORS = [
    '[class*="cookie"]', '[class*="Cookie"]',
    '[class*="popup"]',  '[class*="Popup"]',
    '[class*="paywall"]','[id*="paywall"]',
    '[class*="overlay"]','.tp-backdrop', '.tp-modal',
    '[aria-label*="cookie"]', '#onetrust-banner-sdk',
]


async def take_screenshot(url: str, filename: str) -> str:
    output_path = str(SCREENSHOTS_DIR / filename)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu',
                  '--disable-extensions']
        )
        context = await browser.new_context(
            viewport={'width': W, 'height': H},
            user_agent=(
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
            ),
        )
        page = await context.new_page()

        try:
            await page.goto(url, wait_until='load', timeout=30000)
            await page.wait_for_timeout(2000)

            # Remove cookie banners / paywalls — each selector isolated so one
            # failure doesn't abort the rest, and we never trigger navigation
            for sel in _POPUP_SELECTORS:
                try:
                    for el in await page.query_selector_all(sel):
                        await el.evaluate('el => el.style.display = "none"')
                except Exception:
                    pass

            await page.screenshot(
                path=output_path,
                clip={'x': 0, 'y': 0, 'width': W, 'height': H},
            )
        except Exception as e:
            logger.warning('Primary screenshot failed for %s: %s', url, e)
            try:
                # Last-resort: whatever is currently visible
                await page.screenshot(path=output_path, full_page=False)
            except Exception as e2:
                logger.error('Fallback screenshot failed: %s', e2)
                raise
        finally:
            try:
                await browser.close()
            except Exception:
                pass

    _post_process(output_path)
    logger.info('Screenshot saved: %s', output_path)
    return output_path


def _post_process(path: str) -> None:
    with Image.open(path) as img:
        img = img.convert('RGB')
        w, h = img.size

        if (w, h) != (W, H):
            scale = W / w
            new_h = int(h * scale)
            img = img.resize((W, new_h), Image.LANCZOS)
            if img.height >= H:
                img = img.crop((0, 0, W, H))
            else:
                canvas = Image.new('RGB', (W, H), (255, 255, 255))
                canvas.paste(img, (0, 0))
                img = canvas

        draw = ImageDraw.Draw(img)
        for i in range(BORDER):
            draw.rectangle([i, i, W - 1 - i, H - 1 - i], outline=BORDER_COLOR)

        img.save(path, 'PNG', optimize=True)
