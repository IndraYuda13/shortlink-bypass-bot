# Shortlink Family Initial Map

## Scope covered
- `link.adlink.click`
- `shrinkme.click`
- `oii.la`
- `xut.io` -> wrapper into `autodime.com/cwsafelinkphp`
- new sample batch captured in `references/target-sample-catalog.md`:
  - `tpi.li`
  - `ez4short.com`
  - `cuty.io`
  - `gplinks.co`
  - `sfl.gl`
  - `exe.io`
  - `aii.sh`
- foundation inventory for reusable solver/browser components

## What is already proven
### shrinkme.click
- Sample checked: `https://shrinkme.click/kVJMw`
- Sample checked: `https://shrinkme.click/ZTvkQYPJ`
- First response is `200 OK`, not an HTTP redirect.
- Initial cookies observed:
  - `AppSession`
  - `refkVJMw` with `Max-Age=300`
  - `csrfToken`
  - `app_visitor`
- Active captcha is **Google reCAPTCHA checkbox**.
- Sitekey observed in DOM:
  - `6LfFeLErAAAAAHYOQfqM3-7BpopXCbBQPAMEeh4B`
- JS config exposes:
  - `captcha_type: "recaptcha"`
  - `counter_value: 12`
  - `counter_start: "DOMContentLoaded"`
- Continue flow is custom and depends on `recaptchaCallback()` in the DOM, but server-side replay for the next hop is narrower than expected.
- After callback, the page rewrites `#div-human-verification` toward:
  - `https://themezon.net/link.php?link=kVJMw`
- Extra click monetization exists on `#invisibleCaptchaShortlink`.
- Popup/ad URL observed:
  - `https://crn77.com/4/4834392`
- `targetClickCount: 2`
- External hop sets cookie `tp=kVJMw` with `Max-Age=180`.
- Proven narrower lane on sample `kVJMw`:
  - `GET https://themezon.net/link.php?link=kVJMw` succeeds without a captcha token when sent with `Referer: https://shrinkme.click/kVJMw`
  - wrong referer returns `Invalid Access, Go to the shorten page.(https://shrinke.me/alias)`
  - success response yields a JS redirect to either a Google wrapper whose `url=` is a ThemeZon article, or to `https://themezon.net/?redirect_to=random` which then `307`s to a ThemeZon article
- Observed ThemeZon article targets include:
  - `https://themezon.net/what-is-linux-managed-vps/`
  - `https://themezon.net/host-my-website/`
- New replay proof for sample `ZTvkQYPJ`:
  - load `https://themezon.net/link.php?link=ZTvkQYPJ` with `Referer: https://shrinkme.click/ZTvkQYPJ`
  - extract ThemeZon article URL from the JS redirect / `307 Location`
  - advance ThemeZon once with `POST https://themezon.net/?redirect_to=random` and `newwpsafelink=ZTvkQYPJ`
  - final external hop resolves as `https://en.mrproblogger.com/ZTvkQYPJ`
  - `GET` to that page works when the referer is the ThemeZon article chain, and the page exposes hidden form `id="go-link"` with `action="/links/go"`
  - after the observed `12s` timer, `POST /links/go` returns JSON success with:
    - `https://claimcoin.in/links/back/kPw2COhFxD0pfQuGrXUz`
- Timer boundary narrowed harder for sample `ZTvkQYPJ`:
  - fresh-session direct `GET https://en.mrproblogger.com/ZTvkQYPJ` with forged `Referer: https://themezon.net/` is enough to expose the `go-link` form, even without touching `shrinkme.click`, `themezon.net/link.php`, or `themezon.net/?redirect_to=random`
  - non-ThemeZon referers like `https://google.com/` or `https://en.mrproblogger.com/anything` bounce back to `https://shrinkme.click/ZTvkQYPJ`
  - server-side lower bound is not a hard 12-13s wall: controlled replays showed `11.3s` after MrProBlogger page load still fails with `{"status":"error","message":"Bad Request."}` while `11.4s` to `11.5s+` can already succeed, with some jitter around the boundary
  - practical safe wait for raw HTTP replay is about `11.6s` from successful MrProBlogger page fetch, not `13s`
  - hidden `ad_form_data` is not worth decoding for speed: cross-session replay of the blob fails with `CSRF token mismatch`, so the useful trick is obtaining a fresh same-session form early, not reverse-engineering the blob
  - same-session repeated submit after the timer succeeds more than once, so the gate is mainly session timer + CSRF, not one-time nonce burn
