# Changelog

## 2026-04-24

### cuty live helper and lnbz browserless handler
- Added `cuty_live_browser.py`, a CDP Chrome helper for the `cuty.io` -> `cuttlinks.com` flow.
- The Cuty handler now uses the local Turnstile solver API, submits the captcha in the same browser context, waits through the final page, and only returns success after navigating to the downstream target.
- Live verification on `https://cuty.io/AfaX6jx` returned `https://www.google.com/`.
- Added `lnbz.la` browserless article-chain handler for sample `Hmvp6`.
- The LNBZ handler follows the same-session `avnsgames.com` article/survey forms, waits the final 15s timer, then posts `/links/go`.
- Live verification on `https://lnbz.la/Hmvp6` returned `https://cryptoearns.com/links/back/AaDZLgKQsnhy423EIS9c`.
- Restored the local `turnstile-solver-api.service` repo/runtime after its configured working directory was missing and the service was crash-looping.

### ez4short fast live handler
- Added `ez4short.com` browserless fast lane for sample `qSyPzeo`.
- The handler uses `Referer: https://game5s.com/` to unlock a fresh final `form#go-link` directly on `ez4short.com`.
- It preserves same-session `AppSession`, `csrfToken`, and `app_visitor`, waits the final timer, and posts hidden fields to `/links/go`.
- Live verification on `https://ez4short.com/qSyPzeo` returned `https://tesskibidixxx.com`.
- Deep probe evidence is recorded in `references/probes/2026-04-24-ez4short-deep.md`.

### gplinks PowerGam partial mapper
- Added a `gplinks.co` handler that uses TLS impersonation to pass the entry Cloudflare layer and reach `powergam.online`.
- The handler decodes the PowerGam query contract:
  - `lid` -> alias
  - `pid` -> publisher id
  - `pages` -> required step count
  - `vid` -> visitor id token
- It parses the `adsForm`, computes the JS `target_final_candidate`, and returns `POWERGAM_STEPS_MAPPED` honestly as partial support.
- Deep replay evidence is recorded in `references/probes/2026-04-24-gplinks-deep.md`.
- Current blocker: naive 3-step replay reaches the computed final candidate but `gplinks.co` rejects it with `error_code=not_enough_steps`, so a missing ad-impression/conversion contract still needs browser instrumentation.

### tpi/aii token handlers and sfl live handler
- Generalized the old `oii.la` hidden-token extraction into a shared token landing handler.
- Added `tpi.li` routing; sample `Dd5xka` now returns `https://99faucet.com/links/back/haBKjYrugRxDIVCpGqMo` from the decoded token tail.
- Added `aii.sh` routing; sample `CBygg8fn2s3` now returns `https://coinadster.com/shortlink.php?short_key=1cnd9hq0nfbem5dr8vrmaz17f44pvh9a` from the ShrinkBixby hidden token.
- Added a browserless `sfl.gl` SafelinkU API flow:
  - parses entry `ray_id` and `alias`
  - follows `app.khaddavi.net/redirect.php`
  - calls `/api/session`, waits the step timer, calls `/api/verify`, then `/api/go`
  - fetches the ready page and extracts `window.location.href`
- Live verification on `https://sfl.gl/18PZXXI9` returned the expected final target `https://google.com`.

### Tests
- Added `tests/test_token_landing.py` for `tpi.li` and `aii.sh` token extraction.
- Added `tests/test_sfl.py` for ready-page extraction and the mocked SafelinkU API flow.
- Verification: `python -m unittest discover -s tests -p 'test*.py' -v` passed with 19 tests.

### Boskuu target sample catalog captured
- Added `references/target-sample-catalog.md` as the durable sample-to-final-target map for the next handler expansion work.
- Captured the new sample batch:
  - `oii.la/BW8ntz` -> `onlyfaucet.com/links/back/.../LTC/...`
  - `xut.io/hd7AOJ` -> `tesskibidixxx.com`
  - `tpi.li/Dd5xka` -> `99faucet.com/links/back/...`
  - `ez4short.com/qSyPzeo` -> `tesskibidixxx.com`
  - `cuty.io/AfaX6jx` -> `google.com`
  - `gplinks.co/YVTC` -> `tesskibidixxx.com`
  - `sfl.gl/18PZXXI9` -> `google.com`
  - `exe.io/vkRI1` -> `google.com`
  - `aii.sh/CBygg8fn2s3` -> target discovery pending
