# 2026-04-30 GPLinks browser vs HTTP ledger diff

Target: `https://gplinks.co/YVTC`
Expected final oracle: `http://tesskibidixxx.com/`

## Active question

Find the real delta between browser success and HTTP failure for the PowerGam ledger, then decide whether the delta can be fixed in HTTP-core.

## Browser success proof

Fresh CDP diff probe artifact:

- `artifacts/active/gplinks-cdp-diff-latest.json`
- candidate reached: `https://gplinks.co/YVTC?pid=1224622&vid=MTAyMDAwODIyNg`
- candidate response in browser: `200 text/html`, not `link-error`

Relevant browser native requests:

```text
POST https://powergam.online/
body form_name=ads-track-data&step_id=1&ad_impressions=0&visitor_id=<raw_vid>&next_target=https://powergam.online
Cookie includes lid/pid/pages/vid/imps/step_count=1 plus analytics/ad cookies
-> redirected internally to GET https://powergam.online/ -> 200

POST https://powergam.online/
body step_id=2 ... next_target=https://powergam.online
Cookie includes step_count=2
-> redirected internally to GET https://powergam.online/ -> 200

POST https://powergam.online/
body step_id=3 ... next_target=https://gplinks.co/YVTC?pid=1224622&vid=<raw_vid>
Cookie includes step_count=3
-> redirected internally to GET https://gplinks.co/YVTC?pid=1224622&vid=<raw_vid>
GET candidate Cookie only sends GPLinks AppSession/csrfToken
-> 200 final gate HTML
```

## HTTP failure proof

Current HTTP helper and focused replays still fail:

- `gplinks_http_fast.py https://gplinks.co/YVTC`: `HTTP_FAST_POWERGAM_LEDGER_REJECTED`, `not_enough_steps`, about `2.86s`.
- Root-action replay with realistic browser-like 16.2s waits still fails:
  - `artifacts/active/gplinks-root-replay-test.json`
  - posts to `https://powergam.online/`, not query URL
  - final candidate still returns `302 /link-error?error_code=not_enough_steps`
- Additional focused tests also failed:
  - final candidate GET with `Origin: https://powergam.online`
  - final post followed as one redirect chain with `allow_redirects=True`
  - domain cookies vs host-only cookies vs both
  - fake analytics/ad cookies (`_ga`, `_ga_*`, `FCCDCF`, `FCNEC`)

## Deltas that are now falsified as sole cause

- Wrong form endpoint: falsified. HTTP root POST still fails.
- Missing raw `vid`: falsified. HTTP uses raw encoded `vid`.
- Missing timer: falsified. 16.2s per step still fails.
- Missing `Origin` on final candidate: falsified.
- Manual follow vs redirect-chain follow: falsified.
- Cookie domain/host-only mismatch: falsified.
- Absence of simple analytics/ad cookies: falsified.

## Remaining real delta

At the application payload level, browser and HTTP are now very close:

- same `POST https://powergam.online/`
- same form payload shape
- same raw `visitor_id`
- same `step_count` progression
- same final target URL
- same GPLinks AppSession/csrfToken on final candidate GET

But browser succeeds and curl_cffi HTTP fails. The remaining observed differences are below the visible app payload:

1. **Real Chrome network stack / Cloudflare edge context**
   - Browser responses advertise/use Cloudflare with `alt-svc: h3=":443"`.
   - Native Chrome can use HTTP/3/QUIC and full browser TLS/client hints behavior.
   - curl_cffi impersonation is close, but it is not the same full Chrome navigation context.

2. **Same-origin Cloudflare Browser Insights beacons**
   - Browser sends `POST https://powergam.online/cdn-cgi/rum?` after each PowerGam page load.
   - Payload includes Cloudflare `siteToken=1c9fa54710914287892298884cfcb9dc`, page timing, navigation id, memory fields, and location/referrer.
   - HTTP lane does not currently replay this. This is a plausible Cloudflare/browser-context signal, although it may be edge-only rather than app-visible.

3. **Browser-only external ad/analytics sequence**
   - Browser loads Tracki banners, GA, DoubleClick partner pixels, PubNotify CORS, and Google ad conversion endpoints between steps.
   - Prior tests showed Tracki pop/banner alone is not sufficient, and fake analytics cookies are not enough.
   - These may still contribute to edge/browser score, but they are unlikely to be a single app-server endpoint.

## Current root-cause status

Root cause is narrowed but not fully closed:

