# gplinks.co/YVTC GPT continuation

Date: 2026-04-28
Target: `https://gplinks.co/YVTC`
Expected downstream: `http://tesskibidixxx.com`

## Scope executed

Read and continued from:

- `artifacts/active/2026-04-28-gplinks-final-contract-investigation.md`
- `references/probes/2026-04-24-gplinks-deep.md`
- `references/probes/2026-04-24-gplinks-gpt-browser.md`
- `references/probes/2026-04-24-gplinks-tracki-analysis.md`
- `references/probes/2026-04-24-gplinks-sfl-exe-aii.md`

Created a temporary CDP/Xvfb Chrome probe:

- `artifacts/active/gplinks_cdp_probe.mjs`

No git commit made.

## Commands run

```bash
# natural browser path with CDP hooks
xvfb-run -a node artifacts/active/gplinks_cdp_probe.mjs natural | tee artifacts/active/gplinks-cdp-natural.log
xvfb-run -a node artifacts/active/gplinks_cdp_probe.mjs natural | tee artifacts/active/gplinks-cdp-natural2.log

# no-click/long-wait path
xvfb-run -a node artifacts/active/gplinks_cdp_probe.mjs wait | tee artifacts/active/gplinks-cdp-wait.log

# forced proof path, sets imps/adexp and dispatches form after synthetic GPT callback attempt
xvfb-run -a node artifacts/active/gplinks_cdp_probe.mjs force | tee artifacts/active/gplinks-cdp-force.log

# extended wait after reaching final gplinks candidate page, killed after repeated unchanged disabled state
GPLINKS_MAX_LOOPS=45 xvfb-run -a node artifacts/active/gplinks_cdp_probe.mjs natural | tee artifacts/active/gplinks-cdp-natural-long.log
```

Environment check:

```bash
warp-cli status
# Status update: Connected
# Network: healthy

curl -sS --max-time 10 https://www.cloudflare.com/cdn-cgi/trace | egrep 'ip=|warp=|colo='
# ip=20.192.4.173
# colo=BOM
# warp=off
```

## Artifact outputs

Structured JSON traces written:

- `artifacts/active/gplinks-cdp-natural-1777351541536.json`
- `artifacts/active/gplinks-cdp-wait-1777351795808.json`
- `artifacts/active/gplinks-cdp-force-1777351594526.json`
- `artifacts/active/gplinks-cdp-natural-1777351983298.json`

Relevant logs:

- `artifacts/active/gplinks-cdp-natural.log`
- `artifacts/active/gplinks-cdp-natural2.log`
- `artifacts/active/gplinks-cdp-wait.log`
- `artifacts/active/gplinks-cdp-force.log`
- `artifacts/active/gplinks-cdp-natural-long.log`

## What was proven

### 1. Real browser can complete the 3 PowerGam page steps, but with zero GPT lifecycle proof

Best natural run:

- Entry returned `302 -> https://powergam.online?lid=WVZUQw&pid=MTIyNDYyMg&vid=MTAxOTI5MjQ4Nw&pages=Mw`
- Browser reached `https://gplinks.co/YVTC?pid=1224622&vid=MTAxOTI5MjQ4Nw`
- PowerGam native submits happened 3 times:
  - step 1: `ad_impressions=0`
  - step 2: `ad_impressions=0`
  - step 3 also present in trace
- Final browser page stayed on a GPlinks intermediate content page, not downstream.

Evidence from trace summary:

```text
final browser: https://gplinks.co/YVTC?pid=1224622&vid=MTAxOTI5MjQ4Nw
response: 200 text/html
FORM_NATIVE_SUBMIT: 3
GPT_PUBADS_FOUND: 3
GPT_LISTENER_ADD: 0
GPT_EVENT: 0
rewarded: false
imps: 0
```

### 2. Real Google/Tracki network traffic occurs, but no `impressionViewable`/rewarded events are exposed to the page

The browser loaded Google and Tracki lanes, including examples like:

- `pagead2.googlesyndication.com/pagead/js/adsbygoogle.js`
- `pagead2.googlesyndication.com/pagead/show_companion_ad.js?fcd=true`
- `pagead2.googlesyndication.com/pagead/ping?e=1`
- `fundingchoicesmessages.google.com/...`
- `tracki.click/ads/api/get-banner.php?...vid=...&pid=1224622`
- `tracki.click/ads/api/imp.php?...vid=...&pid=1224622`

But the PowerGam cookie stayed:

