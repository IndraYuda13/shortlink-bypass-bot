# 2026-04-28 gplinks.co final push

## Objective
Make `https://gplinks.co/YVTC` return final `http://tesskibidixxx.com` through the existing `/bypass` path. Do not promote until a real browser or engine reaches a non-error downstream final.

## Success oracle
- `engine.py https://gplinks.co/YVTC --pretty` returns `status=1` with `bypass_url=http://tesskibidixxx.com` or equivalent non-error downstream target.
- If not solved, evidence must identify the exact remaining boundary: PowerGam GPT lifecycle vs final GPlinks `#captchaButton` unlock.

## Known blockers
- HTTP replay with cookies/form fields/Tracki calls still gives `error_code=not_enough_steps`.
- Real browser can complete PowerGam steps but GPT lifecycle events are absent or insufficient.
- Final candidate page can load as 200 but `#captchaButton` stays disabled.
- PowerGam can show `AdBlocker Detected` / `Brave browser is not supported`, likely poisoning ad proof.

## Checklist
- [in progress] 1. Re-run browser probe with more normal Chrome fingerprint and full final-page script hooks.
- [pending] 2. Identify `#captchaButton` unlock condition and exact network/script boundary.
- [pending] 3. Patch guarded browser helper only if final oracle is reached.
- [pending] 4. Verify engine, update docs/tests, restart service, commit/push/sync.

## 2026-04-28 final-gate helper evidence

- Added guarded helper draft: `gplinks_live_browser.py`.
- Browser path now reaches final candidate page and uses the page's own Turnstile completion callback path, not just a blind button enable.
- Key success evidence from `/tmp/gplinks_helper_run11.json`:
  - `#captchaButton` changed to `Get Link`.
  - final href exposed by GPLinks page: `http://tesskibidixxx.com/`.
  - Turnstile token was used against DOM sitekey `0x4AAAAAAAynCEcs0RV-UleY`.
- Important nuance: a manual direct `fetch('/links/go')` after the page's own ajax can return 403, so the helper must trust the first in-page jQuery submit result and read/click the resulting button href instead of doing a second direct fetch.
- Reliability blocker still open: repeated live runs can stall at `powergam.online` 403 / PowerGam step timeout, likely due the PowerGam scroll/verification/adblock sensitivity or rate/exposure state. Keep registry status conservative until a clean engine run returns status=1 with the new helper.


## 2026-04-28 HTTP fast-lane probe

- Added `gplinks_http_fast.py` as an HTTP-first GPLinks probe and engine preflight lane.
- Live run: `.venv/bin/python gplinks_http_fast.py https://gplinks.co/YVTC --timeout 90`.
- Result: `status=0`, `stage=powergam-ledger`, `message=HTTP_FAST_POWERGAM_LEDGER_REJECTED`, `waited_seconds=2.1`.
- Bounded replay attempted:
  - entry redirect decode
  - PowerGam page fetch with referer
  - local cookies for `lid`, `pid`, `pages`, `vid`, `step_count`, `imps`, `adexp`
  - three `adsForm` POSTs with `step_id=1/2/3`, `ad_impressions=5`, `visitor_id`, and final `next_target`
- Server still redirected final candidate to `gplinks.co/link-error?alias=YVTC&error_code=not_enough_steps`.
- Meaning: full HTTP replacement is not yet valid because PowerGam ledger requires a browser-side proof beyond form fields/cookies, likely GPT impression/reward or JS activity proof. Keep browser fallback as production success lane.
