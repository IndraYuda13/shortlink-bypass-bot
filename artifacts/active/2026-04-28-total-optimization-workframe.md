# 2026-04-28 Total shortlink optimization workframe

## Objective
Bedah semua supported shortlink family untuk mencari step yang bisa dipotong tanpa menurunkan success oracle. Fokus bukan hanya support, tapi speed: ukur baseline vs after dalam detik, persen lebih cepat, dan speedup kali.

## Success oracle
Sebuah upgrade hanya boleh dianggap berhasil kalau:
- `engine.py <sample> --pretty` tetap `status=1`
- final URL tetap downstream expected atau equivalent
- waktu lebih cepat secara live measurement
- browser fallback tetap ada untuk lane yang belum general/live-proven

## Hard constraints
- Tetap satu command: `/bypass`.
- Jangan naikkan klaim status tanpa live final oracle.
- Untuk HTTP/hybrid fast lane, fallback browser tetap hidup kecuali HTTP lane sudah terbukti live.
- Catat skipped step dan bukti kenapa step itu aman dipotong.

## Parent checklist
- [in progress] 1. Baseline timing matrix semua sample.
- [pending] 2. Research independent family lanes: GPLinks, XUT, token family, existing fast families.
- [pending] 3. Implement hanya skip lane yang live-proven.
- [pending] 4. Re-run timing matrix dan hitung delta.
- [pending] 5. Update docs, tests, deploy, push, sync.

## Candidate lanes
- GPLinks: browser works, HTTP preflight fails `not_enough_steps`; likely GPT/PowerGam ledger. Look for skip/shortcut around final button or cached page state.
- XUT: browser works, simple HTTP->browser hybrid failed at gamescrate `Forbidden`; look for browser-start-later/earlier or direct Step 6 shortcut.
- Token family (`oii.la`, `tpi.li`, `aii.sh`): token extraction works; test whether final gate can be skipped entirely or whether live final can be proven cheaply.
- Existing fast families: adlink, shrinkme, ez4short, lnbz, sfl, exe, cuty; verify if any timers/ad calls can be shortened safely.

## 2026-04-28 first implementation batch
- Parent checklist status:
  - [done] 1. Baseline timing matrix semua sample.
  - [done] 2. Research independent family lanes: GPLinks, XUT, token family, existing fast families.
  - [in progress] 3. Implement hanya skip lane yang live-proven.
  - [in progress] 4. Re-run timing matrix dan hitung delta.
  - [pending] 5. Update docs, tests, deploy, push, sync.

### Baseline snapshots
- Fast/token matrix saved: `artifacts/active/total-optimization/current-fast-token-baseline.jsonl`.
- Browser-heavy baseline saved: `artifacts/active/total-optimization/current-browser-baseline.jsonl`.
- Baselines observed:
  - `gplinks.co/YVTC`: `183.3s` wall, final `http://tesskibidixxx.com/`.
  - `xut.io/hd7AOJ`: `187.0s` wall, final `http://tesskibidixxx.com/`.
  - `cuty.io/AfaX6jx`: `73.9s` in baseline matrix, already HTTP-fast/no-VHit lane after earlier work.
  - `exe.io/vkRI1`: `72.2s`, already HTTP-fast.
  - token family: `oii/tpi/aii` are already ~`0.9-1.8s` token extraction lanes.

### Implemented skip lanes
- GPLinks:
  - Default now skips `gplinks_http_fast.py` preflight because it always fast-fails with `not_enough_steps` and costs about `2.4s`.
  - `SHORTLINK_BYPASS_GPLINKS_HTTP_FAST=1` can re-enable it for research.
  - Replaced several fixed waits in `gplinks_live_browser.py` with DOM/Cloudflare/state polling.
  - Live after: `148.6s`, final `http://tesskibidixxx.com/`, `http_fast_stage=http-fast-skipped`.
  - Improvement vs local baseline `183.3s`: saved `34.7s`, `18.9%` faster, `1.23x` speedup.
- XUT:
  - Default now treats visible exact `Get Link` href as final oracle and skips the click/navigation wait.
  - `SHORTLINK_BYPASS_XUT_CLICK_FINAL=1` can restore the old click behavior.
  - Gamescrate dwell is env-tunable via `SHORTLINK_BYPASS_XUT_GAMESCRATE_DWELL`, default `8s`.
  - Live after: `181.21s`, final `http://tesskibidixxx.com/`, `get_link_clicked.skipped=true`.
  - Improvement vs local baseline `187.0s`: saved `5.8s`, `3.1%` faster, `1.03x` speedup.

### Research decisions
- Token family stays `token_bypass`: current extraction is already the fastest useful lane for returning final URL; live Turnstile/timer gate is not proven and would be slower.
- XUT simple HTTP hybrid remains rejected because gamescrate signed token rejects browser context switch with `Forbidden`.

## 2026-04-28 batch 2 follow-up
- Parent checklist status:
  - [done] 1. Probe GPLinks timing bottleneck with current optimized lane.
  - [done] 2. Try smaller GPLinks wait values under env/tunable guard.
  - [done] 3. Probe XUT gamescrate dwell values under env/tunable guard.
  - [in progress] 4. Implement only values that keep final oracle live.
  - [in progress] 5. Run focused tests + full tests.
  - [pending] 6. Live before/after timing table, restart service, commit/push, sync.

