# Probe notes: gplinks PowerGam / tracki final blocker

Date: 2026-04-24
Scope: `https://gplinks.co/YVTC` PowerGam final `not_enough_steps` blocker
Method: static JS deobfuscation + safe HTTP probes. No code changes.

## Known state before this pass

- Entry still redirects with Chrome TLS impersonation:
  - `https://gplinks.co/YVTC`
  - -> `https://powergam.online?lid=WVZUQw&pid=MTIyNDYyMg&vid=<vid>&pages=Mw`
- Decoded values for the sampled run:
  - `lid=YVTC`
  - `pid=1224622`
  - `pages=3`
  - `vid=<base64-ish visitor id>`
- `powergam.online` returns the same `#adsForm` hidden payload:
  - `form_name=ads-track-data`
  - `step_id`
  - `ad_impressions`
  - `visitor_id`
  - `next_target`

## `power-cdn.js` findings

Fetched script:

```text
https://api.gplinks.com/track/js/power-cdn.js?v=2.0.0.5
```

Static deobfuscation confirms the visible form replay contract, but also narrows the missing state:

```js
mainDomain = 'gplinks.com'
redirectDomain = 'gplinks.co'
randPost = GetRandom(postsArray) // page inline: ['https://powergam.online']

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

Submit handler:

```js
$('#adsForm').on('submit', async function (e) {
  e.preventDefault()
  step_id = cookie_step_count + 1
  ad_impressions = Number(Cookies.get('imps'))
  visitor_id = cookie_visitor_id
  Cookies.set('step_count', step_id)
  Cookies.set('imps', 0)
  this.step_id.value = step_id
  this.ad_impressions.value = ad_impressions
  this.visitor_id.value = visitor_id
  this.next_target.value = next_target
  this.submit()
})
```

The only first-party counter mutation found is Google Publisher Tag viewability:

```js
googletag.cmd.push(() => {
  googletag.pubads().addEventListener('impressionViewable', AddImps)
})
function AddImps() {
  imps = Number(Cookies.get('imps'))
  Cookies.set('imps', imps + 1)
}
```

Inline page GPT setup also defines interstitial/rewarded ad slots:

```js
/23305795243/POWERGAM_INT
/23305795243/POWERGAM_REWARDED

function playRewardedIfNeeded(nextCallback) {
  if (window.readyToGo && rewardedAdReadyEvent) {
    window._adsFormSubmitAfterReward = nextCallback
    rewardedAdReadyEvent.makeRewardedVisible()
  } else nextCallback()
}
```

This means the final step may be gated by a real GPT rewarded/interstitial lifecycle in a browser. If no rewarded slot is ready, JS still submits, but the server may still consider the visitor under-qualified.

## Conversion/postback helpers

`power-cdn.js` contains two helpers, but no call site was found in the normal submit/timer path:

```js
addConversion(pid, vid, o_id, o_type) {
  $.post('https://gplinks.com/track/data.php', {
    request: 'addConversion', pid, vid, o_id, o_type
  })
}