- Current success oracle for this lane is now: a successful `MrProBlogger /links/go` response that returns a downstream `.../links/back/...` URL. ThemeZon article extraction alone is only intermediate evidence.

### oii.la
- Samples checked:
  - `https://oii.la/TaVOKJleNN`
  - `https://oii.la/FOT3p2HAVb`
- New Boskuu-provided oracle sample captured for next live run:
  - `https://oii.la/BW8ntz` -> `https://onlyfaucet.com/links/back/vYal1NZ2dtDFTr5cXqUi/LTC/208faecab92bd6cc094014e046df165d`
- First response is `200 OK`, not an HTTP redirect.
- Initial cookie pattern observed:
  - `ref<alias>` with `Max-Age=300`
- Landing form posts to:
  - `https://advertisingcamps.com/taboola2/landing/`
- Hidden params observed:
  - `url=https://oii.la/<alias>`
  - `token=...`
  - `mysite=clk.sh`
  - `c_d=<yyyymmdd>`
  - `c_t=<epoch-like value>`
  - `alias=<alias>`
- Token tail decodes to downstream targets proven on tested samples:
  - `TaVOKJleNN` -> `https://99faucet.com/links/back/SNcKa7f52qRk4xiA1gl6`
  - `FOT3p2HAVb` -> `https://claimcrypto.cc/links/back/wvCF7sRItpKGM2XrhoOj`
- Active captcha config is **Cloudflare Turnstile**.
- Sitekey observed:
  - `0x4AAAAAABatM0GOBpAxBoeD`
- JS config exposes:
  - `captcha_type: "turnstile"`
  - `captcha_shortlink: "yes"`
  - `counter_value: 15`
  - `counter_start: "load"`
- Live browser DOM proof:
  - widget injects hidden input `name="cf-turnstile-response"` inside the form
  - Continue button starts disabled and is enabled by the Turnstile callback only on the client side
- Important server-side finding from tested samples:
  - POST to `https://advertisingcamps.com/taboola2/landing/` returned the same `302 -> https://www.taboola.com` both with and without captcha fields
  - so this POST currently looks like an ad handoff, not the real success oracle for the downstream `links/back/...` URL
- Page also contains stale inline `grecaptcha` helpers, but active runtime config is Turnstile.
- Adblock gate exists via fetch to:
  - `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js`

### tpi.li
- Sample checked:
  - `https://tpi.li/Dd5xka`
- Shape matches the `oii.la` token-tail Turnstile landing family:
  - `200 OK` entry page
  - `refDd5xka` cookie
  - form action `https://advertisingcamps.com/taboola1/landing/`
  - active Turnstile config with `counter_value=15` and `counter_start=load`
- Hidden `token` decodes to the expected final oracle:
  - `https://99faucet.com/links/back/haBKjYrugRxDIVCpGqMo`
- Engine status:
  - supported as analysis-only token extraction via shared token landing handler
  - not a proven live captcha/timer completion lane

### aii.sh
- Sample checked:
  - `https://aii.sh/CBygg8fn2s3`
- Shape is ShrinkBixby token-tail Turnstile landing:
  - `200 OK` entry page
  - `refCBygg8fn2s3` and `visit_token` cookies
  - form action rotates through `techbixby.com` article pages
  - active Turnstile config with `counter_value=15` and `counter_start=load`