- Synced `ROADMAP.md`, `README.md`, and `references/shortlink-family-initial-map.md` so future work starts from the same oracle list.

### Guardrail
- These entries are target oracles only. Do not mark a family as supported until the engine returns the expected final target or a directly equivalent downstream URL.

## 2026-04-21

### xut/autodime warm-handoff lane wired into engine
- Added `xut_live_browser.py` as the first live helper for the `xut -> autodime -> gamescrate` lane.
- The helper now:
  - solves the live IconCaptcha Step 1 through the local solver API
  - drives the same Chromium session through Step 2, Step 3, and Step 4
  - hands the warmed browser over to the patched local FlareSolverr attach mode through `debuggerAddress`
  - reuses the current `gamescrate` page instead of restarting from a fresh browser
- `engine.py` now calls this helper for the autodime/xut family when the helper runtime is available.
- Important guardrail kept intact:
  - if the helper still does **not** reach the downstream `onlyfaucet.com/links/back/...` oracle, the engine returns a partial live-progress result instead of falsely claiming success.
- Added regression coverage so the xut handler can now surface either:
  - partial live progress from the handoff lane, or
  - a final bypass URL if a future run really closes the oracle.

### xut/autodime partial-support wording fix
- Reproduced the live `https://xut.io/3lid` lane again and confirmed the current implementation still stops at the Step 1 IconCaptcha boundary.
- Fresh live browser proof still lands on `Step 1/6`, renders the IconCaptcha strip, and populates:
  - `_iconcaptcha-token`
  - `ic-rq`
  - `ic-wid`
  - `ic-cid`
- Root cause of the confusing bot reply was not a broken sample alias. The engine for this family is still intentionally partial and returns `ICONCAPTCHA_STEP1_MAPPED` before any final `onlyfaucet.com/links/back/...` oracle is proven.
- Updated bot output so non-final results are labeled clearly as:
  - `Status: Partial / belum final bypass`

### xut/autodime live progression breakthrough
- Switched from manual guessing to the real IconCaptcha lane and replayed live browser captures from `https://xut.io/3lid`.
- Confirmed that the existing local/public IconCaptcha solver can process the canvas, but its current heuristic is not reliable for this autodime variant. The solver repeatedly chose a wrong cell on sampled live challenges.
- Captured the real Step 1 request contract more tightly:
  - initial challenge load posts `action = LOAD` to `/cwsafelinkphp/sl-iconcaptcha-request.php`
  - a user click posts `action = SELECTION` to the same endpoint with coordinates like `x`, `y`, and `width`
  - when the selection is wrong, the response does **not** return `completed=true`; the widget resets and loads a new challenge
- Ran live cell brute-force on fresh challenges and proved that at least one valid selection advances beyond Step 1.
- New proven downstream progression for the sample lane:
  - `Step 1/6` on `autodime.com`
  - `Step 2/6` on `autodime.com/blog/...`
  - `Step 3/6` on `textfrog.com/links/...`
  - `Step 4/6` on another `textfrog.com/links/...`
  - handoff into `https://gamescrate.app/cwsafelinkphp/setcookie.php?t=...`
- New blocker after the progression breakthrough:
  - `gamescrate.app` is now the active boundary
  - browser trace reaches the `setcookie.php?t=...` lane, but then sits on Cloudflare `Just a moment...`
  - browserless `curl_cffi` impersonation against that `gamescrate` lane still returned `403` / Cloudflare challenge, so the easy HTTP shortcut is not proven yet

