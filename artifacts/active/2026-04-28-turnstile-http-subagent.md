# Turnstile live-browser -> HTTP probe: cuty.io and exe.io

Date: 2026-04-28 Asia/Jakarta  
Scope: `cuty.io/AfaX6jx` and `exe.io/vkRI1` only. No production files modified. Scratch probes only under `artifacts/active/`.

## Verdict

- `exe.io` / `exeygo.com`: **can be converted to HTTP-only now** with `curl_cffi` + local Turnstile solver, preserving same-session CakePHP forms and timer. Live HTTP probe reached Google.
- `cuty.io` / `cuttlinks.com`: **not safe to convert to full HTTP-only yet**. HTTP replay can reach the final `form#submit-form`, but the `/go/<alias>` POST bounces back to the shortlink page instead of leaving to Google. Live CDP succeeds with the same visible form fields, so the missing boundary is browser-executed JS/VHit/ad lifecycle state, not basic Laravel CSRF or Turnstile token submission.

## Files inspected

- `cuty_live_browser.py`
- `exe_live_browser.py`
- `engine.py` handlers/constants for cuty/exe
- `tests/test_cuty_lnbz.py`
- `tests/test_exe.py`
- prior notes:
  - `references/probes/2026-04-24-xut-ez-cuty.md`
  - `references/probes/2026-04-24-exe-deep.md`
  - `references/probes/2026-04-28-exe-live-turnstile.md`
  - `references/target-sample-catalog.md`

## Scratch artifacts created

- `artifacts/active/turnstile_http_probe.py`
- `artifacts/active/2026-04-28-exe-http-probe.json`
- `artifacts/active/2026-04-28-cuty-http-probe.json`
- `artifacts/active/2026-04-28-cuty-http-probe-origin-null.json`
- `artifacts/active/cuty_cdp_network_probe.py`
- `artifacts/active/2026-04-28-cuty-cdp-network.log`
- `artifacts/active/cuty_cookie_probe.py`
- `artifacts/active/2026-04-28-cuty-cookie-probe.log`
- `artifacts/active/cuty_vhit_network_probe.py`
- `artifacts/active/2026-04-28-cuty-vhit-network.json`

## exe.io exact HTTP flow

Sample: `https://exe.io/vkRI1`  
Oracle: `https://google.com`

### Required session and headers

Use one `curl_cffi.requests.Session(impersonate="chrome136")` for the entire chain.

Baseline headers:

```text
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8
Accept-Language: en-US,en;q=0.9
Upgrade-Insecure-Requests: 1
```

For POSTs:

```text
Content-Type: application/x-www-form-urlencoded
Origin: https://exeygo.com
Referer: current exeygo page URL
```

Cookies observed and required in same session:

```text
AppSession on exe.io
AppSession on exeygo.com
csrfToken on exeygo.com
origin=exe on exeygo.com
```

### Flow map

1. Entry redirect:

```text
GET https://exe.io/vkRI1, allow_redirects=False
-> 302 Location: https://exeygo.com/vkRI1
sets AppSession for exe.io
```

2. First gate:

```text
GET https://exeygo.com/vkRI1
-> 200 title: exe.io
sets AppSession, csrfToken, origin=exe for exeygo.com
```

Parse `window.app_vars`:

```json
{
  "captcha_type": "turnstile",
  "turnstile_site_key": "0x4AAAAAACPCPhXQQr5wP1VW",
  "reCAPTCHA_site_key": "6LfUVmMqAAAAAI0OCsP4rvCa2HlgEgHB-5Cu7QwI",
  "counter_value": "6",
  "counter_start": "DOMContentLoaded"
}
```

Parse and submit `form#before-captcha`:

```text
POST https://exeygo.com/vkRI1
_method=POST
_csrfToken=<session csrf>
f_n=sle
_Token[fields]=<Cake token>:f_n
_Token[unlocked]=adcopy_challenge|adcopy_response|captcha_code|captcha_namespace|cf-turnstile-response|g-recaptcha-response
```

3. Captcha gate:

Response contains `form#link-view`:

```text
POST https://exeygo.com/vkRI1
_method=POST
_csrfToken=<same session csrf>
ref=https://exeygo.com/vkri1
f_n=slc
cf-turnstile-response=<valid local solver token>
g-recaptcha-response=
_Token[fields]=<Cake token>:f_n|ref
_Token[unlocked]=adcopy_challenge|adcopy_response|captcha_code|captcha_namespace|cf-turnstile-response|g-recaptcha-response
```