- Hidden `token` has suffix noise after the base64 URL, but the shared decoder now extracts:
  - `https://coinadster.com/shortlink.php?short_key=1cnd9hq0nfbem5dr8vrmaz17f44pvh9a`
- Engine status:
  - supported as analysis-only token extraction
  - not a proven live Turnstile/timer completion lane

### sfl.gl
- Sample checked:
  - `https://sfl.gl/18PZXXI9`
- Browserless lane uses `curl_cffi` TLS impersonation.
- Proven flow:
  1. entry page exposes form to `https://app.khaddavi.net/redirect.php` with `ray_id` and `alias`
  2. redirect lands on a rotating `app.khaddavi.net` article
  3. `POST /api/session` returns `step=1`, `captcha=null`, `passcode=false`
  4. wait the real step timer, currently `10s` for step 1
  5. `POST /api/verify` with boolean `_a=true`
  6. `POST /api/go` returns `https://sfl.gl/ready/go?...`
  7. ready page embeds final target in `window.location.href`
- Live verification on the sample returned:
  - `https://google.com`
- Engine status:
  - live bypass supported for the sampled no-captcha SafelinkU path

### ez4short.com
- Sample checked:
  - `https://ez4short.com/qSyPzeo`
- Full frontend family is a multi-domain `newwpsafelink` chain:
  - `ez4short -> tech8s safe/article POST -> game5s safe/article POST -> ez4short final go-link`
- Fast lane now proven:
  1. `GET https://ez4short.com/qSyPzeo` with `Referer: https://game5s.com/`
  2. parse fresh same-session `form#go-link`
  3. preserve `AppSession`, `csrfToken`, and `app_visitor`
  4. wait the final page timer, currently `3s` plus safety margin
  5. `POST https://ez4short.com/links/go` with hidden CakePHP fields
- Live verification on the sample returned:
  - `https://tesskibidixxx.com`
- Engine status:
  - live bypass supported for the sampled fast referer path

### gplinks.co
- Sample checked:
  - `https://gplinks.co/YVTC`
- Browserless lane with TLS impersonation can pass entry Cloudflare and reach PowerGam.
- PowerGam query values decode as:
  - `lid` -> alias `YVTC`
  - `pid` -> publisher id `1224622`
  - `pages` -> required step count `3`
  - `vid` -> visitor id token
- The JS computes a target candidate:
  - `https://gplinks.co/YVTC?pid=1224622&vid=<vid>`
- Current blocker:
  - naive 3-step form replay reaches that candidate but server rejects with `error_code=not_enough_steps`
  - missing proof likely lives in ad-impression/conversion state around `gplinks.com/track/data.php` or third-party ad callbacks
- Engine status:
  - partial mapper only, not final bypass support

### cuty.io / cuttlinks.com
- Sample checked:
  - `https://cuty.io/AfaX6jx`
- Entry redirects to:
  - `https://cuttlinks.com/AfaX6jx?auth_token=...`
  - then `https://cuttlinks.com/AfaX6jx`
- Proven live flow:
  1. first page exposes `form#free-submit-form` and `Continue`
  2. first submit returns Turnstile page with sitekey `0x4AAAAAAABnHbN4cNchLhd_`
  3. local Turnstile solver API returns a valid `cf-turnstile-response` token
  4. same browser context submits captcha form and reaches `last.js` page with `form#submit-form action=https://cuttlinks.com/go/AfaX6jx`
  5. final submit leaves Cuty/Cuttlinks and lands on `https://www.google.com/`
- Engine status:
  - live bypass supported for the sampled Cuty/Cuttlinks path via `cuty_live_browser.py`
  - success is only claimed after the browser actually navigates to the downstream host

### lnbz.la
- Sample checked:
  - `https://lnbz.la/Hmvp6`
- Proven browserless flow:
  1. `GET /Hmvp6` sets `refHmvp6` and `visit_token` and returns an entry form to a rotating `avnsgames.com` article
  2. submit entry form to `avnsgames.com`
  3. submit two `form#go_d2` article/survey steps
  4. return to `https://lnbz.la/Hmvp6` and parse final `form#go-link`
  5. wait the final 15s timer with a safe 16s margin
  6. `POST https://lnbz.la/links/go` returns the downstream URL