### xut/autodime solver consistency and same-session replay update
- Found that the local `indra-api-hub` IconCaptcha endpoint was still exposing the old default grouping threshold `5.0`, which made the live autodime solver lane inconsistent across fresh challenges.
- Updated the shared IconCaptcha defaults to `20.0` and restarted the local hub so the live API now returns the newer grouping threshold.
- Fresh live proof after the reload:
  - Step 1 can now auto-advance to `Step 2/6` through the local solver API in a real browser session
  - one verification run solved on the first attempt and reached `https://autodime.com/blog/...` `Step 2/6`
  - another verification run solved within three attempts on live refreshed challenges
- New same-session replay proof:
  - a single Chromium session can now be driven from `xut.io/3lid` through Step 1, Step 2, Step 3, and Step 4 again after the solver reload
  - the same session still lands on `https://gamescrate.app/cwsafelinkphp/setcookie.php?t=...`
  - final page state remains `Just a moment...`
- Deeper `gamescrate` DOM probe from the warmed headless session:
  - the page DOM does **not** expose a normal iframe or checkbox element at probe time
  - instead it shows a hidden placeholder input `name="cf-turnstile-response"` under container `#GQTnq7`
  - page source also loads `/cdn-cgi/challenge-platform/.../orchestrate/chl_page/...`
- New click-boundary proof on `gamescrate`:
  - blind clicking the **left side** of `#GQTnq7` changes the body text from `Performing security verification` to `Verifying you are human. This may take a few seconds.`
  - clicking the center of the same box does **not** cause that state change
  - this proves the live Cloudflare widget is spatially present and reacts to pointer input even when Selenium cannot find a normal checkbox selector
- Practical meaning:
  - the Step 1 boundary is weaker now and partly automatable
  - the active hard blocker remains the downstream `gamescrate` Cloudflare managed challenge, but the boundary is now narrower: widget interaction is possible, selector visibility is the problem

### Files changed
- `bot.py`
  - non-success results now explicitly show that the lane is partial instead of looking like a generic failed live bypass

### Guardrail
- Do not present `xut.io` as a solved family until the handler actually crosses the `gamescrate` Cloudflare gate and reaches the downstream `onlyfaucet.com/links/back/...` oracle.

## 2026-04-18

### xut.io initial family mapping
- Added first structured notes for sample `https://xut.io/3lid`.
- Verified that `xut.io` is not yet its own final engine family. The tested alias immediately redirects into `https://autodime.com/cwsafelinkphp/go.php?link=snpurl%2F3lid`.
- Verified the current warmup chain:
  - `xut.io` sets `AppSession` and `ref3lid`
  - `autodime ... go.php` sets short-lived cookie `fexkomin`
  - that response then redirects to a Google wrapper for `https://autodime.com/`
  - replaying `https://autodime.com/` with the warmed cookies and Google referer yields live page `Step 1/6`
- Captured the active gate facts from the live step page:
  - countdown `10s`
  - captcha provider `iconcaptcha`
  - endpoints `/cwsafelinkphp/sl-iconcaptcha-request.php` and `/cwsafelinkphp/sl-iconcaptcha-verify.php`
  - path-scoped session cookie `CWSLSESSID`
- Recorded Boskuu's provided downstream success oracle for this sample:
  - `https://onlyfaucet.com/links/back/s7tM4CWuTNyfUkOLoqjR/USDT/b67127d45564acfeb4ef509e8a682ff5`

### Files changed
- `ROADMAP.md`
  - added `xut.io` into tracked scope and current known facts
- `references/shortlink-family-initial-map.md`
  - added initial wrapper-family map for `xut.io -> autodime cwsafelinkphp`

### xut/autodime Step 1 load contract verified
- Re-checked the earlier Step 1 IconCaptcha assumption with a real Chromium capture plus an out-of-browser replay.
- Verified the first `LOAD` request contract is narrower than expected:
  - real request goes to `/cwsafelinkphp/sl-iconcaptcha-request.php`
  - it uses `X-Requested-With: XMLHttpRequest`
  - it also requires `X-IconCaptcha-Token` mirroring the hidden `_iconcaptcha-token`
  - the warmed browser cookie jar must include path-scoped `CWSLSESSID` for `/cwsafelinkphp/`