Token call:

```text
GET http://127.0.0.1:5000/turnstile?url=https://exeygo.com/vkRI1&sitekey=0x4AAAAAACPCPhXQQr5wP1VW
GET http://127.0.0.1:5000/result?id=<taskId>
```

Wait `counter_value + 1` seconds before submitting `form#link-view`.

4. Final timer form:

Captcha POST returns `form#go-link`:

```text
action=https://exeygo.com/links/go
_method=POST
_csrfToken=<same session csrf>
ad_form_data=<server-generated encrypted payload>
_Token[fields]=<Cake token>:ad_form_data
_Token[unlocked]=adcopy_challenge|adcopy_response|captcha_code|captcha_namespace|cf-turnstile-response|g-recaptcha-response
```

Wait another `counter_value + 1` seconds, then:

```text
POST https://exeygo.com/links/go
<body exactly from form#go-link>
```

### Live HTTP result

Command:

```bash
.venv/bin/python artifacts/active/turnstile_http_probe.py exe https://exe.io/vkRI1 | tee artifacts/active/2026-04-28-exe-http-probe.json
```

Result:

```json
{
  "status": 1,
  "stage": "http-final",
  "bypass_url": "https://www.google.com/?gws_rd=ssl",
  "final_url": "https://www.google.com/?gws_rd=ssl",
  "waited_seconds": 71.3
}
```

Success oracle: final response loaded Google title/body after same-session HTTP POST to `/links/go`.

## cuty.io exact HTTP flow and blocker

Sample: `https://cuty.io/AfaX6jx`  
Oracle: `https://google.com`

### Required session and headers tested

Use one `curl_cffi.requests.Session(impersonate="chrome136")` for all steps.

Baseline headers same as exe. For form POSTs, both of these were tested:

```text
Origin: https://cuttlinks.com
Referer: current cuttlinks page URL
```

and browser-like:

```text
Origin: null
Content-Type: application/x-www-form-urlencoded
```

Neither made final `/go/AfaX6jx` leave to Google.

Cookies visible in HTTP replay:

```text
XSRF-TOKEN on cuty.io
cutyio_session on cuty.io
XSRF-TOKEN on cuttlinks.com
cutyio_session on cuttlinks.com
```

### Flow map

1. Entry redirect:

```text
GET https://cuty.io/AfaX6jx, allow_redirects=False
-> 302 Location: https://cuttlinks.com/AfaX6jx?auth_token=<uuid>
sets XSRF-TOKEN + cutyio_session on cuty.io
```

2. Auth token hop:

```text
GET https://cuttlinks.com/AfaX6jx?auth_token=<uuid>, allow_redirects=False
-> 302 Location: https://cuttlinks.com/AfaX6jx
sets XSRF-TOKEN + cutyio_session on cuttlinks.com
```

3. First page:

```text
GET https://cuttlinks.com/AfaX6jx
-> 200
form#free-submit-form action=https://cuttlinks.com/AfaX6jx method=POST
_token=<Laravel csrf>
```

4. Free form POST:

```text
POST https://cuttlinks.com/AfaX6jx
_token=<Laravel csrf>
```

Response stays at same URL and exposes Turnstile:

```text
sitekey=0x4AAAAAAABnHbN4cNchLhd_
form#free-submit-form
_token=<same csrf>
cf-turnstile-response=
```

5. Captcha token submit:

Token call:

```text
GET http://127.0.0.1:5000/turnstile?url=https://cuttlinks.com/AfaX6jx&sitekey=0x4AAAAAAABnHbN4cNchLhd_
GET http://127.0.0.1:5000/result?id=<taskId>
```

Submit:

```text
POST https://cuttlinks.com/AfaX6jx
_token=<Laravel csrf>
cf-turnstile-response=<valid solver token>
```

Response reaches final visible form:

```text
form#submit-form action=https://cuttlinks.com/go/AfaX6jx method=POST
_token=<same csrf>
data=<server-generated encrypted payload>
#timer starts at 8 seconds
```

6. Final `/go` POST replay:

```text
POST https://cuttlinks.com/go/AfaX6jx
_token=<Laravel csrf>
data=<server-generated encrypted payload>
```

Observed HTTP result:

```json
{
  "status": 0,
  "stage": "http-final",
  "final_url": "https://cuttlinks.com/AfaX6jx",
  "waited_seconds": 63.6
}
```

The response is the cuty page again, not Google.

### Browser-only evidence for missing boundary

