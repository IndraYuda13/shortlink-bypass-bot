# Probe notes: gplinks PowerGam deep pass

Date: 2026-04-24
Scope: `https://gplinks.co/YVTC` -> expected `http://tesskibidixxx.com`

## Summary

`gplinks.co/YVTC` is not a simple embedded-token family. `curl_cffi` can pass the entry Cloudflare layer and reach `powergam.online`, but the final server validation still rejects a naive 3-step replay with `not_enough_steps`.

## Confirmed entry contract

- `GET https://gplinks.co/YVTC` with Chrome TLS impersonation returns `302` to:
  - `https://powergam.online?lid=WVZUQw&pid=MTIyNDYyMg&vid=<base64-ish>&pages=Mw`
- Decoded query values:
  - `lid=WVZUQw` -> `YVTC`
  - `pid=MTIyNDYyMg` -> `1224622`
  - `pages=Mw` -> `3`
  - `vid` stays base64-ish in the URL and is decoded by JS only for some postback paths

## PowerGam JS contract

Fetched script:
- `https://api.gplinks.com/track/js/power-cdn.js?v=2.0.0.5`

Deobfuscated enough to confirm:

```js
mainDomain = 'gplinks.com'
redirectDomain = 'gplinks.co'
link_id = base64UrlDecode(query.lid)
pub_id = base64UrlDecode(query.pid)
pages = base64UrlDecode(query.pages)
visitor_id = query.vid

Cookies.set('lid', link_id)
Cookies.set('pid', pub_id)
Cookies.set('pages', pages)
Cookies.set('vid', visitor_id)
Cookies.set('step_count', 0)
Cookies.set('imps', 0)

target_final = 'https://' + redirectDomain + '/' + cookie_link_id + '?pid=' + cookie_pub_id + '&vid=' + cookie_visitor_id
next_status = cookie_step_count + 1
readyToGo = next_status >= stepsToGo
next_target = readyToGo ? target_final : randPost
```

The form submission handler sets:
- `step_id = cookie_step_count + 1`
- `ad_impressions = Number(Cookies.get('imps'))`
- `visitor_id = cookie_visitor_id`
- `next_target = next_target`
- then submits `#adsForm`

Known conversion helpers in JS:

```js
POST https://gplinks.com/track/data.php
request=addConversion&pid=<pid>&vid=<vid>&o_id=<offer_id>&o_type=<offer_type>
```

and image GET variant:

```text
https://gplinks.com/track/data.php?request=addConversion&pid=<pid>&vid=<decoded_vid>&o_id=<offer_id>&o_type=<offer_type>
```

The constants visible in JS resolve to likely offer ids/types:
- push offer: `o_id=3`, `o_type=2`
- iframe offer: `o_id=4`, `o_type=3`

## Replay attempted

Attempted three POSTs to the PowerGam page with:

```text
form_name=ads-track-data
step_id=1/2/3
ad_impressions=1 or 2
visitor_id=<vid>
next_target=<same PowerGam URL for steps 1-2, target_final for step 3>
```

Also attempted setting the JS cookies before each POST:
- `lid`
- `pid`
- `pages`
- `vid`
- `step_count`
- `imps`

Observed result:
- step 1 POST -> `302` back to PowerGam URL
- step 2 POST -> `302` back to PowerGam URL
- step 3 POST -> `302` to `https://gplinks.co/YVTC?pid=1224622&vid=<vid>`
- final GET -> `302` to `https://gplinks.co/link-error?alias=YVTC&error_code=not_enough_steps`

Conversion endpoint probes to `gplinks.com/track/data.php` with the visible offer ids returned HTTP `500`, so that contract is still incomplete.

## Current blocker

The browserless form replay can reproduce the visible step transitions but does **not** satisfy the server-side step validation. The missing piece is likely one or more of:

- a valid ad impression event from Google/offer iframe
- a conversion/postback written through `track/data.php` with exact required params/headers
- a timing or cookie detail not yet captured
- additional state written by third-party ad scripts before `#adsForm` submit

## Handler recommendation

Do not mark `gplinks.co` as supported yet.