- Verified replay behavior split:
  - same warmed session **without** `X-IconCaptcha-Token` decodes to `invalid form token`
  - same warmed session **with** `X-IconCaptcha-Token` returns a normal challenge JSON again, including `identifier`, `challenge`, `expiredAt`, and `timestamp`
- Practical meaning:
  - the old `404 route not found` conclusion was incomplete
  - the first IconCaptcha `LOAD` step is replayable outside the browser if the request contract matches the real browser state closely enough
  - the remaining blocker has moved forward to `SELECTION` and `sl-iconcaptcha-verify.php`, not the initial challenge load itself

### Files changed
- `ROADMAP.md`
  - synced the new Step 1 contract and moved the xut blocker from `browser-only load` to `selection + verify`
- `references/shortlink-family-initial-map.md`
  - recorded the verified `CWSLSESSID + X-IconCaptcha-Token` replay contract

### Why this exists
- Boskuu supplied a new shortlink sample and the expected final downstream URL.
- Before writing a handler, the stronger evidence was to map the real wrapper family and its first hard gates.

### Guardrail
- Do not claim `xut.io` support yet.
- A future handler should only call this family `supported` after it reaches the final downstream `onlyfaucet.com/links/back/...` style oracle, not just the Google warmup redirect or the `Step 1/6` page.

### xut/autodime initial engine handler
- Added a first real engine handler for `xut.io` and direct `autodime.com/cwsafelinkphp/go.php` URLs.
- The new handler normalizes both entry styles into family `autodime.cwsafelinkphp`.
- It replays the currently proven warmup chain:
  - wrapper entry
  - `go.php`
  - Google wrapper decode
  - `https://autodime.com/` step page fetch
- It now returns a structured partial result instead of `UNSUPPORTED_FAMILY`:
  - `message = ICONCAPTCHA_STEP1_MAPPED`
  - `stage = step1-iconcaptcha`
- Added regression tests for both entry styles so the new family mapping does not silently disappear.

### Files changed
- `engine.py`
  - added autodime/xut family detection and step1 warmup handler
  - added parsing for `step`, `countdown`, `captchaProvider`, `iconcaptchaEndpoint`, and `verifyUrl`
  - added helper decoding for Google wrapper redirects and signed JSON-style cookies like `fexkomin`
- `tests/test_xut.py`
  - added regression coverage for `xut.io` wrapper entry and direct `autodime` go URL entry
- `README.md`, `ROADMAP.md`
  - synced support table and live milestone wording for the new handler

### Why this exists
- Boskuu asked to gas the new family after the initial mapping was done.
- The strongest honest next step was turning the mapping into a real handler without pretending the IconCaptcha gate was already solved.

## 2026-04-16

### shrinkme.click final chain fix
- Fixed the `shrinkme.click` handler so it no longer reports the first ThemeZon article as a successful bypass.
- Added a full HTTP replay for the verified chain:
  - `shrinkme.click/<alias>`
  - `themezon.net/link.php?link=<alias>`
  - ThemeZon next-hop POST `newwpsafelink=<alias>`
  - `en.mrproblogger.com/<alias>`
  - final AJAX POST to `/links/go`
- Verified live on sample `https://shrinkme.click/ZTvkQYPJ`.
- Verified final downstream result:
  - `https://claimcoin.in/links/back/kPw2COhFxD0pfQuGrXUz`

### Files changed
- `engine.py`
  - touched `_handle_shrinkme(...)`
  - added `_resolve_shrinkme_mrproblogger(...)`
  - now waits the observed MrProBlogger timer and submits the hidden final form before claiming success
- `tests/test_shrinkme.py`
  - added regression coverage so ThemeZon intermediate URLs stay non-final
  - added success coverage for the final claimcoin result
- `README.md`
  - support table now marks `shrinkme.click` as a live bypass lane
- `ROADMAP.md`
  - synced new shrinkme milestone and current next action
