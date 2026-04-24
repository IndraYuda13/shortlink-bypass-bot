# Probe notes: gplinks / sfl / exe / aii

Date: 2026-04-24
Scope: `https://gplinks.co/YVTC`, `https://sfl.gl/18PZXXI9`, `https://exe.io/vkRI1`, `https://aii.sh/CBygg8fn2s3`
Method: safe HTTP probing with `requests` and `.venv` `curl_cffi` TLS impersonation. No code edits.

## Common engine state

Command:

```bash
for u in https://gplinks.co/YVTC https://sfl.gl/18PZXXI9 https://exe.io/vkRI1 https://aii.sh/CBygg8fn2s3; do
  .venv/bin/python engine.py --pretty "$u"
done
```

Observed:
- `gplinks.co`, `sfl.gl`, `exe.io` return `UNSUPPORTED_FAMILY` in current engine.
- `aii.sh` is already recognized by current engine and extracts the token target.

## `gplinks.co/YVTC`

### Entry behavior

Plain `requests` gets Cloudflare managed challenge:
- `GET https://gplinks.co/YVTC` -> `403`
- title: `Just a moment...`
- headers: `server=cloudflare`, `cf-mitigated=challenge`

With `.venv` `curl_cffi` / Chrome impersonation:
- `GET https://gplinks.co/YVTC` -> `302`
- `Location: https://powergam.online?lid=WVZUQw&pid=MTIyNDYyMg&vid=<base64-ish>&pages=Mw`
- cookies set on entry: `AppSession`, `csrfToken`

Decoded query values seen:
- `lid=WVZUQw` -> `YVTC`
- `pid=MTIyNDYyMg` -> `1224622`
- `pages=Mw` -> `3`

### Interstitial behavior

`GET powergam.online?...` with referer `https://gplinks.co/YVTC`:
- `200`, title `Please Wait... | PowerGam`
- form:
  - method: `POST`
  - action: same PowerGam URL
  - id: `adsForm`
  - hidden inputs: `form_name=ads-track-data`, `step_id`, `ad_impressions`, `visitor_id`, `next_target`
- important scripts:
  - `https://api.gplinks.com/track/js/power-cdn.js?v=2.0.0.5`
  - multiple ad scripts from `tracki.click`, `bvtpk.com`, etc.

The PowerGam JS is obfuscated but exposes the relevant state boundary in readable snippets:
- reads cookies/params for `pid`, `lid`, `vid`, `pages`, `step_count`
- `stepsToGo = Number(cookie_pages)` and sample has `pages=3`
- computes `readyToGo = next_status >= stepsToGo`
- maintains `next_target`
- references `/track/data.php` and an ad/impression-driven submit flow

### Captcha/timer/final target

- No captcha sitekey found on the entry/PowerGam HTML.
- The visible gate is ad-impression/step-count based, not a classic Turnstile/reCAPTCHA widget on the fetched HTML.
- Expected oracle remains `http://tesskibidixxx.com`, but that target was **not embedded visibly** in the HTTP-fetched entry/interstitial HTML.

### Handler recommendation

Add a dedicated `gplinks.co` handler using `curl_cffi` impersonation for entry. First map the PowerGam JS contract (`/track/data.php`, required cookies, step counter, `adsForm` payload) before attempting final replay. Treat plain `requests` as expected-CF-fail for this host.

## `sfl.gl/18PZXXI9`

### Entry behavior

Plain `requests` gets Cloudflare managed challenge (`403 Just a moment...`), but `.venv` `curl_cffi` / Chrome impersonation succeeds.

Entry:
- `GET https://sfl.gl/18PZXXI9` -> `200`, title `Wait...`
- cookies: `XSRF-TOKEN`, `SESSION`
- form:
  - method: `GET`
  - action: `https://app.khaddavi.net/redirect.php`
  - hidden: `ray_id=<random>`, `alias=18PZXXI9`

Following form GET:
- `GET https://app.khaddavi.net/redirect.php?ray_id=<ray>&alias=18PZXXI9` -> `302`
- `Location: /<random Indonesian article slug>/`
- sets `__session=<ray>`

Article page:
- host: `app.khaddavi.net`
- title examples varied by run, e.g. `Tips & Trik Bermain Clash of Clans... - khaddavi`
- JS module: `https://app.khaddavi.net/c/assets/link-CEoi9cK_.js`
- helper module: `https://app.khaddavi.net/c/assets/elements-C__E46FJ.js`

### API/timer/captcha contract

Readable JS contract from `elements-C__E46FJ.js`:
- `POST /api/session`
- `POST /api/go` with JSON `{key, size, _dvc}` and `Idempotency-Key`
- `POST /api/verify` with JSON `{_a, captcha, passcode}`
- Step 1 wait is hardcoded as `10` seconds; later steps use `3` seconds.
- If `captcha == "turnstile"`, page injects Turnstile with global `captcha_key`.

Observed for this sample:
- `POST /api/session` -> `{"step":1,"fb":false,"captcha":null,"passcode":false}`
- first premature `POST /api/go` -> `422 {"message":"Incomplete action","url":"https://app.khaddavi.net/redirect.php"}`
- `POST /api/verify` with no captcha needed -> `200 {"message":"OK","target":"https://app.khaddavi.net/redirect.php?ray_id=<new-ray>"}`
- subsequent `POST /api/go` -> `200 {"url":"https://sfl.gl/ready/go?t=<...>&a=MThQWlhYSTk%3D"}`