- Live verification on the sample returned:
  - `https://cryptoearns.com/links/back/AaDZLgKQsnhy423EIS9c`
- Engine status:
  - live browserless bypass supported for the sampled article-chain path

### link.adlink.click
- Samples checked:
  - `https://link.adlink.click/CBuahny8kxt`
  - `https://link.adlink.click/SfRi`
  - `https://link.adlink.click/VnLS`
  - `https://link.adlink.click/Zy6W`
  - `https://link.adlink.click/6Omf`
- HTTP entry normalizes `http -> https` via `301`.
- Static/raw-request entry is blocked by **Cloudflare managed challenge** before site-specific shortlink logic is visible.
- Proven pre-origin facts from raw request:
  - response status `403`
  - page title `Just a moment...`
  - header `Cf-Mitigated: challenge`
  - challenge bootstrap hits `/cdn-cgi/challenge-platform/.../orchestrate/chl_page/...`
  - ephemeral params observed: `__cf_chl_tk`, `__cf_chl_f_tk`, `__cf_chl_rt_tk`
- New live-browser proof for multiple samples:
  - one-shot FlareSolverr HTTP API on this VPS timed out at `60s` and `120s`
  - direct browser lane using `undetected-chromedriver` + `xvfb-run` + `page_load_strategy=none` **did** get out of `link.adlink.click`
  - samples live-tested successfully:
    - `6Omf`
    - `VnLS`
    - `SfRi`
    - `CBuahny8kxt`
  - first visible redirect after Cloudflare matches this pattern:
    - `https://www.maqal360.com/secure.php?id=<alias>&site=adlink.click`
  - `maqal360` is an interstitial chain, not the final success oracle
  - proven fast lane for sample `SfRi`:
    1. pass Cloudflare until the browser leaves `link.adlink.click`
    2. once the shared browser session is alive, jump directly to `https://blog.adlink.click/<alias>`
    3. wait for the AdLinkFly page to render
    4. extract `a.get-link`
  - benchmark from local probe:
    - `SfRi` can reach the final `earn-pepe` verify URL in about `13s`
- New browserless proof on this VPS with TLS impersonation:
  - after installing `curl_cffi` and `cloudscraper` into the repo venv, both libraries can hit `https://link.adlink.click/<alias>` without Selenium and receive normal `302` redirects instead of Cloudflare `403`
  - proven redirect chain for sample `CBr27fn4of3`:
    1. `GET https://link.adlink.click/CBr27fn4of3`
    2. `302 -> https://www.maqal360.com/secure.php?id=CBr27fn4of3&site=adlink.click`
    3. `302 -> https://www.google.com/url?...url=https://www.maqal360.com/single-post.php?id=advice-for-successful-trading-of-cryptocurrencies`
  - stronger shortcut: cold `GET https://blog.adlink.click/<alias>` works browserlessly too **if** the request uses TLS impersonation and a `Referer` on `https://www.maqal360.com/`
  - plain `requests` and plain `curl` still fail there with `403 Just a moment...`, so the delta is not just headers or cookies, it is the client fingerprint / challenge handling path
  - browserless direct-blog samples proven with `curl_cffi impersonate='chrome136'`:
    - `SfRi` -> `POST https://blog.adlink.click/links/go` after ~`6s` returns `https://earn-pepe.com/member/shortlinks/verify/ca7c179027eb04abfb79`
    - `VnLS` -> same pattern returns `https://99faucet.com/links/back/mfEPnvjHl5JOaZSRLD4M`
    - `CBr27fn4of3` -> same pattern returns `https://bitcointricks.com/shortlink.php?short_key=fu8dbowmwyx1q1f9et8qmao3o9r5wfu4`
  - required page facts on `blog.adlink.click/<alias>`:
    - title `adlink`
    - form action `/links/go`
    - hidden `ad_form_data`
    - runtime `counter_value = 5`
    - runtime `captcha_type = securimage`
  - on the proven samples above, `/links/go` succeeded without solving any extra captcha field, as long as the session came from impersonated HTTP and the wait budget exceeded the 5 second timer
  - slower fallback lane still exists if the fast lane ever fails:
    1. wait around `10s` on each `maqal360` article page
    2. call same-origin `verify.php`
    3. if JSON returns `{"status":"ok","url":"..."}`, navigate to that next URL
    4. repeat until final gate `GO NEXT 7/7`
    5. final `verify.php` may return `{"status":"error"}` even though the flow is still recoverable
    6. from that final `maqal360` page, navigate in the same browser session to `https://blog.adlink.click/<alias>`
    7. wait for the AdLinkFly page to fully render, then extract `a.get-link`
  - proven DOM oracle on `https://blog.adlink.click/SfRi`:
    - page title `adlink`
    - `form action="/links/go"`
    - hidden input `name="ad_form_data"`
    - anchor text `Get Link`
    - anchor href `https://earn-pepe.com/member/shortlinks/verify/ca7c179027eb04abfb79`
