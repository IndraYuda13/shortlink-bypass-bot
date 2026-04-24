# Probe notes: xut / ez4short / cuty samples

Date: 2026-04-24 Asia/Jakarta  
Scope: safe HTTP probing only; no code changes.

## `https://xut.io/hd7AOJ`

Expected oracle: `http://tesskibidixxx.com`.

### Entry / redirects

- `GET https://xut.io/hd7AOJ` returns `302` to:
  - `https://autodime.com/cwsafelinkphp/go.php?link=snpurl%2Fhd7AOJ`
- Entry cookies:
  - `AppSession`
  - `refhd7AOJ`
- `GET` the `go.php` URL with `Referer: https://xut.io/hd7AOJ` returns `302` to Google wrapper for `https://autodime.com/`.
- `go.php` sets `fexkomin`; decoded unsigned payload observed:
  - `v: 1`
  - `step: 1`
  - `sid: /hd7AOJ`
  - `iat/exp`
  - `nonce`
  - `fp`

### Backend family / gate

- Same wrapper family as prior xut sample: `autodime.com/cwsafelinkphp`.
- Warming `https://autodime.com/` with `Referer: https://www.google.com/` lands on `Step 1/6`.
- Step page facts:
  - title: `Step 1/6`
  - form: `form#sl-form`, `method=post`, `action=https://autodime.com/`
  - hidden input: `_iconcaptcha-token`
  - `step: 1`
  - `countdown: 10`
  - `captchaProvider: iconcaptcha`
  - `iconcaptchaEndpoint: /cwsafelinkphp/sl-iconcaptcha-request.php`
  - `verifyUrl: /cwsafelinkphp/sl-iconcaptcha-verify.php`

### Target embedding

- No `tesskibidixxx.com` URL observed in entry/go/home HTML or decoded cookies.
- Target appears to require live stepwise gate completion beyond `Step 1/6`; it is not statically embedded at entry.

### Engine status

- Current engine identifies it as `autodime.cwsafelinkphp` and maps the Step 1 IconCaptcha gate.
- Local live helper invocation failed in this environment with `ModuleNotFoundError: No module named 'undetected_chromedriver'`; engine returned progress-only / no final.

## `https://ez4short.com/qSyPzeo`

Expected oracle: `https://tesskibidixxx.com`.

### Entry / redirects

- `GET https://ez4short.com/qSyPzeo` returns `307` to:
  - `https://tech8s.net/safe.php?link=qSyPzeo`
- Entry cookie:
  - `AppSession`
- `GET https://tech8s.net/safe.php?link=qSyPzeo` returns HTML with JS redirect through a Google URL wrapper to a rotating `tech8s.net` article.
- `tech8s.net/safe.php` sets:
  - `tp=qSyPzeo` with short max-age.

### Backend family / gate

- This is a multi-domain `newwpsafelink` article-step flow, not the autodime family.
- First article page has:
  - hidden form field: `newwpsafelink=qSyPzeo`
  - button: `Continue`
  - two JS-only click steps (`Step One`, `Step Two`) that reveal the continue button client-side.
  - no real captcha sitekey observed; there is anti-adblock code and dead/placeholder `g-recaptcha` handling.
- Posting `newwpsafelink=qSyPzeo` to the tech8s article returned another article page containing:
  - `https://game5s.com/safe.php?link=qSyPzeo`
- `game5s.com/safe.php?link=qSyPzeo` returns JS redirect through Google/Bing wrapper to a `game5s.com` article and sets/uses `tp=qSyPzeo`.
- `game5s` article is step `3/4`:
  - hidden form field: `newwpsafelink=qSyPzeo`
  - text says to watch/open an ad tab for `10 seconds`
  - no captcha sitekey observed.
- Posting that form returns step `4/4` page:
  - modal/button timer `count3 = 3` with interval `1200ms`
  - visible link after modal close points back to `https://ez4short.com/qSyPzeo`.

### Target embedding

- No `tesskibidixxx.com` URL observed in entry, tech8s article, game5s article, or step 4 HTML.
- Re-requesting the original ez4short URL after the rough HTTP-only sequence did not produce the oracle; it returned the generic EZ4Short landing page in my run.
- Target likely requires preserving exactly the live browser/session/ad-step state and/or a server-side visitor cookie sequence, not just naive form POST replay.

### Engine status

- Current engine returns `UNSUPPORTED_FAMILY` for `ez4short.com`.

## `https://cuty.io/AfaX6jx`

Expected oracle: `https://google.com`.

### Entry / redirects

- `GET https://cuty.io/AfaX6jx` returns `302` to:
  - `https://cuttlinks.com/AfaX6jx?auth_token=<uuid>`
- It sets Laravel-style cookies:
  - `XSRF-TOKEN`
  - `cutyio_session`
- `GET` the `cuttlinks.com/...auth_token=...` URL returns `302` to:
  - `https://cuttlinks.com/AfaX6jx`
- Final page title:
  - `Shorten Links And Earn Money | cuty.io`

### Backend family / gate

- Cuty/cuttlinks Laravel-style gate.
- Main free form:
  - `form#free-submit-form`
  - `method=POST`
  - `action=https://cuttlinks.com/AfaX6jx`
  - hidden `_token=<csrf>`
  - disabled submit button `id=submit-button`, class `vhit`, `data-ref=first`
  - button text initially: `Please Wait ...`
- Page includes:
  - `https://cdn.cuty.io/js/public/links/first.js?...` (large obfuscated script)
  - `https://vhit.io/scripts/vhit.js?ref=cuty&tid=...&cid=...`
- Page copy says: `Continue with Ads`, `Watch ads and complete captcha`.
- Static HTML did not expose a Turnstile/reCAPTCHA/hCaptcha sitekey. The captcha/enablement boundary appears JS/VHit-driven.
- Plain POST with only `_token` returned another cuty page, not a redirect/final.

### Target embedding

- No `google.com` final target observed in HTML, form, cookies, or POST response.
- Target appears to require live JS gate/VHit/captcha completion; not embedded in the initial page.

### Engine status

- Current engine returns `UNSUPPORTED_FAMILY` for `cuty.io`.

## Commands / evidence used

- `python3 tmp_probe.py` (temporary local probe; removed after use): entry redirects, cookies, forms, embedded URLs.
- Inline Python `requests`/`BeautifulSoup` probes for:
  - xut entry/go/autodime warmup + `fexkomin` decode
  - ez4short tech8s/game5s article-step pages and form POSTs
  - cuty/cuttlinks entry/auth-token/free-form page and plain POST
- Engine smoke:
  - `python3 - <<'PY' ... ShortlinkBypassEngine(...).analyze(...) ... PY`

## Next handler recommendation

1. `xut.io/hd7AOJ`: reuse/extend existing `autodime.cwsafelinkphp` handler. Next blocker remains live IconCaptcha/step chain and later Cloudflare/gamescrate-style handoff; no new static target shortcut found.
2. `ez4short.com/qSyPzeo`: add a new `ez4short multi-domain newwpsafelink` mapper/handler. Start with requests mapping for `ez4short -> tech8s safe -> article POST -> game5s safe -> article POST -> step 4`, then validate in a real browser because final oracle did not appear in HTTP-only replay.
3. `cuty.io/AfaX6jx`: add a new `cuty/cuttlinks` mapper. Treat VHit/obfuscated JS as the primary boundary; likely needs browser instrumentation or JS deobfuscation before final `google.com` can be claimed.