> The PowerGam/GPLinks ledger is not satisfied by visible form payload, cookies, target URL, or timing alone. The accepting condition appears tied to a real browser/Cloudflare navigation context around the PowerGam POST redirects. The strongest concrete missing HTTP-side candidate is the same-origin Cloudflare RUM/browser telemetry plus full Chrome transport fingerprint, not final Turnstile.

This is not a final impossible claim. It is the current evidence-backed boundary.

## Fixability assessment

Likely fixable, but not by only tweaking visible form fields.

Most promising next experiments:

1. **Replay Cloudflare RUM around each PowerGam page load**
   - Add a controlled HTTP experiment that sends `/cdn-cgi/rum?` payloads before each step using the same location/referrer pattern as Chrome.
   - Oracle: candidate GET changes from `302 not_enough_steps` to `200 final gate`.

2. **Use Chrome/CDP only as a ledger-token extractor, then HTTP for final**
   - This is not pure HTTP, but can immediately reduce browser scope.
   - Browser stops at accepted candidate page, exports AppSession/csrfToken + final form hidden fields, then HTTP core does Turnstile prewarm + `/links/go`.

3. **Investigate true HTTP/3/QUIC client lane**
   - If RUM replay fails, test whether the ledger acceptance depends on Chrome/HTTP3/Cloudflare bot score.
   - This would require an HTTP/3-capable client or a Chrome network-service harness rather than plain requests/curl_cffi.

## Top-level checklist

- HTTP-core Turnstile prewarm: done.
- Browser vs HTTP request diff capture: done.
- Visible form/root-action/timing/header/cookie hypotheses: falsified as sole cause.
- RUM replay hypothesis: pending.
- Full HTTP-only production replacement: pending, not yet verified.

## RUM replay test

Artifact: `artifacts/active/gplinks-rum-replay-test.json`.

Result:

```text
POST https://powergam.online/cdn-cgi/rum? -> 204 after root page load
POST https://powergam.online/cdn-cgi/rum? -> 204 after step 1 follow
POST https://powergam.online/cdn-cgi/rum? -> 204 after step 2 follow
final candidate -> 302 https://gplinks.co/link-error?alias=YVTC&error_code=not_enough_steps
```

Interpretation:

- A synthetic Cloudflare RUM beacon is accepted by the endpoint (`204`) but does **not** satisfy the PowerGam ledger by itself.
- RUM remains possible as one part of browser context, but not as a standalone visible fix.
- Remaining strongest delta after this test is full browser transport/runtime context, not a single simple endpoint replay.

Updated next best action:

1. Try a true browser-to-HTTP split after PowerGam candidate acceptance: browser only until final gate page is accepted, then transfer form/cookies into HTTP `/links/go` with prewarmed Turnstile.
2. In parallel, investigate whether an HTTP/3-capable client can reproduce Chrome's accepted PowerGam navigation without Selenium.

## Browser-to-HTTP final handoff probe

Patch added `SHORTLINK_BYPASS_GPLINKS_HTTP_FINAL_HANDOFF=1` in `gplinks_live_browser.py`.

Live artifact: `artifacts/active/gplinks-hybrid-http-final-live.json`.

Result:

```text
browser reached accepted final GPLinks page
http-final-gate-start imported GPLinks cookies: AppSession, csrfToken, app_visitor, cf_clearance, ab, analytics cookies
HTTP /links/go result: {"status":"error","message":"Bad Request.","url":""}
browser fallback then submitted the same page path and reached http://tesskibidixxx.com/
```

Meaning:

- Browser-to-HTTP split after PowerGam acceptance is wired, but not accepted by GPLinks final submit yet.
- The failure is after the PowerGam ledger, at the CakePHP/GPLinks final form boundary.
- Because it adds a second Turnstile solve and slows the successful browser fallback, the lane remains disabled by default.

Likely next delta at this final boundary:

- Browser submit may rely on exact in-page callback/runtime state, not just copied cookies and hidden form fields.
- Need a CDP performance-log capture of browser `/links/go` request headers/cookies/body from the same run and compare to the curl_cffi handoff request.

## curl_cffi HTTP/3 replay test

Artifact: `artifacts/active/gplinks-h3-replay-test.json`.

Result:

```text
curl_cffi CurlHttpVersion.V3
PowerGam root POST steps 1/2/3 -> expected redirects
candidate -> 302 /link-error?error_code=not_enough_steps
```

Meaning:

- HTTP/3 alone does not reproduce the accepted browser PowerGam ledger.
- Transport may still matter in combination with browser runtime state, but `CurlHttpVersion.V3` by itself is falsified as the missing single switch.
