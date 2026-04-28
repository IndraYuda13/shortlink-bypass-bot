# 2026-04-28 Remaining Shortlink Families Workframe

## Objective
Close the remaining partial families without adding extra bot commands. Keep `/bypass` universal and only promote a family after a final URL oracle is live-proven.

## Parent checklist
- [in progress] 1. Baseline current xut/gplinks/exe behavior and docs.
- [in progress] 2. Parallel investigations for independent blockers.
- [pending] 3. Implement smallest proven patches.
- [pending] 4. Live verify sample URLs.
- [pending] 5. Update registry/docs/tests, restart bot, push project, sync MyAiAgent.

## Current partial targets
- `xut.io/hd7AOJ` expected final `http://tesskibidixxx.com`.
- `gplinks.co/YVTC` expected final `http://tesskibidixxx.com`.
- `exe.io/vkRI1` expected final `https://google.com`.

## Success oracle
- Engine or bot `/bypass` returns the downstream final target, not just a mapped gate, UI progress, token, or intermediate callback.

## 2026-04-28 exe milestone
- [done] `exe.io/vkRI1` final lane proven.
- Evidence:
  - CDP helper followed `exe.io -> exeygo.com`.
  - Submitted `before-captcha` form.
  - Extracted Turnstile sitekey from `app_vars.turnstile_site_key` because `.cf-turnstile` container is not always materialized in DOM.
  - Local Turnstile solver returned a valid token.
  - Injected `cf-turnstile-response` and `g-recaptcha-response` into `form#link-view`.
  - Submitted `form#link-view`, reached `form#go-link`, then submitted it.
  - Final URL: `https://www.google.com/`.
- Code:
  - Added `exe_live_browser.py`.
  - Wired `_handle_exe` to `_resolve_exe_live`.
  - Promoted `exe.io` to `live_bypass`.

## 2026-04-28 gplinks investigation result
- [blocked] `gplinks.co/YVTC` remains partial.
- Strongest evidence from browser/PowerGam investigation:
  - Final candidate still returns `error_code=not_enough_steps`.
  - Visible PowerGam form replay and common cookie/field variations do not create server-side enough-step proof.
  - Current blocker is GPT rewarded/interstitial lifecycle, especially `impressionViewable` / rewarded slot events.
- Decision: do not promote until a real browser helper reaches non-error downstream target.

## 2026-04-28 xut status after remaining-family pass
- [blocked] `xut.io/hd7AOJ` remains partial.
- Current evidence:
  - Step 1 IconCaptcha is still not stable enough. Fresh capture set had multiple failed attempts and one later pass.
  - A light probe also ended with `canvas missing` after repeated attempts in one run.
  - Earlier successful Step 1 still reaches gamescrate Cloudflare/waiting-for-response, not the final target.
- Decision: keep `xut.io` partial. Next proper work is a larger labeled IconCaptcha corpus plus gamescrate-specific CF handoff testing.

## Parent checklist status after this pass
- [done] 1. Baseline current xut/gplinks/exe behavior and docs.
- [done] 2. Parallel investigations for independent blockers.
- [done] 3. Implement smallest proven patches.
- [done] 4. Live verify sample URLs.
- [pending] 5. Update registry/docs/tests, restart bot, push project, sync MyAiAgent.

## 2026-04-28 11:xx continuation probes
- Direct continuation resumed for remaining partials while subagents work in parallel.
- `xut.io`:
  - `artifacts/active/xut_icon_probe.py` showed Step 1 can pass again on attempt 1 with current solver (`selected_cell_number=4`, confidence around `0.70`).
  - A full `xut_live_browser.py` run captured another Step 1 pass (`selected_cell_number=2`, confidence around `0.965`) but Chrome/UC died during later step navigation with localhost chromedriver connection refused. This is a runtime stability problem in addition to gamescrate final gate.
- `gplinks.co`:
  - Plain CDP from original `gplinks.co/YVTC` hit Cloudflare before PowerGam.
  - Bootstrapping via curl_cffi to `powergam.online` avoided entry Cloudflare and advanced visible PowerGam steps, but GPT events stayed empty and `imps=0`.
  - Headless PowerGam direct probe reached `gplinks.co/YVTC?pid=1224622&vid=<encoded>` but got Cloudflare in browser; separate curl replay of same candidate still returned `not_enough_steps`.
  - Xvfb/non-headless Chrome also advanced steps but produced no GPT lifecycle events and reset to a new PowerGam `vid` after step 3 instead of reaching the final target. Forcing `imps=5` in browser did not help; PowerGam/server still reset.
- Current strongest blockers remain:
  - XUT: stabilize browser after Step 1 and solve gamescrate waiting response.
  - GPLINKS: real GPT rewarded/interstitial lifecycle is still absent on VPS/browser runs, so server-side proof is not created.
