# 2026-04-29 GPLinks PowerGam ledger case note

Target: `https://gplinks.co/YVTC` -> expected `http://tesskibidixxx.com/`

## Proven

- Current browser helper still reaches final oracle in this environment:
  - artifact: `artifacts/active/batch4-breakthrough/gplinks-live-current-run.json`
  - result: `status=1`, `stage=live-browser-final-gate`, `final_url=http://tesskibidixxx.com/`, `waited_seconds=150.1`, `token_used=true`.
- The final GPLinks page exposes the downstream URL only after the in-page Turnstile completion / `/links/go` path:
  - before unlock: `#captchaButton` is disabled with `href=javascript: void(0)`.
  - after Turnstile token + page submit: `#captchaButton` becomes `Get Link` with `href=http://tesskibidixxx.com/`.
- The live final page form has action `/links/go`, hidden `_csrfToken`, hidden `cf-turnstile-response`, and encrypted `ad_form_data`/token fields inside the form data captured in the helper state.
- Browser PowerGam steps can reach `https://gplinks.co/YVTC?pid=1224622&vid=<raw_vid>` and get a 200 final-gate page. The resulting final page includes Tracki click URLs with decoded `vid` and `pid`, but the decisive unlock remains the GPLinks Turnstile + form submission.

## Falsified / narrowed

- Pure visible PowerGam form replay is not sufficient.
- Raw encoded `vid` is the correct browser-like `visitor_id`, but using it does not satisfy the server ledger by itself.
- A bounded real-delay HTTP probe with `16.2s` before each of the three form posts still ended in:
  - `302 https://gplinks.co/link-error?alias=YVTC&error_code=not_enough_steps`
  - artifact: `artifacts/active/batch4-breakthrough/gplinks-delay16-imps0.json`
- Therefore the missing proof is not just elapsed wall time between PowerGam submits.
- Prior probes already falsified Tracki pop/banner impressions and `gplinks.com/track/data.php addConversion` as standalone replacements.

## Current boundary catalog

- Entry/session gate: narrowed. `gplinks.co/YVTC` returns PowerGam redirect with `AppSession`, `csrfToken`, `lid`, `pid`, `vid`, `pages`.
- PowerGam visible step boundary: narrowed/falsified as sufficient. Browser clicks work, HTTP form posts alone do not.
- PowerGam hidden browser activity boundary: primary open. The difference between browser success and HTTP failure is likely resource/JS/browser-bound state around PowerGam, not the visible form payload or timer.
- GPLinks final gate: closed for browser lane. Requires Turnstile token and page's own `/links/go` submission; success oracle is downstream href from `#captchaButton`.
- Pure HTTP final candidate: blocked. HTTP candidate still gets `not_enough_steps` before final page HTML is served.

## Do not repeat

- Do not retry immediate or delayed raw `adsForm` POSTs as if delay alone will solve it.
- Do not mark `https://gplinks.co/YVTC?pid=...&vid=...` as success. It is only a candidate and may be rejected by server ledger.
- Do not trust synthetic `imps`, `adexp`, or Tracki calls as ledger proof without downstream final oracle.

## Next best action

Use a browser-to-HTTP extraction probe, not another pure HTTP replay:

1. In a live browser run, capture all PowerGam and final GPLinks cookies/localStorage/sessionStorage immediately after each successful native submit and at the final candidate page.
2. Capture CDP request/response headers for the three native PowerGam POSTs and the final `GET /YVTC?pid=...&vid=...`.
3. Compare those against `gplinks-delay16-imps0.json` to find the exact missing browser-bound request/header/storage/resource side effect.
4. If a minimal transferable state is found, patch an env-guarded hybrid lane: browser only for PowerGam ledger, then HTTP for final Turnstile `/links/go` if cookies and CSRF can be transferred. Otherwise keep current live-browser lane.

## 2026-04-30 browser vs HTTP diff update

Fresh diff artifact: `artifacts/active/2026-04-30-gplinks-browser-http-diff.md`.

New evidence:

- Browser CDP capture reached candidate `https://gplinks.co/YVTC?pid=1224622&vid=MTAyMDAwODIyNg` with `200 text/html`.
- Browser native PowerGam posts are root-action posts to `https://powergam.online/`, with raw encoded `visitor_id`, `step_count=1/2/3` in cookies, and `ad_impressions=0`.
- Focused HTTP root-action replay with 16.2s waits still returned `not_enough_steps`.
- Additional HTTP tests also failed: final `Origin` header, redirect-chain follow, domain vs host-only cookies, and fake GA/FCCDCF/FCNEC cookies.

Updated narrowed root cause:

- The blocker is no longer likely to be visible form endpoint, payload, raw vid, simple cookies, final Origin header, or timing.
- Remaining concrete delta is browser/Cloudflare navigation context around PowerGam, especially Chrome transport context and same-origin `POST /cdn-cgi/rum?` Browser Insights beacons after each PowerGam page load.
- Next best HTTP-only experiment is a controlled RUM replay around each PowerGam step. Success oracle remains strict: candidate GET must become `200` final gate, not `302 not_enough_steps`.

### RUM replay result

Synthetic `POST https://powergam.online/cdn-cgi/rum?` after PowerGam page loads returned `204` but final candidate still returned `not_enough_steps` (`artifacts/active/gplinks-rum-replay-test.json`). Treat RUM as falsified as a standalone ledger proof. The remaining delta is full browser transport/runtime context or another browser-only side effect not yet isolated to one replayable endpoint.

### 2026-04-30 final handoff and HTTP/3 probes

- Added env-gated `SHORTLINK_BYPASS_GPLINKS_HTTP_FINAL_HANDOFF=1` browser-to-HTTP final handoff in `gplinks_live_browser.py`.
- Live artifact `artifacts/active/gplinks-hybrid-http-final-live.json`: browser reached the accepted final page, HTTP `/links/go` returned `Bad Request.`, then browser fallback still reached `http://tesskibidixxx.com/`.
- The handoff is disabled by default because it slows the proven lane and is not yet successful.
- Artifact `artifacts/active/gplinks-h3-replay-test.json`: curl_cffi `CurlHttpVersion.V3` replay still returned `not_enough_steps`, so HTTP/3 alone is falsified as the missing PowerGam ledger proof.
