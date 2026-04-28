# GPLinks batch 3 timing profile

Target: `https://gplinks.co/YVTC`  
Expected final oracle: `http://tesskibidixxx.com/`  
Scope: profiling only. Production code was not edited.

## Parent checklist

- [done] Read `gplinks_live_browser.py` and current total-optimization workframe.
- [done] Collect live timing evidence for the latest optimized GPLinks path.
- [done] Break timing down by phase.
- [done] Identify biggest remaining waits and safe cuts.
- [done] Save this report.

## Evidence files

- Successful instrumented run: `artifacts/active/total-optimization/gplinks-batch3-profile-selenium-raw.json`
- Successful run log: `artifacts/active/total-optimization/gplinks-batch3-profile-selenium-run.log`
- UC failure evidence: `artifacts/active/total-optimization/gplinks-batch3-profile-run.log`, `artifacts/active/total-optimization/gplinks-batch3-profile-run2.log`, `artifacts/active/total-optimization/gplinks-live-plain-run.json`, `artifacts/active/total-optimization/gplinks-live-plain-run.time`
- Workframe read: `artifacts/active/2026-04-28-total-optimization-workframe.md`

## Important caveat

The production helper currently uses `undetected_chromedriver`. During this profiling pass, UC session creation or later ChromeDriver calls repeatedly failed with:

```text
('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
```

A raw Selenium smoke test using the same Chrome/ChromeDriver binary succeeded, so I used a profiling harness that imports `gplinks_live_browser.py` and monkeypatches only `build_driver()` to plain Selenium. That means the phase timing is a close live profile of the current GPLinks logic, but browser startup time is not UC production startup time. The actual optimized production benchmark from the workframe is still `148.6s`; this profile run measured `151.3s` and hit the same final URL oracle.

## Result oracle

Successful profiled run:

- `status=1`
- `stage=live-browser-final-gate`
- `bypass_url=http://tesskibidixxx.com/`
- `final_url=http://tesskibidixxx.com/`
- `token_used=true`
- `sitekey=0x4AAAAAAAynCEcs0RV-UleY`
- measured helper time: `151.3s`

The browser could not DNS-resolve `tesskibidixxx.com` after navigating to it, but the GPLinks page had already exposed `#captchaButton.href = http://tesskibidixxx.com/`. The helper correctly treats that as the final URL oracle.

## Phase timing breakdown

Measured from `gplinks-batch3-profile-selenium-raw.json`.

| Phase | Start | End | Duration | Notes |
|---|---:|---:|---:|---|
| curl_cffi entry request | `0.000s` | `0.561s` | `0.561s` | Gets PowerGam redirect before browser launch. |
| Browser build | `0.561s` | `1.398s` | `0.838s` | Plain Selenium profile only. UC production currently failed in this environment. |
| Browser navigation to PowerGam | `1.398s` | `3.501s` | `2.103s` | `driver.get(url)` landed on `https://powergam.online/`. |
| Initial PowerGam DOM ready | `3.501s` | `3.534s` | `0.115s` | State already usable. |
| PowerGam step 1 | `3.572s` | `34.767s` | `31.195s` | Verify clicked immediately, then countdown/continue wait. |
| PowerGam step 2 | `34.909s` | `66.700s` | `31.791s` | Same pattern. |
| PowerGam step 3 | `66.786s` | `99.033s` | `32.247s` | Same pattern, then lands on GPLinks candidate. |
| GPLinks candidate page ready | `99.043s` | `99.515s` | `0.482s` | Candidate URL had `pid` and `vid`; sitekey present. |
| Cloudflare wait/check | `99.615s` | `99.665s` | `0.050s` | No visible CF interstitial. |
| Turnstile solve | `99.874s` | `149.947s` | `50.073s` | Largest single non-PowerGam wait. |
| Final form submit and href extraction | `149.947s` | `151.284s` | `1.337s` | `final_href=http://tesskibidixxx.com/`. |
| Total helper run | `0.000s` | `151.410s` | `151.410s` | Helper returned `waited_seconds=151.3`. |

Grouped view:

- PowerGam 3-step ledger: about `95.2s` to `96.1s` depending on exact boundary.
- Turnstile final gate: `51.6s`, mostly solver time.
- Browser/curl/navigation/non-wait overhead: about `4s` to `5s`.

## Biggest remaining waits

1. **PowerGam timers: ~95s**
   - Each of the 3 PowerGam steps took about `31-32s` even though the visible wait value starts at `15`.
   - This is the biggest total block.
   - The current loop sleeps `min(waitLeft + 0.5, 9.0)` and polls repeatedly: `15 -> 11 -> 6 -> 3 -> 1 -> 1 -> 0`.
   - The slow visible countdown suggests browser timer throttling or page-side timer scaling. It should be profiled before assuming the server truly requires 30s per step.

