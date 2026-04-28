# XUT batch 3 timing profile

Target: `https://xut.io/hd7AOJ`
Date: 2026-04-28
Scope: timing profile only. Production code was not edited.

## Success oracle

- Final URL: `http://tesskibidixxx.com/`
- Raw success capture: `artifacts/active/total-optimization/xut-batch3-profile-raw-4.json`
- Probe helper used only as an artifact: `artifacts/active/total-optimization/xut_batch3_timing_probe.py`

## Current implementation inspected

- `xut_live_browser.py` default `XUT_GAMESCRATE_DWELL_SECONDS = 4` via `SHORTLINK_BYPASS_XUT_GAMESCRATE_DWELL`.
- Step 1 has already replaced the old initial `12s` sleep with widget/canvas readiness polling in the current worktree.
- Step 1 still has fixed waits inside `solve_step1_until_step2`:
  - `4s` after IconCaptcha widget click before canvas read.
  - `6s` after canvas click before checking Step 2.
- Gamescrate path:
  - waits until `Open Final Page` is visible.
  - sleeps dwell, currently `4s`.
  - clicks `Open Final Page`.
  - waits on xut Step 6 until visible exact `Get Link` href is non-blocklisted.
- Step 6 already returns visible exact `Get Link` href without clicking unless `SHORTLINK_BYPASS_XUT_CLICK_FINAL=1`.

## Measured successful run

Command:

```bash
xvfb-run -a .venv/bin/python artifacts/active/total-optimization/xut_batch3_timing_probe.py \
  https://xut.io/hd7AOJ \
  --out artifacts/active/total-optimization/xut-batch3-profile-raw-4.json
```

Result:

- Status: `1`
- Message: `XUT_FINAL_OK`
- Final: `http://tesskibidixxx.com/`
- Wall time: `98.243s`
- Dwell env/default observed: `4.0s`

### Phase timings

| Phase | Seconds | Notes |
|---|---:|---|
| Chrome launch | `0.895` | UC browser startup. |
| Initial get to Autodime Step 1 | `3.945` | Landed on `https://autodime.com/`, `Step 1/6`, countdown at `10`. |
| Step 1 IconCaptcha -> Step 2 | `46.126` | 1 attempt, API solver response had click coords. Solver call itself took `4.671s`. |
| Steps 2-4 -> gamescrate | `23.270` | Arrived at `https://gamescrate.app/game/pool-master`, `Step 5/6`, countdown at `10`. |
| gamescrate entry wait | `0.006` | Already on gamescrate when checked. |
| gamescrate wait until Open Final Page | `10.193` | Timer reached `0`, `Open Final Page` visible. |
| gamescrate dwell | `4.000` | Current default. |
| click Open Final Page + fixed post wait | `3.291` | Click succeeded and landed on `xut.io/hd7AOJ?sl=...`. Includes current fixed `3s` sleep. |
| Step 6 wait to final href | `6.085` | 7 polls. Visible exact `Get Link` href was `http://tesskibidixxx.com/`. |

## Important failed/invalid probes

These were not used as the success profile, but they explain instability seen during profiling:

- `xut-batch3-profile-raw.json`: ChromeDriver disconnected during initial get after `2.907s`.
- `xut-batch3-profile-raw-2.json`: Step 1 API solver returned a schema without `click_x`, causing production-style helper exception after `45.187s` in Step 1.
- `xut-batch3-profile-raw-3.json`: artifact probe fell back to local Python solver and passed Step 1, but ChromeDriver disconnected during Steps 2-4.
- `xut-batch3-profile-raw-headless-no-xvfb.json`: headless reached gamescrate but got stuck on Cloudflare/security verification; `Open Final Page` never actually appeared. Headless is not a valid timing lane for this target.

Interpretation: the valid production-shaped timing evidence is the non-headless xvfb success run. Headless should not be promoted for XUT.

## Bottleneck interpretation

1. **Step 1 is now the largest measured phase**: `46.126s` total. The old initial `12s` sleep is already gone in the current worktree, but `4s + 6s` fixed waits remain around the IconCaptcha canvas/click check. This is still the best safe optimization target.
2. **Gamescrate timer itself is expected**: `10.193s` until `Open Final Page`. This should not be cut by blind clicking because prior notes recorded `too_fast` risk.
3. **Current `4s` dwell is live-proven again**: final oracle survived with `4.000s` dwell. Do not cut below 4 yet without a dedicated ladder.
4. **Step 6 wait is moderate**: `6.085s`. The final href appeared after the xut Step 6 countdown. The code already skips final click, so only polling/post-click wait can be trimmed.
5. **Fixed `3s` post-open-final sleep is a safe candidate**: after gamescrate click, code sleeps `3s` before polling Step 6. A polling loop for `xut.io`/Step 6 body could replace this and probably save up to `1-3s` without changing boundaries.

## Safe next cuts

Recommended order:

1. **Patch the remaining Step 1 sleeps to polling, env-guarded or directly with conservative caps.**
   - Replace the `4s` canvas wait with polling until canvas `toDataURL()` is present and non-empty.
   - Replace the `6s` post-click wait with polling for Step 2 or captcha reset/failure.
   - Add finer Step 1 subphase telemetry before/with the patch because the total Step 1 phase is still large even after the initial `12s` sleep was removed.
   - Expected gain: `4-10s` on single-attempt runs, more on retries.

2. **Replace the fixed `3s` post gamescrate-click wait with state polling.**
   - Start polling immediately for `xut.io`, Step 6 text, or exact visible `Get Link` href.
   - Keep timeout cap unchanged.
   - Expected gain: `1-3s`.

3. **Do not reduce gamescrate dwell below `4s` in production yet.**
   - `4s` is proven in this run and prior batch 2.
   - Any `0-3s` dwell attempt should remain an env-only ladder with at least two final-oracle successes before promotion.

4. **Do not use headless XUT timing as a success basis.**
   - Headless got stuck at gamescrate Cloudflare/security verification and failed final oracle.

## Parent checklist status

- [done] Read current XUT implementation and optimization workframe.
- [done] Profile non-production instrumented run without editing production code.
- [done] Capture successful phase timings for Step 1 IconCaptcha, gamescrate dwell, and Step 6 wait.
- [done] Save report and raw evidence under `artifacts/active/total-optimization/`.
- [pending] Main agent decides whether to patch Step 1 polling and post-gamescrate polling next.