- Important interpretation:
  - for this family on Rawon, the blocker was not that the lane is impossible
  - the blocker was that raw HTTP and one-shot FlareSolverr API calls were the wrong execution lane for this sample
  - the earlier bot bug came from stopping at the first visible `maqal360` article instead of continuing the interstitial chain through the shared browser session

### xut.io -> autodime cwsafelinkphp
- Sample checked:
  - `https://xut.io/3lid`
- Boskuu already supplied the expected downstream final for this sample:
  - `https://onlyfaucet.com/links/back/s7tM4CWuTNyfUkOLoqjR/USDT/b67127d45564acfeb4ef509e8a682ff5`
- Entry behavior is a true HTTP redirect, not an HTML page:
  - `302 -> https://autodime.com/cwsafelinkphp/go.php?link=snpurl%2F3lid`
- Initial cookies observed on `xut.io`:
  - `AppSession`
  - `ref3lid` with `Max-Age=300`
- First `autodime` handoff currently behaves like an anti-bot / warmup step:
  - request to `.../go.php?link=snpurl%2F3lid` sets cookie `fexkomin`
  - same response then `302`s to a Google wrapper URL whose `url=` points to `https://autodime.com/`
- Decoded `fexkomin` payload on the tested sample contained:
  - `step = 1`
  - `sid = /3lid`
  - short-lived `iat/exp`
  - `nonce`
  - `fp` fingerprint hash
- After replaying `https://autodime.com/` with the warmed cookie jar and a Google referer, the live page becomes:
  - title `Step 1/6`
  - subtitle `Preparing a secure redirect. When the timer ends, solve the captcha to continue.`
- Runtime config observed in DOM:
  - `countdown: 10`
  - `captchaProvider: 'iconcaptcha'`
  - `iconcaptchaEndpoint: '/cwsafelinkphp/sl-iconcaptcha-request.php'`
  - `verifyUrl: '/cwsafelinkphp/sl-iconcaptcha-verify.php'`
- Browser-context proof now exists for the first IconCaptcha load request:
  - after the 10s countdown and the initial widget click in a real Chromium session, the page posts to `/cwsafelinkphp/sl-iconcaptcha-request.php`
  - hidden fields become populated with `ic-rq`, `ic-wid`, and `ic-cid`
  - the live browser request carries `X-Requested-With: XMLHttpRequest` plus `X-IconCaptcha-Token: <_iconcaptcha-token>`
  - the warmed browser cookie jar also includes path-scoped session cookie `CWSLSESSID` under `/cwsafelinkphp/`
