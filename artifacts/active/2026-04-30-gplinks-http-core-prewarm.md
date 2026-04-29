# 2026-04-30 GPLinks HTTP-core Turnstile prewarm

## Goal

Upgrade GPLinks toward the ClaimCoin-style architecture: HTTP remains the core lane, solver is only a helper boundary, and Turnstile solving starts in parallel with the GPLinks engine instead of waiting until the final gate.

## Changes

- `gplinks_http_fast.py`
  - Added `TurnstilePrewarmer`.
  - Starts local Turnstile solving at `run()` start using the configured/default GPLinks sitekey.
  - Reuses a ready token at `/links/go` when the final page sitekey matches.
  - Rejects mismatched or expired tokens and falls back to synchronous solve.
  - Emits timeline stages: `turnstile-prewarm-start`, `turnstile-prewarm-miss`, and `turnstile-token` with `source=prewarm|sync`.
- `engine.py`
  - GPLinks HTTP fast lane is now default-on via `SHORTLINK_BYPASS_GPLINKS_HTTP_FAST=1`.
  - HTTP success facts now include `token_source`.
- Docs/tests updated.

## Verification

Unit and regression tests:

```text
.venv/bin/python -m unittest tests.test_gplinks_http_fast tests.test_gplinks -q
Ran 15 tests in 0.011s
OK

.venv/bin/python -m unittest discover -s tests -q
Ran 83 tests in 0.103s
OK
```

Live HTTP helper probe:

```text
.venv/bin/python gplinks_http_fast.py https://gplinks.co/YVTC --timeout 90 --solver-url http://127.0.0.1:5000
status=0
stage=powergam-ledger
message=HTTP_FAST_POWERGAM_LEDGER_REJECTED
waited_seconds=2.86
```

Interpretation: prewarm is wired and starts at engine start, but the current sample still fails before the final GPLinks Turnstile gate because the server rejects the HTTP PowerGam ledger with `not_enough_steps`. That means the remaining blocker is still PowerGam step proof, not the final Turnstile solve timing.

## Current top-level status

- HTTP-core engine: done.
- Turnstile prewarm: done.
- `/links/go` token reuse: done, test-covered.
- Browser fallback removal: pending. Cannot remove honestly until the HTTP lane reaches the final GPLinks page instead of `not_enough_steps`.
- Remaining investigation: reproduce the browser-only PowerGam ledger proof over HTTP or find the exact transferable state from native browser submits.
