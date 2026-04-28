# 2026-04-28 XUT HTTP/Browser Hybrid Optimization Report

Scope: `xut.io` / `autodime.com/cwsafelinkphp` path, focused on reducing `xut_live_browser.py` solve time by moving browser-independent parts into HTTP requests. No project source files were modified.

## Summary

A faster hybrid lane is feasible.

The biggest proven win is: **Step 1 IconCaptcha and autodime Steps 2-4 can run browserless over `requests`**. The only part that still needs a live browser is the `gamescrate.app` Cloudflare boundary. After gamescrate opens the `xut.io?...sl=` Step 6 URL, the final `xut.io /links/go` submit can also run over HTTP.

Observed full current helper run:

- command: `xvfb-run -a .venv/bin/python xut_live_browser.py https://xut.io/hd7AOJ --timeout 260`
- result: `status=1`, `message=XUT_FINAL_OK`, `bypass_url=http://tesskibidixxx.com/`
- wall time: `real 116.99s`
- run needed 2 IconCaptcha attempts.

Proven HTTP lane in this investigation:

- `xut -> autodime Step 1 -> HTTP IconCaptcha LOAD/SELECTION -> verify`: `15.54s`, returned `{"ok":true,"redirect":"/blog/..."}`.
- `Step 2 -> Step 3 -> Step 4 -> gamescrate setcookie`: `40.3s` total from fresh xut entry, including required waits.
- `xut Step 6 HTML -> /links/go`: HTTP POST returned `{"status":"success","url":"http://tesskibidixxx.com"}` after the 5s wait.

## Current bottlenecks by step

### 0. Browser process startup and warm entry

Current helper always starts `undetected_chromedriver` and drives every step through Selenium. This adds cold-start overhead and makes the whole path depend on ChromeDriver stability.

Evidence:

- Previous workframe noted a live run died after Step 1 with `localhost chromedriver connection refused`.
- Current full helper run succeeded but still paid the full browser overhead for browserless-compatible stages.

### 1. Step 1 IconCaptcha in browser

Current implementation:

- waits for Step 1 page
- hard sleeps `12s`
- clicks `.iconcaptcha-widget`
- waits `4s` for canvas
- solves canvas through local API or Python fallback
- clicks canvas
- sleeps `6s`
- retries up to 6 attempts

Current-run evidence:

- attempt 1 failed, selected cell 5, confidence `0.7335`
- attempt 2 passed, selected cell 3, confidence `0.4601`
- failed attempt costs roughly another challenge-load/click/reset cycle.

Browserless proof:

- Step 1 page exposes `_iconcaptcha-token`, `CWSLSESSID`, `iconcaptchaEndpoint=/cwsafelinkphp/sl-iconcaptcha-request.php`, `verifyUrl=/cwsafelinkphp/sl-iconcaptcha-verify.php`.
- IconCaptcha client JS is simple base64 JSON, not encrypted:
  - `LOAD`: base64 JSON `{widgetId, action:"LOAD", theme, token, timestamp, initTimestamp}`
  - `SELECTION`: base64 JSON `{widgetId, challengeId, action:"SELECTION", x, y, width, token, timestamp, initTimestamp}`
  - header: `X-IconCaptcha-Token: <_iconcaptcha-token>`
- Live HTTP probe returned normal challenge JSON with `identifier`, `challenge`, `expiredAt`, `timestamp`.
- Solving `challenge` with existing `solve_iconcaptcha_data_url('data:image/png;base64,' + challenge)` and POSTing `SELECTION` returned `completed:true`.
- POSTing `/cwsafelinkphp/sl-iconcaptcha-verify.php` with `_iconcaptcha-token`, `ic-rq=1`, `ic-wid=<widgetId>`, `ic-cid=<identifier>`, `ic-hp=` returned redirect to Step 2.

Conclusion: IconCaptcha can run without browser for this target.

### 2. Autodime Step 2

