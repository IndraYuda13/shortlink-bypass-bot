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
| `link.adlink.click` | Live bypass | Uses browserless TLS impersonation against `blog.adlink.click`, with live Chromium kept as fallback |
| `oii.la` | Token bypass | Token-tail extraction returns sampled `onlyfaucet` target; live Turnstile/timer completion is not proven |
| `tpi.li` | Token bypass | Same token-tail Turnstile family as `oii.la`; extracts sampled `99faucet` target |
| `aii.sh` | Token bypass | ShrinkBixby token-tail extraction; sampled target is `coinadster.com/shortlink.php?...` |
| `cuty.io` | Live bypass | HTTP-only Cuttlinks form replay solves Turnstile, mirrors the final timer/go-form flow, and returns sampled `google.com` target; VHit replay is opt-in and CDP browser fallback is disabled by default |
| `lnbz.la` | Live bypass | Browserless article/survey chain through `avnsgames.com` reaches `/links/go` and returns sampled `cryptoearns.com` target |
| `sfl.gl` | Live bypass | Direct VPS egress is Cloudflare-blocked, but WARP proxy fallback reaches SafelinkU API flow and returns sampled `google.com` target |
| `gplinks.co` | Live bypass | Browser PowerGam lane completes the 3-step gate, solves final Turnstile through the page callback, and returns sampled `tesskibidixxx.com` target |
| `ez4short.com` | Live bypass | Fast `game5s.com` referer lane unlocks final go-link form and returns sampled `tesskibidixxx.com` target |
| `shrinkme.click` | Live bypass | Uses a direct `MrProBlogger -> /links/go` shortcut with ThemeZon-style referer spoof over plain HTTP |
| `xut.io` -> `autodime cwsafelinkphp` | Live bypass | Live browser lane now reaches IconCaptcha Step 1, gamescrate Step 5, xut Step 6, and clicks `Get Link` to return sampled `tesskibidixxx.com` target |
| `exe.io` | Live bypass | HTTP-only `exe.io -> exeygo.com` lane solves Turnstile, submits CakePHP forms, and returns sampled `google.com` target |

## How it works

- `bot.py` receives Telegram commands, enforces the required join gate, and edits the same status message while work is running
- `engine.py` detects the target family and chooses the right handler
- `adlink_live_browser.py` stays as Adlink fallback when the faster browserless lane is not enough
- `xut_live_browser.py` drives the live autodime -> gamescrate -> xut Step 6 lane, preferring the standalone IconCaptcha API at `SHORTLINK_BYPASS_ICONCAPTCHA_ENDPOINT` with local fallback; set `SHORTLINK_BYPASS_XUT_CLICK_FINAL=1` to restore final-click behavior or `SHORTLINK_BYPASS_XUT_GAMESCRATE_DWELL=<seconds>` to tune Step 5 dwell.
- `cuty_http_fast.py` solves `cuty.io` over HTTP with curl_cffi plus the local Turnstile solver; VHit replay can be enabled with `SHORTLINK_BYPASS_CUTY_HTTP_VHIT=1`. CDP browser fallback is disabled by default to avoid opening Chrome on desktop deployments; set `SHORTLINK_BYPASS_CUTY_BROWSER_FALLBACK=1` to re-enable it.
- `cuty_live_browser.py` remains the Cuty/Cuttlinks fallback for same-browser Turnstile and final go-form flow.
- `exe_http_fast.py` solves `exe.io` over HTTP with curl_cffi plus the local Turnstile solver, keeping the browser helper as fallback. Final submit redirects are not auto-followed so `/links/back/...` reward paths are preserved before target homepages can truncate them.
- `gplinks_http_fast.py` is kept as opt-in research with `SHORTLINK_BYPASS_GPLINKS_HTTP_FAST=1`; default skips it because the current live result is a quick `not_enough_steps` before browser fallback.
- `gplinks_live_browser.py` drives the PowerGam 3-step browser flow, scroll/verify handling, pre-navigation network ledger recorder, and final GPLinks Turnstile callback lane; `SHORTLINK_BYPASS_GPLINKS_NAVIGATE_FINAL=1` restores old final navigation after a valid final href is exposed. `SHORTLINK_BYPASS_GPLINKS_EARLY_CONTINUE_SECONDS=1` enables the current aggressive PowerGam timer experiment; `2` is known to fail with `not_enough_time` on sample `YVTC`.
- `references/` and `ROADMAP.md` keep technical notes and current implementation status

Flow and target docs:

- [`docs/FLOWS.md`](docs/FLOWS.md)
- [`references/target-sample-catalog.md`](references/target-sample-catalog.md)

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

- `/start`
- `/help`
- `/status`
- `/ping`
- `/bypass <url>`
- `/adlink <url>`
- plain `https://...` URL messages also work and are treated like `/bypass <url>`

## Access gate

This bot can enforce a required Telegram group membership before letting someone use the bypass commands.

Current intended gate:

- required group: `Cari Garapan`
- invite link shown to blocked users: `https://t.me/+Vfpap1m10v5iODA1`

When a user is not in the required group, the bot replies with:

