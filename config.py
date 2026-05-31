import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

TELEGRAM_BOT_TOKEN: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID: str = os.getenv('TELEGRAM_CHAT_ID', '')
ANTHROPIC_API_KEY: str = os.getenv('ANTHROPIC_API_KEY', '')

SCREENSHOTS_DIR = Path(os.getenv('SCREENSHOTS_DIR', 'screenshots'))
LOGS_DIR = Path(os.getenv('LOGS_DIR', 'logs'))

CLAUDE_MODEL = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-6')


def validate() -> None:
    missing = [
        v for v in ('TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'ANTHROPIC_API_KEY')
        if not os.getenv(v)
    ]
    if missing:
        raise EnvironmentError(
            f"Missing required env vars: {', '.join(missing)}\n"
            "Copy .env.example to .env and fill in the values."
        )