Ready page:
- `GET https://sfl.gl/ready/go?...` -> `200`, title `Your link almost ready | SafelinkU`
- contains button JS:
  - `window.location.href = "https:\/\/google.com";`

### Final target evidence

Final target is visibly embedded in the ready page as `https://google.com`, matching the oracle.

### Handler recommendation

Implement `sfl.gl` as a browserless `curl_cffi` handler:
1. entry GET and parse `ray_id`/`alias`
2. follow `app.khaddavi.net/redirect.php`
3. load article page to establish cookies
4. `POST /api/session`
5. respect `step` wait (`10s` for step 1; JS says `3s` for later steps)
6. `POST /api/verify` if required; this sample has `captcha=null`
7. `POST /api/go`
8. fetch ready page and extract `window.location.href` destination

## `exe.io/vkRI1`

### Entry behavior

With `.venv` `curl_cffi` / Chrome impersonation:
- `GET https://exe.io/vkRI1` -> `302`
- `Location: https://exeygo.com/vkRI1`
- cookie after entry: `AppSession`

`GET https://exeygo.com/vkRI1`:
- `200`, title `exe.io`
- cookies: `AppSession`, `csrfToken`, `origin=exe`
- first form:
  - id: `before-captcha`
  - method: `post`
  - action: `/vkRI1`
  - hidden: `_method=POST`, `_csrfToken`, `f_n=sle`, CakePHP `_Token[...]`
- button text: `Continue` but initially disabled client-side.

Submitting `before-captcha` once with hidden fields returned a second gate page:
- form id: `link-view`
- hidden `ref=https://exeygo.com/vkri1`, `f_n=slc`, `_csrfToken`, CakePHP `_Token[...]`
- button id: `invisibleCaptchaShortlink`
- button text: `I am not a robot`

### Captcha/timer config

Second gate page exposes `app_vars`:
- `captcha_type: "recaptcha"`
- `reCAPTCHA_site_key: "6LfUVmMqAAAAAI0OCsP4rvCa2HlgEgHB-5Cu7QwI"`
- `turnstile_site_key: "0x4AAAAAACPCPhXQQr5wP1VW"`
- `counter_value: "6"`
- `counter_start: "DOMContentLoaded"`
- `captcha_shortlink: "yes"`
- `force_disable_adblock: "1"`

Posting `link-view` without a captcha token caused a `302` back to `/vkRI1` and reset to the first page, so captcha/timer completion is required.

### Final target evidence

Expected oracle is `https://google.com`, but the real destination was **not proven from the active gate**. The HTML contains `https://google.com/` only in an anti/referrer-randomization snippet:

```js
const os = ["https://google.com/", "https://youtube.com/", "https://reddit.com/"];
Object.defineProperty(document, "referrer", { get: function(){ ... } });
```

Do not treat that snippet as final-target proof. It coincides with the oracle but is not sufficient evidence for extraction.

### Handler recommendation

Add a two-stage `exe.io -> exeygo.com` handler that parses CakePHP form tokens and app config, then integrate captcha solving for the active reCAPTCHA shortlink gate. The final destination should only be claimed after the captcha/timer `link-view` POST returns a redirect/final page.

## `aii.sh/CBygg8fn2s3`

### Entry behavior

`GET https://aii.sh/CBygg8fn2s3`:
- `200`, title `ShrinkBixby`
- cookies: `refCBygg8fn2s3`, `visit_token`
- form:
  - method: `POST`
  - action: rotating `https://techbixby.com/<article-slug>/`
  - hidden fields include `url`, `token`, `mysite=shrinkbixby.com`, `c_d`, `c_t`, `ad_type=4`, `visit_token`, `alias=CBygg8fn2s3`

Runtime/config extracted by current engine:
- `captcha_type: turnstile`
- `counter_value: 15`
- `counter_start: load`
- `captcha_shortlink: yes`
- `turnstile_site_key: 0x4AAAAAABde2R5F8ZlSAQ3R`

### Embedded/decoded target

Hidden `token` contains a base64 tail. Decoding the `aHR0...` tail yields:

```text
https://coinadster.com/shortlink.php?short_key=1cnd9hq0nfbem5dr8vrmaz17f44pvh9a
```

Current engine result:
- family: `aii.sh`
- message: `TOKEN_TARGET_EXTRACTED`
- bypass_url: `https://coinadster.com/shortlink.php?short_key=1cnd9hq0nfbem5dr8vrmaz17f44pvh9a`
- note: extracted from entry payload, not live captcha/timer execution.

### Handler recommendation

Keep/extend the existing `aii.sh` token decoder. Use the decoded token URL as the cheap oracle candidate, but label it `embedded-token target` until a live Turnstile/timer article flow proves downstream success.

## Next implementation order

1. `sfl.gl`: highest confidence; final `https://google.com` is reproducible browserlessly from ready page after API flow.
2. `aii.sh`: handler already extracts a stable decoded token target; improve tests/fixtures and wording.
3. `exe.io`: map is clear, but needs captcha solver integration before claiming final.
4. `gplinks.co`: needs more JS contract work around PowerGam `/track/data.php` and 3-step ad-impression state before final can be proven.