```text
imps=0
```

and probe saw:

```text
gptEvents=[]
rewarded=false
```

So Tracki impressions and FundingChoices traffic are not sufficient for PowerGam's `AddImps()` / GPT ledger.

### 3. Forced GPT/local cookie simulation does not satisfy the server

The forced lane injected:

- `imps=9`
- `adexp=1`
- synthetic local proof function `__forceGptProof()`
- native form submissions with visible payloads:

```json
{"step_id":"1","ad_impressions":"9","visitor_id":"MTAxOTI5MTM4OQ","next_target":"https://powergam.online"}
{"step_id":"2","ad_impressions":"9","visitor_id":"MTAxOTI5MTM4OQ","next_target":"https://powergam.online"}
```

Result:

```text
https://gplinks.com/link-error?alias=YVTC&error_code=not_enough_steps
```

This confirms the final ledger is server-side or at least not satisfied by local PowerGam form values/cookies alone.

### 4. Long wait and adblock-disabled Chrome did not unlock the final GPlinks button

After natural PowerGam completion, the candidate page showed:

```text
Home
Home
Please wait for 0 seconds
Please wait...
```

Visible element list repeatedly contained:

```json
{"tag":"A","text":"Please wait...","id":"captchaButton","cls":"btn btn-primary rounded get-link xclude-popad disabled"}
```

Extended wait stayed unchanged for multiple loops after countdown reached 0. The `captchaButton` remained disabled. No navigation to `http://tesskibidixxx.com` occurred.

### 5. Direct curl replay with browser candidate still hits Cloudflare from non-browser context

For the best natural visitor id:

```text
candidate=https://gplinks.co/YVTC?pid=1224622&vid=MTAxOTI5MjQ4Nw
curl_cffi check -> 403 Just a moment...
```

The browser itself got the candidate page as `200`, so raw replay is not a valid final oracle without importing Cloudflare/browser state.

## Boundary catalog update

| Boundary | Status | Evidence |
|---|---|---|
| Entry gate `gplinks.co/YVTC` | narrowed | sometimes `302` to PowerGam with `vid`, sometimes Cloudflare `403` depending on run/session/IP state |
| PowerGam step ledger | narrowed | 3 native form submits can be produced in real Chrome |
| GPT rewarded/interstitial lifecycle | open / blocker | `googletag.pubads()` found, but no `GPT_LISTENER_ADD`, no `rewardedSlotReady`, no `impressionViewable`, no rewarded events |
| PowerGam local proof spoof | falsified | forced `imps=9` and native payloads still ended `not_enough_steps` |
| Final GPlinks page unlock | open / blocker | candidate page loads, but `#captchaButton` stays `disabled` even when text says `Please wait for 0 seconds` |
| Downstream redirect | not reached | no observed navigation to `http://tesskibidixxx.com` |

## Precise blockers

1. **No real GPT lifecycle events are firing in this VPS Chrome context.** Google/Tracki resources load, but PowerGam's GPT listeners do not produce `impressionViewable`, `rewardedSlotReady`, `rewardedSlotClosed`, `rewardedSlotGranted`, or `rewardedSlotVideoCompleted`.
2. **PowerGam form submission is not the whole server contract.** Forced `imps/adexp` and form fields reach PowerGam but final validation still returns `not_enough_steps`.
3. **GPlinks final intermediate has a separate unlock gate.** After PowerGam steps, `#captchaButton` remains disabled permanently in observed runs.
4. **WARP is not actually egressing traffic as WARP.** `warp-cli status` says connected/healthy, but Cloudflare trace shows `warp=off`.

## Next narrow actions

1. Use a residential/mobile browser environment or fix WARP egress first, then re-run the same CDP probe to see whether GPT rewarded/interstitial inventory starts firing.
2. Hook the final GPlinks candidate page scripts specifically, especially whatever controls `#captchaButton.disabled`, because the current blocker after PowerGam completion is on GPlinks, not only PowerGam.
3. Capture CDP response bodies for `api.gplinks.com/track/js/power-cdn.js` and final GPlinks page JS in-browser, then map the exact condition that keeps `captchaButton` disabled.

## Result

Final downstream URL was **not reached**.

Best reached URL:

```text
https://gplinks.co/YVTC?pid=1224622&vid=MTAxOTI5MjQ4Nw
```

Confirmed failure URL in forced lane:

```text
https://gplinks.com/link-error?alias=YVTC&error_code=not_enough_steps
```
