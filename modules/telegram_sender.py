import asyncio
import logging

from telegram import Bot
from telegram.error import TelegramError

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from modules.fetchers.base import NewsItem

logger = logging.getLogger(__name__)

# Telegram limits: photo caption 1024 chars, text message 4096 chars
_CAPTION_LIMIT = 1024
_TEXT_LIMIT = 4096

_BRIEF_TEMPLATE = """\
🔥 НОВИНА #{n} | Vibility: {score}/10

📰 {title}
🔗 {url}

━━━━━━━━━━━━━━━━

🎬 HOOK (для першої секунди відео):
"{hook}"

💭 TAKE (30-45 сек):
{take}

❓ END QUESTION:
{end_question}

━━━━━━━━━━━━━━━━

📱 THREADS VERSION (готовий до копіпасту):
{threads_version}"""


async def send_brief(
    n: int,
    item: NewsItem,
    commentary: dict,
    screenshot_path: str | None,
) -> None:
    score_str = f'{item.score:.1f}' if item.score is not None else '?'
    full_text = _BRIEF_TEMPLATE.format(
        n=n,
        score=score_str,
        title=item.title,
        url=item.url,
        hook=commentary.get('hook', ''),
        take=commentary.get('take', ''),
        end_question=commentary.get('end_question', ''),
        threads_version=commentary.get('threads_version', ''),
    )

    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    for attempt in range(3):
        try:
            if screenshot_path:
                # Telegram caption limit is 1024 chars.
                # If full text fits, send everything in one shot.
                # Otherwise: photo with header, then full text as a follow-up.
                if len(full_text) <= _CAPTION_LIMIT:
                    with open(screenshot_path, 'rb') as photo:
                        await bot.send_photo(
                            chat_id=TELEGRAM_CHAT_ID,
                            photo=photo,
                            caption=full_text,
                        )
                else:
                    header = f'🔥 НОВИНА #{n} | Vibility: {score_str}/10\n📰 {item.title}'
                    with open(screenshot_path, 'rb') as photo:
                        await bot.send_photo(
                            chat_id=TELEGRAM_CHAT_ID,
                            photo=photo,
                            caption=header[:_CAPTION_LIMIT],
                        )
                    await bot.send_message(
                        chat_id=TELEGRAM_CHAT_ID,
                        text=full_text[:_TEXT_LIMIT],
                    )
            else:
                await bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text=full_text[:_TEXT_LIMIT],
                )

            logger.info('Brief #%d sent', n)
            return

        except TelegramError as e:
            wait = 2 ** attempt
            logger.warning('Send attempt %d/3 failed: %s. Retry in %ds', attempt + 1, e, wait)
            if attempt < 2:
                await asyncio.sleep(wait)

    logger.error('Failed to send brief #%d after 3 attempts', n)
