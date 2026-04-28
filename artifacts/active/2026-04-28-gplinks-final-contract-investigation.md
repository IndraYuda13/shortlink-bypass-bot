# gplinks.co final-contract investigation

Sample: `https://gplinks.co/YVTC`
Date: 2026-04-28

## Status

Still blocked at final server validation. Current sample continues to return:

```text
302 -> https://gplinks.co/link-error?alias=YVTC&error_code=not_enough_steps
```

A live HTTP replay with fresh visitor ids confirmed that adding visible PowerGam step fields, first-party JS cookies, `adexp=1`, high `ad_impressions`, and Tracki pop `serve/track` calls does not satisfy the final `gplinks.co` ledger.

## Current raw response clues

Entry still works with curl_cffi Chrome impersonation:

```text
GET https://gplinks.co/YVTC
302 Location: https://powergam.online?lid=WVZUQw&pid=MTIyNDYyMg&vid=<vid>&pages=Mw
Set-Cookie: AppSession=<...>; domain/path implicit gplinks.co
Set-Cookie: csrfToken=<...>; domain/path implicit gplinks.co
```

Decoded values:

```text
lid=YVTC
pid=1224622
pages=3
vid=<base64-ish visitor id, e.g. MTAxOTI4MTkzNw>
computed candidate=https://gplinks.co/YVTC?pid=1224622&vid=<vid>
```

PowerGam page:

```text
GET powergam URL -> 200 https://powergam.online/?lid=...&pid=...&vid=...&pages=Mw
<title>Please Wait... | PowerGam</title>
form#adsForm hidden inputs:
  form_name=ads-track-data
  step_id=
  ad_impressions=
  visitor_id=
  next_target=
```

Important current HTML/JS snippets:

```js
interstitialSlot = googletag.defineOutOfPageSlot('/23305795243/POWERGAM_INT', googletag.enums.OutOfPageFormat.INTERSTITIAL)
rewardedSlot = googletag.defineOutOfPageSlot('/23305795243/POWERGAM_REWARDED', googletag.enums.OutOfPageFormat.REWARDED)
googletag.pubads().addEventListener('rewardedSlotReady', function(e){ if(rewardedSlot && e.slot === rewardedSlot) rewardedAdReadyEvent = e })
googletag.pubads().addEventListener('rewardedSlotClosed', function(e){ if(rewardedSlot && e.slot === rewardedSlot && window._adsFormSubmitAfterReward){ cb(); }})
function playRewardedIfNeeded(nextCallback){
  if (window.readyToGo && rewardedAdReadyEvent) rewardedAdReadyEvent.makeRewardedVisible()
  else nextCallback()
}
```

Power CDN deobfuscated enough:

```js
googletag.pubads().addEventListener('impression' + 'Viewable', AddImps)
function AddImps() {
  imps = Number(Cookies.get('imps'))
  Cookies.set('imps', imps + 1)
}

$('#adsForm').on('submit', async function(e) {
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

Current page contains Tracki pop script only in an HTML comment:

```html
<!-- self pop
<script src="https://tracki.click/ads/js/pop.js" data-vid="" data-pid=""></script> -->
```

Power CDN still HEAD-checks Tracki pop/embed as anti-adblock resources, but the page does not execute Tracki pop with real `data-vid` / `data-pid`.

## Falsified live replay lanes

### Naive/visible PowerGam replay

For each fresh visitor id:

```text
POST step 1 -> 302 https://powergam.online
POST step 2 -> 302 https://powergam.online
POST step 3 -> 302 https://gplinks.co/YVTC?pid=1224622&vid=<vid>
GET final -> 302 https://gplinks.co/link-error?alias=YVTC&error_code=not_enough_steps
```

This remains true with:

- JS cookies on `powergam.online`: `lid`, `pid`, `pages`, `vid`, `step_count`, `imps`, `adexp`
- `ad_impressions=1` and `ad_impressions=9`
- reloading PowerGam between steps
- following the step 3 redirect in the same session

### Tracki pop endpoint

The endpoint is live and accepts synthetic track calls:

```text
GET https://tracki.click/ads/api/pop.php?action=config
-> 200 {"ok":true,"has_campaigns":true,"frequency_seconds":5,"pops_per_minute":5,"exclude_classes":"exclude-pop"}

GET https://tracki.click/ads/api/pop.php?action=serve&vid=<vid>&pid=1224622&prefetch=1
-> 200 {"ok":true,"url":"https://...&vid=<vid>&pid=1224622","campaign_id":"1"|"21",...}

GET https://tracki.click/ads/api/pop.php?action=track&cid=<campaign_id>&vid=<vid>&pid=1224622
-> 200 {"ok":true}
```

But running `config -> serve -> track` before all steps, before each step, after each step, or after step 3 still ended with `not_enough_steps`.

## Boundary catalog

- Entry/session gate: `gplinks.co/YVTC` sets `AppSession` and `csrfToken`, then 302s to PowerGam. Status: narrowed, not the blocker.
- PowerGam visible step boundary: `form#adsForm` posts `step_id/ad_impressions/visitor_id/next_target`. Status: falsified as sufficient. Server accepts redirects but final ledger still rejects.
- Ad/GPT lifecycle boundary: GPT `impressionViewable` increments `imps`; final step optionally waits for `rewardedSlotReady -> makeRewardedVisible -> rewardedSlotClosed`. Status: primary open. Prior VPS traces did not produce these lifecycle events.
- Tracki pop/banner boundary: `tracki.click` config/serve/track and banner impressions. Status: falsified as sufficient for final ledger.
- Final go boundary: `gplinks.co/YVTC?pid=1224622&vid=<vid>` requires server-side enough-step proof not produced by HTTP replay. Status: primary open.

## Conclusion

The blocker is not missing visible form fields, not missing PowerGam cookies, and not Tracki pop/banner tracking. The remaining required proof is almost certainly a real Google Publisher Tag lifecycle, especially `impressionViewable` and/or the rewarded out-of-page ad cycle on the final step. In this VPS/browserless lane those events are not generated, so the server-side enough-steps ledger never marks the visitor as qualified.

## Smallest honest patch proposal

Do **not** convert `_handle_gplinks` to `status=1` from HTTP replay.

Smallest safe code patch is to add a gplinks browser-helper lane that is success-oracle gated:

1. Keep current `_handle_gplinks` mapper as fallback.
2. Optional env flag: `SHORTLINK_BYPASS_GPLINKS_BROWSER=1`.
3. Helper opens the original URL in real Chrome/CDP, injects hooks before page scripts, and clicks through only when the page naturally exposes `VERIFY`/`CONTINUE`.
4. Hook/capture:
   - GPT events: `impressionViewable`, `rewardedSlotReady`, `rewardedSlotClosed`, `rewardedSlotGranted`, `rewardedSlotVideoCompleted`
   - each native `adsForm.submit` payload
   - cookies/localStorage/sessionStorage before submit
   - all `gplinks`, `powergam`, Google ad, and Tracki requests
5. Only return `status=1` if browser navigation reaches a URL that is not `link-error` and not `powergam.online`/`gplinks.co` intermediate, or if the final HTTP response is a verified 30x/200 to the known downstream target.
6. If no GPT rewarded/viewable lifecycle is observed, return current partial `POWERGAM_STEPS_MAPPED` with facts showing `gpt_events=[]` and `final_error=not_enough_steps`.

This patch satisfies the final-go contract only when the server-side ad/GPT lifecycle actually occurs. It avoids a false positive from computed `target_final_candidate`.
