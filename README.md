# shortlink-bypass-bot

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-active--development-orange)

Telegram bot and Python engine for analyzing and bypassing selected shortlink families.

## Why this repo exists

Some shortlink families are cheap to inspect with plain HTTP. Others hide the real result behind Cloudflare, browser-only state, timed hops, and downstream redirect chains. This project keeps those lanes separated so supported targets can escalate only when needed.

## Use cases

- Analyze a shortlink family before writing custom automation
- Run `/bypass` or `/adlink` from Telegram and get live progress updates
- Reuse the family handler structure to add more supported hosts
- Document findings and success oracles for tricky shortlink chains

## Current support

| Family | Status | Notes |
| --- | --- | --- |
| `link.adlink.click` | Live bypass | Uses a live Chromium lane for Cloudflare and final extraction |
| `oii.la` | Analysis only | Static mapping and downstream extraction |
| `shrinkme.click` | Live bypass | Replays `ThemeZon -> MrProBlogger -> /links/go` and waits the final timer over plain HTTP |

## How it works

- `bot.py` receives Telegram commands and edits the same status message while work is running
- `engine.py` detects the target family and chooses the right handler
- `adlink_live_browser.py` runs the Adlink browser lane when plain HTTP is blocked
- `references/` and `ROADMAP.md` keep technical notes and current implementation status

Flow docs:

- [`docs/FLOWS.md`](docs/FLOWS.md)

## Quick start

```bash
git clone https://github.com/IndraLawliet13/shortlink-bypass-bot.git
cd shortlink-bypass-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 engine.py https://link.adlink.click/SfRi --pretty
```

## Run the Telegram bot

```bash
source .venv/bin/activate
export TELEGRAM_BOT_TOKEN='your_bot_token'
python3 bot.py
```

Available commands:

- `/bypass <url>`
- `/adlink <url>`
- `/help`

## Example result

```json
{
  "status": 1,
  "family": "link.adlink.click",
  "message": "LIVE_BROWSER_CHAIN_BYPASS_OK",
  "stage": "blog-fast-final",
  "bypass_url": "https://earn-pepe.com/member/shortlinks/verify/ca7c179027eb04abfb79"
}
```

## Why Adlink uses a real browser

For `link.adlink.click`, plain `requests` is not enough from a cold session in this environment.

Observed behavior:

- `GET https://link.adlink.click/<alias>` returns Cloudflare `403 Just a moment...`
- `GET https://blog.adlink.click/<alias>` also returns Cloudflare `403`
- Reusing cookies inside a plain `requests.Session` was still not enough to render the final blog target reliably

Because of that, the current winning lane is a live Chromium session under `xvfb-run`, followed by direct extraction from the rendered Adlink blog page.

## Requirements

System packages:

- Python 3.11+
- Google Chrome or Chromium
- `xvfb-run`

Python packages:

```bash
pip install -r requirements.txt
```

## Configuration

Environment variables:

- `TELEGRAM_BOT_TOKEN`
- `SHORTLINK_BYPASS_ADLINK_BROWSER_TIMEOUT`
- `SHORTLINK_BYPASS_ADLINK_HELPER`
- `SHORTLINK_BYPASS_HELPER_PYTHON`
- `SHORTLINK_BYPASS_HELPER_PYTHONPATH`

Defaults are chosen so the helper runs with the current Python interpreter unless overridden.

A starter env file is included at:

- `.env.example`

## Deployment

A sample systemd unit is included at:

- `systemd/shortlink-bypass-bot.service.example`

## Project layout

- `bot.py` - Telegram polling bot and progress updates
- `engine.py` - family detection and orchestration
- `adlink_live_browser.py` - live Chromium helper for Adlink
- `references/` - technical notes
- `docs/` - flow documentation
- `ROADMAP.md` - current implementation tracker

## Public roadmap

- [x] Implement live Adlink browser lane
- [x] Add Telegram progress updates with same-message edits
- [x] Publish a cleaned public repo with deployment examples
- [ ] Validate the Adlink fast lane across more aliases
- [x] Add live `shrinkme.click` chain support for sampled alias flow
- [ ] Validate the `shrinkme.click` chain across more aliases
- [ ] Add broader examples and regression checks for supported families

## Security and sanitization notes

- This repo does not ship a real bot token or deployment env file
- Live logs, local virtualenv contents, and host-specific runtime artifacts are excluded from the repository
- Public docs keep examples sanitized and focused on flow behavior rather than sensitive runtime state

## License

MIT