CDP browser with the same visible fields succeeds:

```text
POST https://cuttlinks.com/go/AfaX6jx
Origin: null
Content-Type: application/x-www-form-urlencoded
_token=<csrf>&data=<encrypted payload>
-> navigates to https://google.com/ -> https://www.google.com/
```

Browser-only state observed before final submit:

```text
localStorage keys include:
- vhit_vid
- vhit_pages_<tid>
- fjidd
- agecc
- vast-client-total-calls
- clever-parameters
```

VHit/ad lifecycle requests observed only in the browser lane after `last.js`:

```text
GET https://vhit.io/scripts/vhit.js?ref=cuty&tid=<tid>&cid=412361
POST https://fp.vhit.io/
GET https://vhit.io/api/request?f=<fingerprint>
```

The HTTP replay never executes `first.js`, `captcha.js`, `last.js`, or the VHit telemetry/fingerprint calls. Since the generated `data` payload alone is not enough for `/go` to accept the request, the smallest proven conclusion is: Cuty final accept depends on browser-executed JS/VHit/ad lifecycle state in addition to same-session cookies, CSRF, Turnstile, timer, and form `data`.

## Smallest patch proposal

### 1. exe.io: add HTTP fast path

Recommended minimal implementation shape:

- Add a new helper module, e.g. `exe_http_fast.py`, instead of expanding `engine.py` heavily.
- Reuse `cuty_live_browser.solve_turnstile()` for the local solver contract.
- Implement the exact flow above with `curl_cffi.requests.Session(impersonate="chrome136")`.
- In `_handle_exe()`, after `form#link-view` is mapped and `captcha_type == "turnstile"`, call the HTTP helper first.
- Promote to success only when final host leaves `exe.io/exeygo.com`.
- Keep `_resolve_exe_live()` as fallback if HTTP helper fails with solver instability or unexpected form shape.

Expected speed:

- Live HTTP probe: `71.3s` end to end.
- Solver latency dominates. The two 7-second waits are required by server/client timer assumptions.
- Compared with CDP helper runs around `100-120s`, expected win is roughly **30-45 seconds** and much lower CPU/RAM because no Chrome page is launched by the bypass helper. The local solver still uses its own browser pool.

Suggested tests:

- Unit test parsing/replay path with mocked responses, similar to `test_exe_maps_two_stage_gate_without_claiming_final`, but with `_solve_turnstile` mocked and final `/links/go` mocked to Google.
- Integration smoke can stay manual because it depends on live solver.

### 2. cuty.io: keep CDP as primary, do not promote HTTP-only yet

Recommended minimal implementation:

- Do **not** replace `cuty_live_browser.py` with HTTP-only based on current evidence.
- Optional low-risk future helper: add a `cuty_http_probe`/experimental fast path that stops at `form#submit-form` and returns a structured blocker when `/go` bounces, but do not mark it success.
- If Boskuu wants to continue cutting Cuty speed, next real target is VHit emulation:
  1. fetch and execute/deobfuscate `vhit.js` enough to reproduce `fp.vhit.io` and `vhit.io/api/request` calls,
  2. preserve the same `tid/cid` from the Cuty page,
  3. prove `/go/<alias>` accepts after the telemetry calls,
  4. only then promote Cuty HTTP-only.

Expected speed if VHit is solved later:

- Best case similar to exe: solver + 8s timer, likely **60-75s**.
- Current proven HTTP replay is not a bypass, so no safe production speed claim for Cuty HTTP-only.

## Boundary catalog

| Family | Boundary | Status | Evidence |
| --- | --- | --- | --- |
| exe | entry redirect `exe.io -> exeygo.com` | closed | HTTP 302 and cookies captured |
| exe | CakePHP `before-captcha` form | closed | HTTP POST advances to `form#link-view` |
| exe | Turnstile token in `form#link-view` | closed for sample | valid solver token advances to `form#go-link` |
| exe | timer + `ad_form_data` final form | closed for sample | HTTP `/links/go` returns Google |
| cuty | Laravel entry/auth CSRF/session | closed | HTTP reaches first and captcha pages |
| cuty | Turnstile token | closed for sample | HTTP token POST reaches final `submit-form` |
| cuty | final `/go/<alias>` accept | open | HTTP bounces to cuttlinks page, CDP succeeds |
| cuty | VHit/ad lifecycle | primary/open | CDP has `vhit_pages_*` localStorage and `fp.vhit.io`/`vhit.io/api/request`; HTTP lacks this state |