- Verified external replay contract for `LOAD`:
  - earlier bare `requests` and `curl_cffi` probes that only reused the warmup step-page cookies were incomplete and misleading
  - when the replay uses the full browser session state, especially `CWSLSESSID` + `_iconcaptcha-token` mirrored into `X-IconCaptcha-Token`, raw HTTP replay to `/cwsafelinkphp/sl-iconcaptcha-request.php` works outside the browser
  - same warmed session without `X-IconCaptcha-Token` decodes into an `invalid form token` error
  - same warmed session with `X-IconCaptcha-Token` returns a normal IconCaptcha challenge JSON again, including `identifier`, `challenge`, `expiredAt`, and `timestamp`
- Captcha form facts:
  - hidden input `_iconcaptcha-token`
  - widget class `.iconcaptcha-widget`
  - cookie `CWSLSESSID` is set under path `/cwsafelinkphp/`
- Important interpretation:
  - `xut.io` itself looks like a thin wrapper / alias entry point
  - the real technical family is probably the reusable `autodime cwsafelinkphp` step engine behind it
  - the earlier `404 route not found` conclusion was too early; the endpoint is replayable, but only after the request contract matches the real browser state closely enough
  - success is still not proven by the Google redirect, step page, or challenge load alone; the final oracle for this sample remains the downstream `onlyfaucet.com/links/back/...` URL above
- Current blocker:
  - Step 1 challenge load is now closed enough
  - the remaining hard blocker is the `SELECTION` solve plus the follow-up verify transition in `/cwsafelinkphp/sl-iconcaptcha-verify.php`
- Next best action:
  1. capture one valid `SELECTION` request and decode its payload structure
  2. replay `sl-iconcaptcha-verify.php` with the warmed `CWSLSESSID` + token contract
  3. check whether steps 2..6 collapse into simpler timed `nextUrl` or form posts once Step 1 is accepted

### Reusable workspace components
- Best solver/browser base:
  - `projects/hcaptcha-challenger-codex`
- Best Cloudflare/session helper:
  - `state/flaresolverr-exp/src`
- Current gap:
  - no site-family runner yet that chains shortlink entry -> cookie/session -> timer -> captcha -> verify/back -> downstream reward confirmation.

## Likely failure reasons already narrowed
### shrinkme.click
- `TIMEOUT`
  - reCAPTCHA callback never fires, so continue anchor is never generated
  - short-lived cookies (`ref*`, `tp`) expire before the flow finishes
- `ERROR_CAPTCHA_UNSOLVABLE`
  - real browser-context reCAPTCHA expectations are not satisfied

### oii.la
- `ERROR_CAPTCHA_UNSOLVABLE`
  - solver may target stale reCAPTCHA helpers while the active challenge is Turnstile
- `TIMEOUT`
  - Turnstile never enables `#continue`
  - cookie/token fields go stale
  - adblock gate or blocked scripts stop the page from progressing

### cuty.io / cuttlinks.com
- Sample checked:
  - `https://cuty.io/AfaX6jx`
- Entry redirects to:
  - `https://cuttlinks.com/AfaX6jx?auth_token=...`
  - then `https://cuttlinks.com/AfaX6jx`
- Proven live flow:
  1. first page exposes `form#free-submit-form` and `Continue`
  2. first submit returns Turnstile page with sitekey `0x4AAAAAAABnHbN4cNchLhd_`
  3. local Turnstile solver API returns a valid `cf-turnstile-response` token
  4. same browser context submits captcha form and reaches `last.js` page with `form#submit-form action=https://cuttlinks.com/go/AfaX6jx`
  5. final submit leaves Cuty/Cuttlinks and lands on `https://www.google.com/`
- Engine status:
  - live bypass supported for the sampled Cuty/Cuttlinks path via `cuty_live_browser.py`
  - success is only claimed after the browser actually navigates to the downstream host

### lnbz.la
- Sample checked:
  - `https://lnbz.la/Hmvp6`
- Proven browserless flow:
  1. `GET /Hmvp6` sets `refHmvp6` and `visit_token` and returns an entry form to a rotating `avnsgames.com` article
  2. submit entry form to `avnsgames.com`
  3. submit two `form#go_d2` article/survey steps
  4. return to `https://lnbz.la/Hmvp6` and parse final `form#go-link`
  5. wait the final 15s timer with a safe 16s margin
  6. `POST https://lnbz.la/links/go` returns the downstream URL