### XUT dwell probe
- `SHORTLINK_BYPASS_XUT_GAMESCRATE_DWELL=4`: final `http://tesskibidixxx.com/`, wall `101.63s`.
- `SHORTLINK_BYPASS_XUT_GAMESCRATE_DWELL=6`: final `http://tesskibidixxx.com/`, wall `153.80s`.
- Default changed to `4s` because it preserved the final oracle and was much faster in the live probe.
- Post-default verification: final `http://tesskibidixxx.com/`, wall `97.10s`.
- Compared with batch-1 baseline `181.21s`, this saves `84.11s`, `46.4%` faster, `1.87x` speedup.
- Compared with original total-optimization baseline `187.0s`, this saves `89.9s`, `48.1%` faster, `1.93x` speedup.

### GPLinks direct-PowerGam probe
- Added experimental `SHORTLINK_BYPASS_GPLINKS_DIRECT_POWERGAM=1` path that imports GPLinks cookies and opens PowerGam directly.
- Live probe with flag failed: wall `305.61s`, engine fell back to static mapper, live helper stage `powergam`, message `POWERGAM_FINAL_CANDIDATE_TIMEOUT`.
- Decision: keep the direct-PowerGam path off by default. Do not promote it as an optimization.

## 2026-04-28 batch 3 start
- Parent checklist status:
  - [in progress] 1. Add/collect timing telemetry for GPLinks, XUT, and Turnstile solver.
  - [pending] 2. Identify biggest proven removable waits.
  - [pending] 3. Patch only low-risk timing cuts or env-guarded experiments.
  - [pending] 4. Run focused and full tests.
  - [pending] 5. Run live timing verification.
  - [pending] 6. Update docs/artifacts, restart service, commit/push, sync.
- User approved continuing after batch 2.
- Focus: profile before cutting more.

### XUT batch 3 profile
- Report saved: `artifacts/active/total-optimization/xut-batch3-profile.md`.
- Raw success evidence: `artifacts/active/total-optimization/xut-batch3-profile-raw-4.json`.
- Production code was not edited by the profiling subtask.
- Live oracle preserved: `status=1`, final `http://tesskibidixxx.com/`, wall `98.243s`, default dwell observed `4.0s`.
- Phase timing: Chrome launch `0.895s`, initial get `3.945s`, Step 1 IconCaptcha -> Step 2 `46.126s` with 1 attempt and solver API `4.671s`, Steps 2-4 -> gamescrate `23.270s`, gamescrate Open Final wait `10.193s`, dwell `4.000s`, open-final click + post wait `3.291s`, Step 6 final href wait `6.085s`.
- Safe next cuts: remaining Step 1 fixed sleeps (`4s` canvas wait + `6s` post-click wait) -> DOM/state polling first; replace fixed `3s` post-gamescrate click wait with immediate Step 6 polling second; do not promote dwell below `4s` without a separate env-only ladder and repeated final-oracle proof.
- Invalid probe note: headless reached gamescrate but failed final oracle by sticking on Cloudflare/security verification, so do not use headless as XUT timing basis.

## 2026-04-28 batch 3 implementation result
- Parent checklist status:
  - [done] 1. Add/collect timing telemetry for GPLinks, XUT, and Turnstile solver.
  - [done] 2. Identify biggest proven removable waits.
  - [done] 3. Patch only low-risk timing cuts or env-guarded experiments.
  - [done] 4. Run focused and full tests.
  - [done] 5. Run live timing verification.
  - [in progress] 6. Update docs/artifacts, restart service, commit/push, sync.

### Turnstile polling
- Turnstile profile showed task creation is cheap (`0.016-0.039s`) and browser challenge dominates (`48-54s`).
- Changed `solve_turnstile()` poll interval default from `5s` to `2s`, tunable with `SHORTLINK_BYPASS_TURNSTILE_POLL_INTERVAL`.
- Live after:
  - `cuty.io/AfaX6jx`: `76.17s`, final `https://www.google.com/`.
  - `exe.io/vkRI1`: `65.98s`, final `https://www.google.com/?gws_rd=ssl`.
- Interpretation: exe improved vs baseline `72.2s`; cuty did not improve on this single run because solver challenge time variance dominated.

### XUT IconCaptcha API + Step 1 rollback note
- Switched XUT IconCaptcha API default to standalone `http://127.0.0.1:8091/solve`, while keeping fallback to local Python solver.
- Normalized standalone API fields (`x/y/position`) into legacy fields (`click_x/click_y/selected_cell_number`) for compatibility.
- Tried replacing Step 1 fixed sleeps with polling, but live verification failed with canvas lookup exceptions / `ICONCAPTCHA_STEP1_FAILED`; that risky change was rolled back.
- Stable live after rollback and API normalization: `108.55s`, final `http://tesskibidixxx.com/`, provider `api`, Step 1 passed on attempt `2`.
- This is slightly slower than the best batch-2 `97.10s` because this run needed 2 IconCaptcha attempts. The API switch is a reliability/maintenance improvement, not a proven speed win yet.

### GPLinks batch3 profile + patch
- Profile reported total `151.3s`: PowerGam ledger `~95-96s`, Turnstile solve `50.07s`, final submit/href `1.34s`.
- Added anti-throttle Chrome flags and `SHORTLINK_BYPASS_GPLINKS_NAVIGATE_FINAL=1` opt-in for old final navigation behavior; default skips navigation after valid final href.
- Live after patch: `150.21s`, final `http://tesskibidixxx.com/`, effectively same as batch-1/2 optimized GPLinks. No major GPLinks speed win from anti-throttle on this run.