Current helper uses Selenium click and page waits.

Browserless proof:

- Step 2 page has `window.SL_CFG = { step:2, countdown:5, nextUrl:'/cwsafelinkphp/sl-step3.php' }`.
- After waiting `5.8s`, HTTP POST `1=1` to `nextUrl` returned JSON redirect to `https://textfrog.com/cwsafelinkphp/setcookie.php?t=...` and then Step 3.

### 3. Textfrog Step 3

Browserless proof:

- Step 3 page has `step:3`, `countdown:10`, `nextUrl:'/cwsafelinkphp/sl-step4.php'`.
- After waiting `10.8s`, HTTP POST returned redirect to Step 4.

### 4. Textfrog Step 4

Browserless proof:

- Step 4 page has `step:4`, `countdown:5`, `nextUrl:'/cwsafelinkphp/sl-step5.php'`.
- After waiting `5.8s`, HTTP POST returned redirect to `https://gamescrate.app/cwsafelinkphp/setcookie.php?t=...`.

### 5. Gamescrate Step 5 / Cloudflare boundary

This remains the primary live-browser boundary.

Evidence:

- Pure HTTP request to the gamescrate `setcookie.php?t=...` URL landed on `Just a moment...` with no `SL_CFG`.
- Earlier notes also found browserless `curl_cffi` against gamescrate returned `403` / Cloudflare challenge.
- Current successful helper run reached normal gamescrate page only through live Chromium:
  - URL: `https://gamescrate.app/game/bubble-shooter-classic`
  - title: `Step 5/6`
  - body showed `10 SECONDS`, then `Open Final Page`.

Current code adds a fixed `14s` dwell after `Open Final Page` appears to avoid `Error: too_fast`, then clicks.

Conclusion: keep browser here unless a separate Cloudflare clearance lane is proven. Do not spend first optimization pass trying to fully browserless gamescrate.

### 6. XUT Step 6 final submit

Current helper keeps using Selenium until final click.

Browserless proof:

- After gamescrate opened `https://xut.io/hd7AOJ?sl=...`, a plain HTTP GET of that URL returned the Step 6 page.
- Static HTML contains `form#go-link`, `_csrfToken`, `ad_form_data`, `_Token[fields]`, `_Token[unlocked]`, and disabled `Please wait...` button.
- After waiting `5.8s`, HTTP POST to `/links/go` with the form fields and normal AJAX headers returned:
  - `{"status":"success","message":"","url":"http:\/\/tesskibidixxx.com"}`

Conclusion: once gamescrate has produced the signed `xut.io?...sl=` URL, final xut Step 6 can be done without Selenium.

## Boundary catalog

| Boundary | Location | Status | Evidence |
|---|---|---:|---|
| XUT alias wrapper | `https://xut.io/<id>` -> `autodime.com/cwsafelinkphp/go.php` | closed | HTTP 302 and `fexkomin` cookie observed. |
| Autodime Step 1 server timer | Step 1 `countdown:10` | narrowed | HTTP verify succeeds after respecting ~10s wait. |
| IconCaptcha protocol | `/cwsafelinkphp/sl-iconcaptcha-request.php` + `/sl-iconcaptcha-verify.php` | closed for xut/autodime | HTTP LOAD/SELECTION/verify succeeded. |
| Autodime/textfrog step timers | `sl-step3.php`, `sl-step4.php`, `sl-step5.php` | closed | HTTP posts after countdown returned JSON redirects. |
| Gamescrate Cloudflare | `gamescrate.app/cwsafelinkphp/setcookie.php?t=...` | primary open boundary | Pure HTTP hit `Just a moment...`; live Chromium reached Step 5. |
| Gamescrate too-fast guard | Step 5 `Open Final Page` | narrowed | Existing code needs extra dwell. Current note says exact timer flip can return `Error: too_fast`. |
| XUT Step 6 final form | `xut.io/<id>?sl=...` + `/links/go` | closed after signed URL | HTTP POST returned final URL. |

