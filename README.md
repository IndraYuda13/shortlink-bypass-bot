# shortlink-bypass-bot

Telegram bot and Python engine for analyzing and bypassing selected shortlink families.

## Current support

- `link.adlink.click`
  - Live browser lane implemented
  - Fast lane: Cloudflare/session bootstrap, then direct extraction from `blog.adlink.click/<alias>`
  - Fallback lane retained for slower intermediate hops when needed
- `oii.la`
  - Static analysis and flow mapping
- `shrinkme.click`
  - Static analysis and flow mapping

## What this project does

- Accepts `/bypass <url>` and `/adlink <url>` from Telegram
- Detects the shortlink family from the host
- Extracts useful runtime facts such as hidden fields, timers, captcha hints, and downstream URLs
- Uses a live Chromium helper for Adlink when plain HTTP is blocked by Cloudflare
- Sends immediate progress feedback in Telegram and edits the same message until the job finishes

## Why Adlink uses a real browser

For `link.adlink.click`, plain `requests` is not enough from a cold session in this environment.
Both the entry URL and the blog hop return Cloudflare `403 Just a moment...` pages unless a real browser session solves the challenge first.

## Requirements

System packages:

- Python 3.11+
- Google Chrome or Chromium
- `xvfb-run`

Python packages:

```bash
pip install -r requirements.txt
```

## Quick start

```bash
git clone <your-repo-url>
cd shortlink-bypass-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 engine.py https://link.adlink.click/SfRi --pretty
```

## Run the Telegram bot

```bash
cp .env.example .env
# fill TELEGRAM_BOT_TOKEN in your shell or env file
source .venv/bin/activate
export TELEGRAM_BOT_TOKEN='your_bot_token'
python3 bot.py
```

## Optional environment variables

- `TELEGRAM_BOT_TOKEN`
- `SHORTLINK_BYPASS_ADLINK_BROWSER_TIMEOUT`
- `SHORTLINK_BYPASS_ADLINK_HELPER`
- `SHORTLINK_BYPASS_HELPER_PYTHON`
- `SHORTLINK_BYPASS_HELPER_PYTHONPATH`

Defaults are chosen so the helper runs with the current Python interpreter unless overridden.

## Deploy with systemd

Example unit file:

- `systemd/shortlink-bypass-bot.service.example`

## Project layout

- `bot.py` - Telegram polling bot and progress updates
- `engine.py` - family detection and orchestration
- `adlink_live_browser.py` - live Chromium helper for Adlink
- `references/` - technical notes
- `ROADMAP.md` - current implementation tracker

## Current limitations

- Only Adlink has an implemented live bypass lane at the moment
- Other families still return structured analysis rather than full bypass execution
- Fast-lane reliability across more Adlink aliases still needs broader validation