- `references/shortlink-family-initial-map.md`
  - recorded the verified ThemeZon -> MrProBlogger -> `/links/go` chain

### Why this exists
- User report showed the bot was returning a wrong intermediate URL like:
  - `https://themezon.net/what-is-linux-managed-vps/`
- That URL is only an interstitial article, not the reward-site target.
- The real success oracle for this sampled lane is the JSON response from `MrProBlogger /links/go`, not the first ThemeZon page.

### Guardrail
- Do not downgrade shrinkme success back to `ThemeZon` article extraction only.
- A result is only `status=1` if the final downstream URL is actually returned from the last `MrProBlogger /links/go` step.

### speed optimization pass
- Added a browserless `link.adlink.click` fast lane using `curl_cffi` TLS impersonation against `blog.adlink.click`.
- Kept `adlink_live_browser.py` only as fallback when the faster browserless lane fails.
- Added a direct `shrinkme.click` shortcut that starts from `https://en.mrproblogger.com/<alias>` with `Referer: https://themezon.net/` instead of replaying every ThemeZon hop first.
- Tightened the final wait windows based on live lower-bound probing:
  - `link.adlink.click` sample `CBr27fn4of3` now succeeds around `4.0s` after the blog page load
  - `shrinkme.click` sample `ZTvkQYPJ` now succeeds around `11.2s` to `11.6s` after the MrProBlogger page load

### Files changed
- `engine.py`
  - added `_resolve_adlink_http(...)`
  - added `_resolve_shrinkme_direct_mrproblogger(...)`
  - now prefers the faster browserless Adlink lane before falling back to Chromium
  - now prefers the direct MrProBlogger shortcut for shrinkme before the longer ThemeZon replay path
- `adlink_live_browser.py`
  - added faster direct blog-form submission so the fallback browser lane wastes less time
- `requirements.txt`
  - added `curl_cffi`
- `tests/test_adlink.py`
  - added regression coverage for Adlink fast-lane selection and browser fallback
- `tests/test_shrinkme.py`
  - added regression coverage for the direct MrProBlogger shortcut
- `README.md`, `ROADMAP.md`, `docs/FLOWS.md`, `references/shortlink-family-initial-map.md`
  - synced the new fast lanes, timer boundaries, and fallback rules

### Why this exists
- The earlier engine still spent too much time on avoidable hops:
  - Adlink kept launching a full browser even when a browserless TLS-impersonated blog hit was enough
  - ShrinkMe still replayed longer ThemeZon steps even though the real bottleneck lived at MrProBlogger
- The new code cuts that waste while keeping the same success oracle discipline.

### Guardrail
- Do not regress Adlink back to browser-only as the default unless TLS impersonation stops working on live samples.
- Do not assume `ad_form_data` can be replayed across sessions for ShrinkMe. The speed win comes from same-session early fetch plus tighter wait windows, not from cross-session blob reuse.

### Telegram access gate and command UX
- Added a required-join gate in `bot.py` so users must join the Telegram group `Cari Garapan` before they can use the bot.
- Added inline button flow for the gate:
  - `Join Cari Garapan`
  - `Sudah join, cek lagi`
- Added better command UX:
  - `/start`
  - `/help`
  - `/status`
  - `/ping`
  - plain URL messages now auto-route to `/bypass`
- Synced `.env.example` and live env usage so the required group can be configured with:
  - `SHORTLINK_REQUIRED_JOIN_CHAT_ID`
  - `SHORTLINK_REQUIRED_JOIN_CHAT_TITLE`
  - `SHORTLINK_REQUIRED_JOIN_LINK`
- Added `tests/test_bot.py` for join-gate and command parsing coverage.

### Why this exists
- Boskuu moved the bot into a private usage flow and wants every user forced through the `Cari Garapan` group first.
- The older bot UX was still too bare: only minimal commands and no proper membership gate.

### Guardrail
- Keep the join requirement enforced through real `getChatMember` checks, not just a text warning.
- Do not silently remove the group gate from `bot.py` without replacing it with an equally strict membership check.
