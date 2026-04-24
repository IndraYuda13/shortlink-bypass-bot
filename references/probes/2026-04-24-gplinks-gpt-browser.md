# Probe notes: gplinks GPT real-browser pass

Date: 2026-04-24
Scope: `https://gplinks.co/YVTC` final `not_enough_steps` blocker
Method: Chrome/CDP real-browser traces on this VPS. No project code changed.

## Goal

Test whether a non-headless Chrome run, with less obviously automated flags, can produce the missing Google Publisher Tag lifecycle (`impressionViewable`, `rewardedSlotReady`, `rewardedSlotClosed`, etc.) and therefore clear the PowerGam/GPlinks final `not_enough_steps` gate.

## Browser setup used

Available tooling on this VPS:

- `/usr/bin/google-chrome`
- `/usr/bin/Xvfb` / `/usr/bin/xvfb-run`
- Node v24 with built-in WebSocket for direct CDP control

Trace mode:

- Chrome was launched **non-headless under Xvfb**.
- CDP injected hooks with `Page.addScriptToEvaluateOnNewDocument` before page scripts ran.
- Flags included:
  - `--disable-popup-blocking`
  - `--autoplay-policy=no-user-gesture-required`
  - `--window-size=1365,900`
  - `--disable-blink-features=AutomationControlled`
  - `--disable-extensions` in the second run
- Hooks captured:
  - `googletag.pubads()` availability
  - GPT events: `impressionViewable`, `slotRenderEnded`, `slotOnload`, `rewardedSlotReady`, `rewardedSlotClosed`, `rewardedSlotGranted`, `rewardedSlotVideoCompleted`, interstitial events
  - native `HTMLFormElement.prototype.submit`
  - PowerGam form payload, cookies, local/session storage, `window.readyToGo`, `window.rewardedAdReadyEvent`
  - network for `gplinks`, `powergam`, Google ad domains, Funding Choices, and `tracki.click`

Temporary trace artifacts:

- `/tmp/gplinks_gpt_trace_stdout.log`
- `/tmp/gplinks_gpt_trace_stdout2.log`
- `/tmp/gplinks_gpt_trace.mjs`

## Run 1: non-headless Xvfb Chrome, permissive click automation

Important evidence from the completed trace:

- PowerGam loaded successfully from the original shortlink redirect.
- GPT loaded and `googletag.pubads()` became available:
  - `GPT_PUBADS_FOUND` logged at `https://powergam.online/`.
- Google/Funding Choices traffic loaded, including:
  - `securepubads.g.doubleclick.net/tag/js/gpt.js`
  - `securepubads.g.doubleclick.net/pagead/managed/js/gpt/.../pubads_impl.js`
  - `fundingchoicesmessages.google.com/...`
  - `pagead2.googlesyndication.com/...`
- Tracki banner path loaded and fired impression pixels with real `vid`/`pid`:
  - `tracki.click/ads/api/get-banner.php?...&vid=1017779586&pid=1224622`
  - multiple `tracki.click/ads/api/imp.php?...&vid=1017779586&pid=1224622`
- A real native `adsForm` submit was captured:

```text
form_name=ads-track-data
step_id=1
ad_impressions=0
visitor_id=MTAxNzc3OTU4Ng
next_target=https://powergam.online
```

State at submit:

```text
imps=0
step_count=1
readyToGo=false
rewardedAdReadyEvent=false
```

Negative evidence:

- No `GPT_EVENT_*` hooks fired.
- No `impressionViewable` event fired.
- No `rewardedSlotReady`, `rewardedSlotClosed`, or rewarded lifecycle event fired.
- The flow remained at PowerGam step 2; final state was:

```text
href=https://powergam.online/
body includes: Step 2 of 3
imps=0
readyToGo=false
rewarded=false
```

## Run 2: non-headless Xvfb Chrome, stricter wait-for-CONTINUE automation

This run used `--disable-extensions` and waited for an actual `CONTINUE` state instead of clicking early.

Evidence:

- GPT again became available:
  - `GPT_PUBADS_FOUND` logged at `https://powergam.online/`.
- No GPT lifecycle event hooks fired:
  - no `impressionViewable`
  - no rewarded/interstitial lifecycle events
- The page did not reach a clickable `CONTINUE` state within the wait window.
- Final observed body before termination:

```text
VERIFY
Verify & Scroll down to Continue
```

State remained:

```text
step_count=0
imps=0
readyToGo=false
rewarded=false
```

## Conclusion

Still blocked.

The strongest available VPS-local browser trace did **not** produce a usable GPT impression/rewarded lifecycle, even in non-headless Chrome under Xvfb with autoplay and popup-friendly flags. GPT loads and `pubads()` exists, but no `impressionViewable` or rewarded events fire, so the first-party `imps` cookie stays `0` and `window.rewardedAdReadyEvent` stays false.

This pass does not prove the final target. It strengthens the existing conclusion that `gplinks.co` should remain a partial mapper only. Current evidence still does not justify marking final `gplinks.co/YVTC -> tesskibidixxx.com` support as solved.

## Updated blocker

The blocker is now narrower than generic browser execution:

- Chrome can load PowerGam and GPT on this VPS.
- Tracki banner impressions can fire.
- PowerGam form submission can be captured.
- But this VPS/browser environment does not obtain the GPT viewability/rewarded ad lifecycle that appears necessary to advance the server-side enough-steps ledger.

## Next best action

If this family must be finished, the next useful trace is not another headless/VPS variant. It should be a real residential/desktop browser profile where Google ad slots can actually become viewable/rewarded, then compare:

1. GPT lifecycle events before each submit.
2. `imps` cookie before submit.
3. Any extra Google/GPlinks postback request IDs.
4. Final `gplinks.co/YVTC?pid=1224622&vid=...` response.

Until that exists, keep `gplinks.co` as `POWERGAM_STEPS_MAPPED` / partial support.