## Concrete patch proposal

Do not patch `engine.py` or registry first. Build and test a new helper path inside `xut_live_browser.py` or a separate helper module, then wire only after live proof.

Recommended minimal-diff implementation shape:

1. Add HTTP helper functions, kept isolated:
   - `xut_http_warm_entry(url) -> session, step1_html, facts`
   - `extract_sl_cfg(html) -> dict`
   - `solve_iconcaptcha_http(session, step1_url, html) -> redirect`
   - `advance_cwsafelink_http(session, url, referer) -> gamescrate_setcookie_url`
   - `submit_xut_step6_http(step6_url) -> final_url`

2. Add an optional hybrid mode in `xut_live_browser.py`:
   - default path can stay direct browser until the hybrid is proven stable.
   - env flag suggestion: `SHORTLINK_BYPASS_XUT_HYBRID=1`.

3. Hybrid flow:
   1. Use HTTP for xut entry and autodime warmup.
   2. Respect Step 1 `countdown`.
   3. Run IconCaptcha over HTTP:
      - generate `widgetId = uuid4()`
      - `initTimestamp = now - 250`
      - POST `LOAD`
      - solve returned `challenge` with existing local solver
      - POST `SELECTION`
      - if `completed:true`, POST verify form
      - if wrong, retry fresh LOAD/SELECTION in the same HTTP session up to current retry count.
   4. Use HTTP for Step 2/3/4 by parsing `SL_CFG.nextUrl` and respecting each countdown.
   5. When `gamescrate.app/cwsafelinkphp/setcookie.php?t=...` is reached, launch Chromium directly on that URL.
   6. Let browser solve/reach gamescrate Step 5.
   7. Either:
      - lowest-risk first patch: keep browser for gamescrate Step 5 click, then export `driver.current_url` once it becomes `xut.io?...sl=` and call `submit_xut_step6_http()`; or
      - second patch: export gamescrate cookies and POST Step 5 `nextUrl` from HTTP after dwell, skipping browser click too. This needs one live proof before enabling.
   8. Submit XUT Step 6 over HTTP and return final URL.

4. Tests to add after patch:
   - unit for IconCaptcha payload generation: LOAD/SELECTION base64 JSON includes required fields and `X-IconCaptcha-Token` header.
   - unit for parsing `window.SL_CFG` from Step 2/3/4 pages.
   - unit for XUT Step 6 form extraction and `/links/go` response handling.
   - integration smoke should keep final oracle strict: only return success if `/links/go` returns `status=success` with a URL or browser reaches non-blocklisted final host.

## Speed estimate

Baseline observed in this run: `116.99s`.

Conservative hybrid estimate:

- HTTP entry + Step 1 IconCaptcha + verify: `15-30s`, depending on captcha retries.
- HTTP Steps 2-4: `24-28s`, mostly mandatory countdowns.
- Browser gamescrate CF + Step 5: `25-45s`, depending on Cloudflare/page load.
- HTTP XUT Step 6: `6-8s`.

Expected total after first hybrid patch: **70-90s** on normal runs, roughly **25-40% faster** than the observed all-browser path.

If gamescrate Step 5 can be reduced to browser-only clearance plus HTTP POST, expected total can drop toward **60-75s**. Full browserless is not currently proven because gamescrate Cloudflare blocks pure HTTP.

## Risk notes

- Do not remove the current all-browser lane. Keep it as fallback because gamescrate and solver behavior are live-target dependent.
- The IconCaptcha heuristic is still imperfect. HTTP mode should retry the same way browser mode does, but cheaper and with clearer failure data.
- Avoid declaring gamescrate browserless until a run proves HTTP after clearance can post Step 5 and produce the `xut.io?...sl=` URL.
- The XUT Step 6 HTTP submit needs the signed `sl=` URL from gamescrate. It is not derivable from entry/static HTML.
