# 2026-04-28 Expansion Workframe

## Objective
Close as many remaining `/bypass` families as possible without adding per-family bot commands. Priority set: `oii.la`, `tpi.li`, `aii.sh`, `xut.io`, `cuty.io`, `gplinks.co`, `sfl.gl`, `exe.io`.

## Success oracle
A family can be promoted to `live_bypass` only when `engine.py <sample> --pretty` returns `status=1` and `bypass_url` equals the captured downstream oracle or a directly equivalent final URL.

## Known status before work
- `oii.la`, `tpi.li`, `aii.sh`: token extraction returns final candidate, but full live gate is not proven.
- `xut.io`: current bot failure shows `xut_live_browser.py` cannot import `dtos`; older notes show later gamescrate Cloudflare gate remains hard.
- `cuty.io`: current bot can fail with `ERROR_CAPTCHA_UNSOLVABLE`.
- `gplinks.co`: PowerGam mapped, but final blocked by `not_enough_steps` / missing ad impression contract.
- `sfl.gl`: current bot failure says `ENTRY_FORM_NOT_FOUND`; old handler may be stale.
- `exe.io`: no handler yet.

## Parent checklist
- [done] 1. Reproduce each current blocker with raw engine output.
- [in progress] 2. Fix cheap deterministic failures first, especially env/import and stale parser issues.
- [done] 3. Run targeted live probes for remaining protocol boundaries.
- [done] 4. Patch handlers with tests.
- [in progress] 5. Promote only families with verified final oracle.
- [pending] 6. Deploy, push project repo, then sync MyAiAgent.

## Boundary catalog
- Token-tail final-candidate boundary: `oii.la`, `tpi.li`, `aii.sh`, status narrowed but live-gate open.
- Helper import/runtime boundary: `xut_live_browser.py -> dtos`, status primary immediate blocker.
- Turnstile solver boundary: `cuty.io`, status flaky/primary.
- Ad impression/conversion boundary: `gplinks.co`, status primary open.
- Entry form/API contract boundary: `sfl.gl`, status stale/open.
- Unknown entry chain boundary: `exe.io`, status open.

## 2026-04-28 progress
- Raw baseline reproduced all target outputs.
- `exe.io` patched from unsupported to honest `EXE_GATE_MAPPED`.
- `sfl.gl` patched to report `CLOUDFLARE_BLOCKED` when entry page is Cloudflare access denied.
- `oii.la`, `tpi.li`, `aii.sh` registry status refined to `token_bypass`, not full `live_bypass`.
- `cuty.io` rerun showed one CDP startup failure and one solver `ERROR_CAPTCHA_UNSOLVABLE`; keep partial.

## Verification snapshot
- Unit tests: `31/31 OK`.
- Live token samples: `oii.la`, `tpi.li`, `aii.sh` all return `TOKEN_TARGET_EXTRACTED` and expected URLs.
- `sfl.gl` now returns `CLOUDFLARE_BLOCKED` with the current VPS egress.
- `exe.io` now returns `EXE_GATE_MAPPED` with Turnstile sitekey/timer, no false final claim.
- `cuty.io` helper now uses dynamic CDP port and returns solver error with timeline; current live blocker remains `ERROR_CAPTCHA_UNSOLVABLE`.