Safe next implementation is a partial mapper that:
- uses `curl_cffi` to pass entry Cloudflare
- decodes `lid`, `pid`, `pages`, and `vid`
- parses `#adsForm`
- computes the `target_final` candidate
- returns `POWERGAM_STEPS_MAPPED` with blocker `server returns not_enough_steps on naive replay`

Next real research lane:
- instrument a real browser for network requests during a human-like ad/impression step
- capture successful `track/data.php` or third-party postback calls
- compare cookies/localStorage before step 3 final GET

## Browser instrumentation pass - 2026-04-24 evening

A CDP-driven Chrome run was added after the initial HTTP replay.

### What changed vs the naive replay

Instead of only posting with `curl_cffi`, Chrome loaded the real `powergam.online` page and executed the page JS:

- PowerGam initialized cookies:
  - `lid=YVTC`
  - `pid=1224622`
  - `pages=3`
  - `vid=<visitor token>`
  - `step_count=0`
  - `imps=0`
- Real page scripts loaded:
  - Google tags / fundingchoices
  - `api.gplinks.com/track/js/power-cdn.js`
  - `tracki.click/ads/js/embed.js`
  - `tracki.click/ads/api/get-banner.php`
  - `tracki.click/ads/api/imp.php?...` for banner impressions
- The browser produced real PowerGam form posts:
  - `step_id=1`, `next_target=https://powergam.online`
  - `step_id=2`, `next_target=https://powergam.online`
  - `step_id=3`, `next_target=https://gplinks.co/YVTC?pid=1224622&vid=<visitor token>`

### Important negative proof

Even when the browser was forced to submit `ad_impressions=5` on all three PowerGam form posts, a follow-up `curl_cffi` request to the computed final candidate still returned:

```text
302 -> https://gplinks.co/link-error?alias=YVTC&error_code=not_enough_steps
```

Adding obvious query params like `steps=3`, `step=3`, `imps=5`, or `pages=3` to the final URL did not change the result.

### Updated interpretation

The missing state is **not only** the visible `step_id` count, the PowerGam cookies, or the visible `ad_impressions` field.

The strongest current hypothesis is that `gplinks.co` expects a server-side conversion/postback record tied to `vid` and `pid`, likely written by one of:

- `gplinks.com/track/data.php` with a stricter contract than the obvious `request=addConversion` attempt
- a Tracki click/ad callback beyond passive `imp.php` impression requests
- a Google ad/fundingchoices viewability path that the current headless run loads but does not convert into the server-side gplinks step record

### Current hard blocker

The frontend PowerGam form can be reproduced and the browser can execute the visible steps, but the server-side enough-steps ledger still does not update. A future pass needs to capture or synthesize the exact conversion/postback that increments that ledger.

## GPT hook trace - 2026-04-24 evening

A follow-up CDP run injected hooks for GPT lifecycle events and native `#adsForm` submission.

Observed:
- The hook installed successfully (`GPT_HOOKED`).
- No `impressionViewable`, `rewardedSlotReady`, `rewardedSlotClosed`, or related GPT lifecycle event was logged before any of the three form submits.
- `window.rewardedAdReadyEvent` stayed false before the final submit.
- The browser still posted the expected visible payloads:
  - step 1: `ad_impressions=0`, `next_target=https://powergam.online`
  - step 2: `ad_impressions=0`, `next_target=https://powergam.online`
  - step 3: `ad_impressions=0`, `next_target=https://gplinks.co/YVTC?pid=1224622&vid=<vid>`
- The final browser navigation to the computed `gplinks.co` candidate hit Cloudflare challenge first in headless Chrome, not the downstream target.
- Separate `curl_cffi` follow-up to the same final candidate still returned `not_enough_steps`.

Updated blocker:
- The missing proof is now narrower: this VPS/headless browser run does not produce a usable GPT rewarded/viewable lifecycle, and without that lifecycle the server ledger still refuses the final candidate.
- No code patch should claim final `gplinks.co` support from current evidence. The current partial mapper is still the honest state.

Next practical options:
1. Run the same hooked trace in a non-headless/real profile browser where GPT rewarded/interstitial ads can actually become ready.
2. Continue JS/protocol analysis of Google/GPT calls, but this is likely lower ROI than a real browser trace because the missing state appears ad-lifecycle dependent.
3. Leave `gplinks.co` as partial and switch to `cuty.io` or `exe.io` if faster family expansion is preferred.
