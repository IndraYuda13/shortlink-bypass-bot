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
