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
- [done] 2. Fix cheap deterministic failures first, especially env/import and stale parser issues.
- [done] 3. Run targeted live probes for remaining protocol boundaries.
- [done] 4. Patch handlers with tests.
- [in progress] 5. Promote only families with verified final oracle.
- [in progress] 6. Deploy, push project repo, then sync MyAiAgent.

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

## Shared blocker phase progress
- Restored FlareSolverr source tree and verified `xut_live_browser` imports.
- Updated Chrome to `147.0.7727.116` and pinned xut helper to installed Chrome major.
- Added local Python IconCaptcha fallback after API hub route returned 404.
- Live xut reached gamescrate Cloudflare once with Step 1 solved by local-python provider, but repeatability is not stable yet.
- WARP proxy fallback made `sfl.gl/18PZXXI9` live again: `SFL_API_FLOW_OK -> https://google.com`.
- Turnstile solver benchmark for cuty/exe still fails with `ERROR_CAPTCHA_UNSOLVABLE`.

## Final smoke after shared blocker phase
- `sfl.gl/18PZXXI9`: `status=1`, `SFL_API_FLOW_OK`, final `https://google.com`.
- `xut.io/hd7AOJ`: current repeat `ICONCAPTCHA_STEP1_FAILED`; previous run reached `GAMESCRATE_HANDOFF_PROGRESS_ONLY`. Treat as partial/flaky, not working.
- `cuty.io/AfaX6jx`: still `TURNSTILE_SOLVER_FAILED` / `ERROR_CAPTCHA_UNSOLVABLE`.

## 2026-04-28 cuty HTTP speed milestone
- Parent checklist status:
  - [done] 1. Reproduce each current blocker with raw engine output.
  - [done] 2. Fix cheap deterministic failures first, especially env/import and stale parser issues.
  - [done] 3. Run targeted live probes for remaining protocol boundaries.
  - [done] 4. Patch handlers with tests.
  - [done] 5. Promote only families with verified final oracle.
  - [in progress] 6. Deploy, push project repo, then sync MyAiAgent.
- `cuty.io/AfaX6jx` is now HTTP-first.
- Live helper oracle: `cuty_http_fast.py https://cuty.io/AfaX6jx -> https://www.google.com/` in `70.2s`.
- Live engine oracle: `CUTY_HTTP_FAST_OK -> https://www.google.com/` in `74.5s`.
- Root-cause correction: the previous HTTP bounce was not a permanent VHit-only blocker. Browser-shaped HTTP replay with `Origin: null`, HeadlessChrome-style UA, final wait, and best-effort VHit fetches can clear `/go/AfaX6jx`.
- Browser fallback remains wired because production success is only promoted when the HTTP helper returns a downstream final URL.

## 2026-04-28 cuty VHit ablation update
- Parent checklist status:
  - [done] 1. Re-read Cuty artifacts/state.
  - [done] 2. Run VHit ablation proof.
  - [in progress] 3. Update boundary note.
  - [pending] 4. Decide code change or no-op.
  - [pending] 5. Verify and report.
- Fresh ablation command: `artifacts/active/cuty_http_vhit_replay_probe.py https://cuty.io/AfaX6jx --no-vhit`.
- Result: final `https://www.google.com/` in `69.9s`.
- Meaning: for the current sample, `fp.vhit.io` and `vhit.io/api/request` are observed in the browser lane but are not required for the server to accept `/go/AfaX6jx`.
- Production decision: make VHit replay opt-in via `SHORTLINK_BYPASS_CUTY_HTTP_VHIT=1`; default skip is faster and avoids dependency on external VHit endpoints. Keep opt-in available for future Cuty variants.
