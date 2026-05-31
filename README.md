# Daily AI News Brief Bot

Scrapes AI industry news daily, ranks top 3 by virality, takes article screenshots, generates Ukrainian-language hot takes in Anton's voice, and sends to Telegram. Runs at **07:30 UTC (09:30 Kyiv)** every day.

---

## Required environment variables

Create a `.env` file in this folder with:

```
TELEGRAM_BOT_TOKEN=   # from @BotFather
TELEGRAM_CHAT_ID=     # from @userinfobot (numeric, e.g. 123456789)
ANTHROPIC_API_KEY=    # from console.anthropic.com
```

Optional overrides (defaults shown):

```
CLAUDE_MODEL=claude-sonnet-4-6
SCREENSHOTS_DIR=screenshots
LOGS_DIR=logs
```

---

## Setup step by step

### 1. Get a Telegram bot token

1. Open Telegram, search for **@BotFather**
2. Send `/newbot`
3. Give it a name (e.g. "AI Brief") and a username (e.g. `my_ai_brief_bot`)
4. BotFather replies with a token like `7123456789:AAH...` — paste that as `TELEGRAM_BOT_TOKEN`

### 2. Get your Telegram chat_id

1. Message **@userinfobot** on Telegram
2. It replies with your numeric ID (e.g. `123456789`) — paste that as `TELEGRAM_CHAT_ID`
3. Start a conversation with your new bot first (send it `/start`) so it can message you

### 3. Get an Anthropic API key

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Settings → API Keys → Create Key
3. Paste as `ANTHROPIC_API_KEY`

### 4. Hetzner VPS setup (Hetzner CX22 or larger recommended — 2 vCPU / 4 GB RAM)

```bash
# On a fresh Ubuntu 22.04 server
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
usermod -aG docker $USER
newgrp docker

# Verify
docker --version
docker compose version
```

### 5. Deploy

```bash
git clone <your-repo-url> daily-ai-brief
cd daily-ai-brief

# Create .env with your credentials
nano .env

docker compose up -d --build
```

The container starts the scheduler and wakes up at 07:30 UTC every day.

---

## Testing manually

Run the full pipeline right now (ignores the schedule):

```bash
# With Docker (recommended — matches prod environment)
docker compose run --rm daily-brief python main.py --now

# Without Docker (local Python 3.11+)
pip install -r requirements.txt
playwright install --with-deps chromium
python main.py --now
```

You should see three Telegram messages arrive within ~90 seconds.

---

## Checking logs

```bash
# Live log tail
docker compose logs -f

# Or read the log file directly
cat logs/app.log

# Last 50 lines
tail -50 logs/app.log
```

Screenshots are saved to `screenshots/YYYYMMDD_N.png` and mounted on the host so you can inspect them without entering the container.

---

## Architecture

```
Pipeline (runs once per day):

1. FETCH  — TechCrunch AI RSS + HackerNews top stories + layoffs.fyi
2. RANK   — Claude scores all items 1-10 for Ukrainian dev audience vibility
3. TOP 3  — For each item (in parallel per item):
             a. Playwright screenshot → 1080×1920 PNG with dark border
             b. Claude generates hook / take / end_question / threads_version
4. SEND   — python-telegram-bot: photo + full commentary to your chat
```

**Fetchers are fault-tolerant:** if one source fails, the pipeline continues with the others.

**layoffs.fyi note:** The site is a JS-heavy Airtable embed. The scraper does a best-effort headless render. If Airtable changes their DOM, this fetcher may return 0 items — that's fine, the other two sources provide plenty of content.

---

## Updating the Claude model

Edit `CLAUDE_MODEL` in your `.env`:

```
CLAUDE_MODEL=claude-opus-4-7   # more expensive, better quality
CLAUDE_MODEL=claude-haiku-4-5-20251001  # cheaper, faster
```

---

## Rebuilding after code changes

```bash
docker compose up -d --build
```