- a short locked-access message
- a `Join Cari Garapan` button
- a `Sudah join, cek lagi` button

## Example result

```json
{
  "status": 1,
  "family": "link.adlink.click",
  "message": "HTTP_IMPERSONATION_BYPASS_OK",
  "stage": "blog-http-fast",
  "bypass_url": "https://bitcointricks.com/shortlink.php?short_key=fu8dbowmwyx1q1f9et8qmao3o9r5wfu4"
}
```

## Why Adlink now prefers browserless HTTP

For `link.adlink.click`, plain `requests` is still not enough from a cold session in this environment.

Observed behavior:

- `GET https://link.adlink.click/<alias>` returns Cloudflare `403 Just a moment...`
- `GET https://blog.adlink.click/<alias>` also returns Cloudflare `403`
- Reusing cookies inside a plain `requests.Session` was still not enough to render the final blog target reliably
- `curl_cffi` with browser impersonation can open `https://blog.adlink.click/<alias>` directly, wait the internal timer, and post `/links/go` without Selenium

Because of that, the current winning lane is:

1. try browserless `curl_cffi` impersonation against `blog.adlink.click`
2. post `/links/go` after the real timer boundary
3. fall back to the live Chromium helper only if the browserless lane fails

## Why ShrinkMe is still not instant

For the verified sample lane, the useful shortcut is not decoding ThemeZon deeper. The real gate is the downstream MrProBlogger timer.

- direct `GET https://en.mrproblogger.com/<alias>` works when the request carries a ThemeZon-flavored referer
- safe final submit boundary is around `11.6s` after the MrProBlogger page load, not the older `13s` sleep
- the engine still keeps the longer ThemeZon replay as evidence-backed fallback, but the fast lane now starts from MrProBlogger directly

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
- `SHORTLINK_REQUIRED_JOIN_CHAT_ID`
- `SHORTLINK_REQUIRED_JOIN_CHAT_TITLE`
- `SHORTLINK_REQUIRED_JOIN_LINK`
- `SHORTLINK_BYPASS_ADLINK_BROWSER_TIMEOUT`
- `SHORTLINK_BYPASS_ADLINK_IMPERSONATE`
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
- [x] Implement browserless Adlink fast lane with TLS impersonation
- [x] Add Telegram progress updates with same-message edits
- [x] Publish a cleaned public repo with deployment examples
- [ ] Validate the Adlink fast lane across more aliases
- [x] Add live `shrinkme.click` chain support for sampled alias flow
- [x] Add direct `MrProBlogger` shortcut for the verified shrinkme sample
- [ ] Validate the `shrinkme.click` chain across more aliases
- [x] Add `tpi.li` token-tail extraction using the shared Turnstile landing handler
- [x] Add `aii.sh` token-tail extraction for ShrinkBixby samples
- [x] Add browserless `sfl.gl` SafelinkU API flow for sampled `google.com` oracle
- [x] Add `gplinks.co` live browser lane with PowerGam steps plus final Turnstile callback oracle
- [x] Add browserless `ez4short.com` fast lane for sampled `tesskibidixxx.com` oracle
- [ ] Add broader examples and regression checks for supported families

## Security and sanitization notes

- This repo does not ship a real bot token or deployment env file
- Live logs, local virtualenv contents, and host-specific runtime artifacts are excluded from the repository
- Public docs keep examples sanitized and focused on flow behavior rather than sensitive runtime state

## License

MIT

## Benchmarking speed

Use the benchmark matrix runner to capture comparable JSONL records for supported sample URLs:

```bash
source .venv/bin/activate
python3 benchmark_matrix.py --family cuty.io --output artifacts/active/benchmark-matrix/latest.jsonl --print
python3 benchmark_matrix.py --family exe.io --output artifacts/active/benchmark-matrix/latest.jsonl --print
```

Each record includes wall time, engine result, `bypass_url`, and a profiler summary. Keep final URL validation strict: benchmark wins count only when the returned URL is the real downstream target, not an intermediate page or a truncated homepage.

### XUT speed note

The `xut.io` helper now polls readiness for IconCaptcha and final href states instead of sleeping through large fixed waits. Keep `SHORTLINK_BYPASS_XUT_GAMESCRATE_DWELL=4` as the safe default until repeated benchmark rows prove a lower dwell still preserves the final `Get Link` oracle.

### GPLinks investigation note

`gplinks_live_browser.py` records GPT/ad lifecycle evidence and a pre-navigation network ledger while keeping the browser lane as the production path. The current recorder captures fetch/XHR/sendBeacon/form submits, cookie/storage mutations, and resource hints such as `tracki.click/ads/api/get-banner.php`, `tracki.click/ads/api/imp.php`, `tracki.click/ads/api/pop.php`, `b7510.com`/`bvtpk.com`, and final `POST /links/go`. Use direct helper output when investigating PowerGam HTTP replay:

```bash
python3 gplinks_live_browser.py https://gplinks.co/YVTC --timeout 340 > artifacts/active/benchmark-matrix/gplinks-live-helper.json
```

Do not promote GPLinks HTTP replay until the ledger proof is reproduced and the final URL oracle still returns a non-GPLinks downstream target.
