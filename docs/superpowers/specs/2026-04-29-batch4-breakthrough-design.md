# Batch 4 breakthrough design

## Objective
Investigate two remaining high-value bottlenecks:
1. GPLinks PowerGam ledger proof, currently forcing ~95s browser PowerGam wait plus final Turnstile.
2. XUT IconCaptcha stability, currently causing slow retries when Step 1 does not pass on first attempt.

## Success oracles
- GPLinks breakthrough: a lane reaches `http://tesskibidixxx.com/` faster than the current ~148-151s path, or a concrete ledger mechanism is proven/falsified with captured evidence.
- XUT breakthrough: first-attempt IconCaptcha pass rate improves on live corpus/probes, or a solver selection rule is proven to avoid known wrong picks while preserving final `http://tesskibidixxx.com/`.

## Constraints
- Do not remove final-oracle checks.
- Do not promote unproven HTTP-only GPLinks success.
- Do not claim IconCaptcha win rate without live evidence.
- Production changes must have fallback/env guard unless repeatedly live-proven.

## Approach
- Run two independent research lanes in parallel.
- Main session reviews evidence and implements only low-risk, live-proven changes.
