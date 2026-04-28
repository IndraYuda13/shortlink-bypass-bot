# 2026-04-28 Solver Stabilization Workframe

## Objective
Improve IconCaptcha solver reliability for xut/autodime and root-cause local Turnstile solver failures for cuty/exe.

## Success oracles
- IconCaptcha: benchmark on captured labeled/validated challenges reaches repeatable >=90% live Step 1 success, target 99% if evidence supports it.
- Turnstile: identify exact failing boundary and either make local solver return a valid token for cuty/exe or produce a precise blocker with next provider/egress requirement.

## Current facts
- ClaimCoin IconCaptcha solver previously worked on ClaimCoin withdraw widgets.
- xut/autodime Step 1 is flaky: one run solved and reached gamescrate, another failed at Step 1.
- indra-api-hub service is crash-looping with systemd `203/EXEC`; old IconCaptcha API route returns 404 from another process on port 5001.
- turnstile-solver-api returns `ERROR_CAPTCHA_UNSOLVABLE` for cuty and exe sitekeys.

## Checklist
- [in progress] 1. Locate solver repos/services and current runtimes.
- [pending] 2. Capture or locate IconCaptcha challenge samples plus success/fail labels.
- [pending] 3. Build benchmark harness before changing solver code.
- [pending] 4. Root-cause Turnstile API failure with raw logs and provider boundary.
- [pending] 5. Patch the smallest proven fixes.
- [pending] 6. Verify live against shortlink samples, deploy, push repos, sync MyAiAgent.

## 2026-04-28 10:45 WIB update
- [done] 1. Located solver repos/services and current runtimes.
  - IconCaptcha repo: `/root/.openclaw/workspace/projects/iconcaptcha-solver`.
  - Current shortlink xut helper was still importing ClaimCoin's embedded solver.
  - Turnstile service: `turnstile-solver-api.service` on `127.0.0.1:5000`.
- [in progress] 2. Capture or locate IconCaptcha challenge samples plus success/fail labels.
  - Added capture support to `xut_live_browser.py` via `--iconcaptcha-capture-dir`.
  - Each Step 1 attempt can now save PNG plus `labels.jsonl` with solver output and pass/fail oracle.
- [done] 3. Build benchmark harness before changing solver code.
  - Added `scripts/benchmark_fixtures.py` in `projects/iconcaptcha-solver` for captured `labels.jsonl`.
- [done] 4. Root-cause Turnstile API failure with raw logs and provider boundary.
  - Production port 5000 returned instant `ERROR_CAPTCHA_UNSOLVABLE`; DB rows showed `CAPTCHA_FAIL` with `elapsed_time=0`.
  - Fresh debug instance on port 5002 solved both cuty and exe in ~45-48s.
  - Restarting production service made port 5000 solve both cuty and exe again.
  - Root cause is stale long-lived browser pool, not wrong sitekey or globally broken Turnstile solver.
- [in progress] 5. Patch the smallest proven fixes.
  - Added systemd drop-in `RuntimeMaxSec=21600` so the Turnstile browser pool refreshes every 6h.
  - Added one clean retry in `cuty_live_browser.solve_turnstile()` for transient solver-side `CAPTCHA_FAIL`.
- [pending] 6. Verify live against shortlink samples, deploy, push repos, sync MyAiAgent.

## 2026-04-28 10:58 WIB verification
- [done] 6. Verify live against shortlink samples, deploy, push repos, sync MyAiAgent.
  - Shortlink unit gate: `34/34 OK` via `.venv/bin/python -m unittest discover -s tests -v`.
  - IconCaptcha solver unit gate: `4/4 OK` via `PYTHONPATH=src python3 -m unittest discover -s tests -v`.
  - IconCaptcha fixture benchmark gate: first xut/autodime live pass fixture scored `1/1` for thresholds `8,12,16,20,24,28`. This is only a smoke fixture, not a 90% corpus claim.
  - Raw Turnstile solver gate after service refresh: cuty and exe sitekeys both returned ready tokens from production `127.0.0.1:5000`.
  - Cuty engine live gate: `https://cuty.io/AfaX6jx` returned final `https://www.google.com/`, so `cuty.io` promoted to `live_bypass`.
  - Xut live gate: Step 1 IconCaptcha passed on attempt 1 and the helper reached gamescrate Cloudflare again; final is still blocked at gamescrate waiting/verification, so `xut.io` remains `partial`.
  - Bot service restarted and is active.
  - Repos pushed: `shortlink-bypass-bot@6305af6`, `iconcaptcha-solver@1653268`.
  - MyAiAgent backup pushed: `5107c34b75`.
