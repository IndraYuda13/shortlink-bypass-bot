# Total optimization batch 2 design

## Objective
Continue shortlink speed optimization after batch 1. The target is to cut unnecessary waits/steps while keeping the exact live final oracle per family.

## Approved direction
Boskuu approved continuing with the next worthwhile lanes:
1. GPLinks aggressive polling to push `~148.6s` lower.
2. XUT Step 1/IconCaptcha and gamescrate dwell cuts where safe.
3. Turnstile solver latency review for Cuty/Exe only if browser-heavy lanes do not yield enough.

## Success oracle
A change is accepted only if:
- `engine.py <sample> --pretty` returns `status=1`.
- final URL remains the expected downstream target or equivalent.
- before/after wall time is recorded.
- fallback or env toggle remains for riskier behavior.

## Design
- GPLinks: keep the required PowerGam browser path and final Turnstile callback. Optimize only timing mechanics: replace more fixed sleeps with state checks, make cooldown/dwell values tunable, and verify with live sample.
- XUT: keep full browser path because HTTP hybrid is falsified. Optimize within browser path: gamescrate dwell, Step 1 waits, and final href handling. Use env toggles for lower dwell or legacy click behavior.
- Cuty/Exe: no change unless needed. Both are already HTTP-first and dominated by Turnstile solver latency.

## Non-goals
- Do not mark token families as `live_bypass`.
- Do not remove GPLinks PowerGam or final Turnstile callback.
- Do not retry the failed XUT HTTP Step 1-4 -> browser gamescrate hybrid as production.