2. **Turnstile solver: 50.073s**
   - Final gate itself is fast once token arrives.
   - Skipping Turnstile is not safe. Prior JS/live evidence says final `/links/go` needs the token/callback.
   - Optimization should target solver latency, not removal.

3. **Final navigation after final href: up to 5s in code**
   - `unlock_final_gate()` navigates to `final_href` and sleeps `5s` after `driver.get(final_href)`.
   - In this run DNS failed quickly, so the full 5s was not paid.
   - The final URL is already known before navigation from `#captchaButton.href`.

4. **UC startup instability**
   - This is not a speed optimization, but it affects production reliability and profiling repeatability.
   - Plain Selenium starts in under `1s`; UC failed with `RemoteDisconnected` in the current environment.

## Safe cuts / next experiments

### 1. Add Chrome anti-throttle flags to GPLinks browser helper

Recommended first experiment:

- `--disable-background-timer-throttling`
- `--disable-renderer-backgrounding`
- `--disable-backgrounding-occluded-windows`
- optionally `--disable-hang-monitor`

Reason: PowerGam visible timer decreases much slower than wall-clock 1 second per tick. If Chrome throttling is involved, these flags could reduce the `~95s` PowerGam block without bypassing the ledger or weakening the final oracle.

Verification needed:

- Run `gplinks_live_browser.py https://gplinks.co/YVTC --timeout 300`.
- Required oracle: `status=1`, `bypass_url=http://tesskibidixxx.com/`.
- Compare PowerGam step durations, not just total wall time.

### 2. Replace coarse PowerGam sleep with a tighter wait for `Continue` clickability

Current loop pays repeated coarse sleeps and sometimes repeats `waitLeft=1`.

Safer cut:

- If `waitLeft > 2`, sleep less aggressively but poll based on DOM change.
- If `waitLeft <= 2`, poll every `0.2-0.3s` for text/body/button state instead of sleeping `1.5s` and rechecking late.
- Click only when `waitLeft <= 0` or the Continue state is visibly ready.

Expected saving: small by itself, probably `2-6s` total. Bigger if combined with anti-throttle flags.

### 3. Skip final navigation to `final_href` after href extraction

Current final oracle can be satisfied when `#captchaButton.href` is a non-GPLinks, non-PowerGam, non-link-error URL.

Safe implementation shape:

- In `unlock_final_gate()`, after `final_href` is found, return it without `driver.get(final_href)` by default.
- Keep a debug env flag for old behavior, e.g. `SHORTLINK_BYPASS_GPLINKS_NAVIGATE_FINAL=1`.

Expected saving: up to `5s` where DNS/network does not fail immediately.

Risk: low, because the helper already returns `button_url` as success if `is_final_url(button_url)`.

### 4. Improve Turnstile solver latency, do not remove it

Safe directions:

- Check solver server health and whether requests queue on port `5000`.
- Keep solver browser warm.
- Increase solver worker capacity only if resource use is safe.
- Add timing telemetry around `solve_turnstile()` in production diagnostics.

Expected saving: variable. This run spent `50.073s` just waiting for the token.

### 5. Fix or isolate UC instability before relying on production live timing

Evidence:

- UC build/session failed with `RemoteDisconnected`.
- Plain Selenium smoke succeeded with the same ChromeDriver binary.

Suggested next diagnostic, not a production patch yet:

- Run a minimal UC smoke under `xvfb-run` with verbose ChromeDriver logs.
- Check whether many stale Chrome/ChromeDriver processes or UC patcher races are causing session death.
- If UC remains unstable and plain Selenium still passes GPLinks, consider env-guarded driver mode for GPLinks only.

## What should not be cut yet

- Do not remove the PowerGam 3-step path. It is still the ledger-producing path.
- Do not promote direct PowerGam start. Batch 2 flag run timed out and did not reach the final candidate.
- Do not skip Turnstile or fake the final gate. Final URL appears only after token/callback/form submit.
- Do not treat `gplinks.co/YVTC?pid=...&vid=...` as success. It is only the candidate before final gate.

## Recommendation order

1. Add anti-throttle Chrome flags and rerun the same timing profile.
2. Tighten the `waitLeft <= 2` polling behavior.
3. Skip final navigation after `final_href` is extracted.
4. Add permanent phase telemetry around PowerGam steps and Turnstile solve.
5. Separately investigate UC `RemoteDisconnected`; do not mix that with the timing patch unless it blocks live verification.
