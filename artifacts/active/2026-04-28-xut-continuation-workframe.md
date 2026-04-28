# 2026-04-28 XUT Continuation Workframe

## Objective
Get `https://xut.io/hd7AOJ` to final `http://tesskibidixxx.com` through `/bypass`, without promoting until final URL is live-proven.

## Current evidence
- Step 1 IconCaptcha can pass with current solver, but not reliably.
- Multiple captured passes exist, including confidence ~0.70 and ~0.965 cases.
- Full helper run has reached gamescrate Cloudflare/waiting-response before.
- A later full run passed Step 1 but Chrome/undetected-chromedriver died during later step navigation with `localhost chromedriver connection refused`.
- Subagent xut deep continuation timed out with no final deliverable, so no final xut claim exists.

## Active hypotheses
1. IconCaptcha is not the only blocker; current solver is viable enough to continue if retries are handled robustly.
2. `undetected_chromedriver` process stability is a blocker after Step 1/2 transitions.
3. gamescrate final gate may need a different lane than current FlareSolverr attach, such as direct Chrome CDP wait/reload, cookie export/import, WARP egress, or non-headless/Xvfb profile.

## Checklist
- [done] 1. Stabilize post-Step1 browser flow enough to reach gamescrate consistently.
- [done] 2. Capture gamescrate setcookie/token/cookies/network state.
- [done] 3. Test alternate gamescrate final lanes.
- [done] 4. Patch helper after proven final.

## Result
- Proven final run: `xut_live_helper_verify4.json` returned status 1 `XUT_FINAL_OK` with `bypass_url=http://tesskibidixxx.com/`.
- Root cause of previous miss: clicking exactly when gamescrate timer flips can return `Error: too_fast`; and on xut Step 6, loose text matching can hit the nearby `Download` ad instead of exact `Get Link`.
- Fix: direct browser lane waits extra dwell on gamescrate, waits for exact visible `Get Link`, and clicks exact text only.

## Result update
- [done] 1. Stabilize post-Step1 browser flow enough to reach gamescrate consistently.
  - Evidence: `xut_headful_final_probe_click_ready_1777355153.json` reached gamescrate Step 5, xut Step 6, and final href.
- [done] 2. Capture gamescrate/xut final state.
  - Final visible href: `http://tesskibidixxx.com/`.
- [done] 3. Patch helper lane.
  - `xut_live_browser.py` now treats direct browser gamescrate Step 5 -> xut Step 6 -> exact `Get Link` as the primary final path.
- [done] 4. Live verify.
  - `artifacts/active/xut_live_helper_verify_1777355376.json` returned `status=1`, `message=XUT_FINAL_OK`, `bypass_url=http://tesskibidixxx.com/`.
- [pending] 5. Registry/docs/tests/deploy/push sync.

## Verification and deploy
- [done] Unit tests: `.venv/bin/python -m unittest discover -s tests -v` -> 36/36 OK.
- [done] Live engine verification: `.venv/bin/python engine.py https://xut.io/hd7AOJ --pretty` -> `status=1`, `message=XUT_FINAL_OK`, `bypass_url=http://tesskibidixxx.com/`.
- [done] Service restart: `shortlink-bypass-bot.service` active; `turnstile-solver-api.service` active.
- [done] Registry/docs: `xut.io` promoted to `live_bypass`; `gplinks.co` remains partial.

## Compact verification evidence
- Helper proof: `xut_live_browser.py https://xut.io/hd7AOJ` under `xvfb-run -a` returned `status=1`, `message=XUT_FINAL_OK`, `stage=final-bypass`, `bypass_url=http://tesskibidixxx.com/`.
- Engine proof: `ShortlinkBypassEngine(timeout=30).analyze('https://xut.io/hd7AOJ')` returned `status=1`, `message=XUT_FINAL_OK`, `stage=final-bypass`, `bypass_url=http://tesskibidixxx.com/`.
- Test gate: `.venv/bin/python -m unittest discover -s tests -v` returned `36 tests OK`.