sendPostback(pid, encodedVid, o_id, o_type) {
  new Image().src = 'https://gplinks.com/track/data.php?request=addConversion'
    + '&pid=' + pid
    + '&vid=' + base64UrlDecode(encodedVid)
    + '&o_id=' + o_id
    + '&o_type=' + o_type
}
```

Visible constants still resolve to:

```text
push_offer_id=3, push_offer_type=2
iframe_offer_id=4, iframe_offer_type=3
```

HTTP probes to `data.php` with both encoded and decoded visitor IDs still returned HTTP 500 for both GET and POST, even with `Origin`, `Referer`, and `X-Requested-With`. Current conclusion: `data.php` is not the missing browser-visible form step by itself, or it requires server-side preconditions not present in the static replay.

## `tracki.click` findings

### `embed.js`

Fetched script:

```text
https://tracki.click/ads/js/embed.js
```

PowerGam embeds five copies like:

```html
<script src="https://tracki.click/ads/js/embed.js" data-size="336x280" data-vid="" data-pid=""></script>
```

The script batches same-size ad slots and calls:

```text
GET https://tracki.click/ads/api/get-banner.php?size=336x280&origin=<location.href>&count=<n>&vid=&pid=&exclude=<ids>
```

Returned banners include `click_url` and `imp_url`, for example:

```text
https://tracki.click/ads/api/imp.php?cid=<banner_id>&r=<base64-origin>&t=<timestamp>
https://tracki.click/ads/api/click.php?cid=<banner_id>&r=<base64-origin>
```

Rendering fires the impression pixel:

```js
new Image().src = b.imp_url + '&t=' + Date.now()
```

Safe HTTP probe result:

```text
get-banner.php -> 200 JSON { ok: true, banners: [...] }
imp.php        -> 200 image/gif, no Set-Cookie
```

No localStorage/cookie writes were found in `embed.js`. Its script attributes have empty `data-vid`/`data-pid`, and the impression pixel writes only to `tracki.click`, not to PowerGam/gplinks state. This is probably not the server-side `not_enough_steps` key.

### `pop.js`

`power-cdn.js` anti-adblock checks this URL with a `HEAD` request:

```text
https://tracki.click/ads/js/pop.js
```

`pop.js` itself uses:

```text
GET https://tracki.click/ads/api/pop.php?action=config
GET https://tracki.click/ads/api/pop.php?action=serve&vid=<VID>&pid=<PID>&prefetch=1
GET/Beacon https://tracki.click/ads/api/pop.php?action=track&cid=<cid>&vid=<VID>&pid=<PID>
```

It stores only:

```js
sessionStorage.setItem('_pop_last', lastPopTime)
```

But the current PowerGam HTML does **not** load `pop.js`; it is only used as an anti-adblock reachability check inside `power-cdn.js`. Therefore `pop.php?action=track` is not part of the current visible step flow unless another third-party ad injects it later.

## Falsified / narrowed hypotheses

1. **Tracki banner impressions alone are not enough.**
   - `tracki.click` impression pixels return GIFs with no cookies and no PowerGam/gplinks mutation.
   - The embed script has empty `data-vid`/`data-pid` on this page.

2. **`adexp=1` cookie is not enough.**
   - `power-cdn.js` can set `adexp=1` when a `.banner-ad` or Google iframe focus path fires.
   - Replaying three posts with `adexp=1` and `ad_impressions=3` still ended at:
     - `https://gplinks.co/link-error?alias=YVTC&error_code=not_enough_steps`

3. **Following intermediate PowerGam redirects is not enough.**
   - A replay that followed each `302 https://powergam.online` back to a fresh `200` page before the next POST still ended in `not_enough_steps`.

4. **Visible `data.php` conversion helper is incomplete as a standalone HTTP call.**
   - `request=addConversion&pid=1224622&vid=<encoded-or-decoded>&o_id=3/4&o_type=2/3` returned HTTP 500 for GET/POST in this context.

## Working hypothesis

`not_enough_steps` is most likely caused by missing **real Google Publisher Tag ad lifecycle evidence**, not by `tracki.click` banners.

Evidence:

- `ad_impressions` is populated only from the `imps` cookie.
- `imps` is incremented only by GPT `impressionViewable` events in `power-cdn.js`.
- The page defines out-of-page GPT interstitial and rewarded units (`POWERGAM_INT`, `POWERGAM_REWARDED`).
- The final `NextBtn` click calls `playRewardedIfNeeded()`, which may require a real `rewardedSlotReady -> makeRewardedVisible -> rewardedSlotClosed` cycle before the final submit in successful browsers.
- Tracki embed/pop scripts do not write first-party cookies/localStorage relevant to the gplinks final validator.

## Next exact probe

Run a real browser trace for only this URL and capture before/after each step:

1. Network requests matching:
   - `gplinks.com/track/data.php`
   - `securepubads.g.doubleclick.net/*`
   - `googleads.g.doubleclick.net/*`
   - `pagead2.googlesyndication.com/*`
   - `tracki.click/ads/api/*`
2. Console-hook these browser events before page scripts run:
   - `googletag.pubads().addEventListener('impressionViewable', ...)`
   - `rewardedSlotReady`
   - `rewardedSlotClosed`
3. Dump state immediately before every `#adsForm` native submit:
   - form payload
   - `document.cookie`
   - `localStorage`
   - `sessionStorage`
   - `window.readyToGo`
   - whether `rewardedAdReadyEvent` is non-null

Success oracle: compare a browser run that reaches the final target with the static replay. If the successful run has GPT `impressionViewable`/rewarded events or additional Google request IDs before final submit, those are the missing server-side step proof.
