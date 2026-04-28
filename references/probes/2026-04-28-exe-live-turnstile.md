# Probe notes: exe.io / exeygo live Turnstile pass

Date: 2026-04-28
Scope: `https://exe.io/vkRI1` -> expected `https://google.com`
Method: headless Chrome CDP live browser plus local Turnstile solver API at `http://127.0.0.1:5000`. Scratch helper: `artifacts/active/tmp_exe_live_solve.py`. No commit.

## Result

Live helper reached the final downstream URL. The integrated engine path also returned the same final URL.

Scratch helper command:

```bash
.venv/bin/python artifacts/active/tmp_exe_live_solve.py https://exe.io/vkRI1 | tee artifacts/active/tmp_exe_live_solve2.out.json
```

Integrated engine command:

```bash
.venv/bin/python engine.py --pretty https://exe.io/vkRI1 | tee artifacts/active/exe_engine_live_run.json
```

Scratch helper result summary:

```json
{
  "status": 1,
  "stage": "live-browser-turnstile-post",
  "bypass_url": "https://www.google.com/",
  "final_url": "https://www.google.com/",
  "final_title": "Google",
  "sitekey": "0x4AAAAAACPCPhXQQr5wP1VW",
  "waited_seconds": 100.6
}
```

Integrated engine result summary:

```json
{
  "status": 1,
  "message": "EXE_LIVE_TURNSTILE_CHAIN_OK",
  "stage": "live-browser-turnstile-go",
  "bypass_url": "https://www.google.com/",
  "live_helper.waited_seconds": 118.5
}
```

Success oracle: browser left `exeygo.com` and loaded `https://www.google.com/` with title `Google`. This proves the final target from post-captcha execution, not from the old random `document.referrer` snippet.

## Exact live sequence

1. `Page.navigate("https://exe.io/vkRI1")` in fresh headless Chrome context.
2. Browser lands on `https://exeygo.com/vkRI1`.
3. Submit first CakePHP form in-browser:

```js
document.querySelector('form#before-captcha')?.submit()
```

4. Second gate appears at same URL with `form#link-view`.
5. Active captcha config from `window.app_vars`:

```json
{
  "captcha_type": "turnstile",
  "turnstile_site_key": "0x4AAAAAACPCPhXQQr5wP1VW",
  "reCAPTCHA_site_key": "6LfUVmMqAAAAAI0OCsP4rvCa2HlgEgHB-5Cu7QwI",
  "counter_value": "6",
  "counter_start": "DOMContentLoaded",
  "captcha_shortlink": "yes"
}
```

6. Solve token with local API:

```http
GET http://127.0.0.1:5000/turnstile?url=https://exeygo.com/vkRI1&sitekey=0x4AAAAAACPCPhXQQr5wP1VW
GET http://127.0.0.1:5000/result?id=<taskId>
```

7. Inject token into existing unlocked field in `form#link-view` and enable the button:

```js
const f = document.querySelector('form#link-view') || document.querySelector('form');
let ta = f.querySelector('[name="cf-turnstile-response"]') || document.querySelector('[name="cf-turnstile-response"]');
if (!ta) {
  ta = document.createElement('textarea');
  ta.name = 'cf-turnstile-response';
  ta.style.display = 'none';
  f.appendChild(ta);
}
ta.value = token;
ta.dispatchEvent(new Event('input', {bubbles: true}));
ta.dispatchEvent(new Event('change', {bubbles: true}));
const b = document.querySelector('#invisibleCaptchaShortlink') || f.querySelector('button,input[type=submit]');
if (b) b.disabled = false;
```

Observed token field:

```text
name=cf-turnstile-response
value=<solver token, observed length 752, ephemeral>
```

Observed `form#link-view` POST fields after injection:

```text
_method=POST
_csrfToken=<session csrf>
ref=
f_n=slc
cf-turnstile-response=<valid solver token>
_Token[fields]=<Cake token>:f_n|ref
_Token[unlocked]=adcopy_challenge|adcopy_response|captcha_code|captcha_namespace|cf-turnstile-response|g-recaptcha-response
```

8. Click captcha submit button:

```js
document.querySelector('#invisibleCaptchaShortlink')?.click()
```

9. Valid captcha POST creates final timer form `form#go-link` at same URL.

Observed `form#go-link` fields:

```text
_method=POST
_csrfToken=<same session csrf>
ad_form_data=<server-generated encrypted/encoded payload>
_Token[fields]=<Cake token>:ad_form_data
_Token[unlocked]=adcopy_challenge|adcopy_response|captcha_code|captcha_namespace|cf-turnstile-response|g-recaptcha-response
```

10. Wait until `#go-submit` is enabled and text is `Get Link`, then click:

```js
(document.querySelector('#go-submit') || document.querySelector('form#go-link button'))?.click()
```

11. Browser navigates to `https://www.google.com/`.

## Boundary catalog

| Boundary | Location | Evidence | Status |
| --- | --- | --- | --- |
| Entry host routing | `exe.io/vkRI1` -> `exeygo.com/vkRI1` | Browser final href after navigation is `https://exeygo.com/vkRI1` | closed |
| Pre-captcha CakePHP state | `form#before-captcha`, `f_n=sle` | In-browser form submit advances to `form#link-view` | closed |
| Captcha validation | `form#link-view`, field `cf-turnstile-response` | Solver token length 752 injected; click advances to `form#go-link` | closed for sample |
| Timer/final payload | `form#go-link`, field `ad_form_data` | Appears only after valid captcha click; button enables after countdown | closed for sample |
| Final target reveal | click `#go-submit` | Browser leaves exeygo and loads `https://www.google.com/` | closed for sample |

## Proposed smallest code changes

1. Add `exe_live_browser.py`, cloned structurally from `cuty_live_browser.py` but with exe-specific stages:
   - navigate input URL
   - submit `form#before-captcha`
   - read sitekey from `.cf-turnstile[data-sitekey]` or `window.app_vars.turnstile_site_key`
   - call existing `solve_turnstile()` helper
   - inject `cf-turnstile-response` into `form#link-view`
   - click `#invisibleCaptchaShortlink`
   - wait for `form#go-link` and enabled `#go-submit`
   - click `#go-submit`
   - success only if final host is not `exe.io/exeygo.com`, with `google.com` accepted for sample.
2. Add env constants to `engine.py` near CUTY settings:
   - `EXE_BROWSER_TIMEOUT`
   - `EXE_LIVE_HELPER`
   - `EXE_HELPER_PYTHON`
   - `EXE_HELPER_PYTHONPATH`
   - `EXE_TURNSTILE_SOLVER_URL` defaulting to `http://127.0.0.1:5000`
3. Add `_resolve_exe_live()` mirroring `_resolve_cuty_live()`.
4. In `_handle_exe()`, after mapping `form#link-view`, call `_resolve_exe_live(url)` when `captcha_type == "turnstile"` and a sitekey exists. Promote to status `1` only when helper returns a downstream URL.
5. Add a unit test that patches `_resolve_exe_live()` to return `status=1,bypass_url=https://www.google.com/` and asserts `EXE_LIVE_TURNSTILE_CHAIN_OK`.

## Caveats

- The token is bound to page/sitekey/browser context and is ephemeral. Do not persist or reuse it.
- A pure HTTP submit may still fail because the valid path also creates a server-generated `ad_form_data` form after frontend JS/timer execution. The smallest proven lane is same-browser CDP, not browserless HTTP.
