# Total optimization batch 3 design

## Objective
Continue from batch 2 by profiling actual bottlenecks before cutting more waits. The goal is to reduce the slowest proven lanes without risking final-oracle correctness.

## Scope
1. GPLinks: profile PowerGam loop and final Turnstile gate timing, then trim only waits that are proven unnecessary.
2. XUT: profile Step 1/IconCaptcha timing and gamescrate/Step 6 transitions, then optimize retries/waits if safe.
3. Cuty/Exe Turnstile: measure local solver latency to see whether API/browser-pool tuning can reduce the ~70s HTTP lanes.

## Success oracle
- Each production change must keep live final URL success.
- Record before/after wall time, seconds saved, percent faster, and speedup ratio.
- Risky shortcuts stay behind environment flags.

## Non-goals
- No promotion of token families to live_bypass.
- No removal of GPLinks PowerGam or final Turnstile callback.
- No retry of failed XUT HTTP-to-gamescrate hybrid.