- Live verification on the sample returned:
  - `https://cryptoearns.com/links/back/AaDZLgKQsnhy423EIS9c`
- Engine status:
  - live browserless bypass supported for the sampled article-chain path

### link.adlink.click
- `TIMEOUT`
  - Cloudflare challenge is never cleared, so origin flow never starts
- `ERROR_CAPTCHA_UNSOLVABLE`
  - very possible if a bypass bot treats this like an origin captcha problem while the real first gate is Cloudflare managed challenge

## Boundary catalog
- `entry shortlink`
  - adlink: narrowed only up to Cloudflare challenge page
  - shrinkme: closed enough for sample `kVJMw`
  - oii: closed enough for sample `TaVOKJleNN`
- `redirect/session cookie gate`
  - adlink: primary, Cloudflare clearance
  - shrinkme: primary
  - oii: primary
- `timer/wait gate`
  - adlink: narrowed, `maqal360` needs about 10s before `verify.php` returns the next URL
  - shrinkme: narrowed, 12s DOMContentLoaded-based counter
  - oii: narrowed, 15s load-based counter
- `captcha gate`
  - adlink: primary at entry because of Cloudflare managed challenge, but `maqal360` chain for `SfRi` was proven to advance by timed `verify.php` and did not need solving the visible image captcha on steps 1-6
  - shrinkme: primary, reCAPTCHA checkbox
  - oii: primary, Turnstile
- `final verify/back endpoint`
  - adlink: narrowed enough for sample `SfRi`, with proven extracted downstream verify URL at `earn-pepe.com/member/shortlinks/verify/...`
  - shrinkme: narrowed enough for sample `ZTvkQYPJ`, with proven downstream URL at `claimcoin.in/links/back/...` after `MrProBlogger /links/go`
  - oii: narrowed, probable downstream `99faucet.com/links/back/...`
- `downstream reward-site callback/state mutation`
  - open for all three families

## New implementation milestone
- Core analyzer scaffold now exists at:
  - `projects/shortlink-bypass-bot/engine.py`
- Telegram wrapper scaffold now exists at:
  - `projects/shortlink-bypass-bot/bot.py`
- Current honest engine behavior:
  - can classify family by host
  - can detect Cloudflare-gated `adlink.click` entry state
  - can bypass sampled `link.adlink.click` aliases browserlessly by hitting `blog.adlink.click/<alias>` with TLS impersonation and replaying `/links/go`
  - can extract `oii.la` token-decoded downstream URL when it is embedded in hidden payload
  - can shortcut sampled `shrinkme.click` aliases directly through `MrProBlogger` with ThemeZon-style referer spoof
  - can replay the verified `shrinkme.click` chain through `ThemeZon` and `MrProBlogger` for sampled aliases
  - can extract entry-page facts, hidden inputs, timer/captcha hints, and embedded target URLs when they are statically recoverable
  - still keeps strict success oracles, so intermediate ThemeZon articles are not promoted as final bypass URLs anymore

## What is not yet proven
- Whether the final `blog.adlink.click` gate can always be recovered by direct alias navigation for all aliases, or only for the tested samples.
- Final reward-site success oracle per family beyond URL extraction.
- Broader post-Cloudflare origin flow coverage for more `link.adlink.click` samples beyond the current tested set.

## Next best action
1. Generalize the proven browserless `curl_cffi -> blog.adlink.click -> /links/go` lane across more `link.adlink.click` aliases and keep the live browser as fallback only.
2. Compare all three families for shared AdLinkFly-like boundaries versus custom wrappers.
3. Keep `oii.la` as the next high-value lane because token decoding already yields a downstream reward URL and Turnstile solver is ready locally.
4. Build a modular runner with pluggable captcha handler and strict success oracles.
