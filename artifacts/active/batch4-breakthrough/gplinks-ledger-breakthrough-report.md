# GPLinks PowerGam ledger breakthrough report

Target: `https://gplinks.co/YVTC`  
Expected final oracle: `http://tesskibidixxx.com/`  
Date: 2026-04-29  
Scope: GPLinks PowerGam ledger only. Production code was not edited.

## Files read

- `gplinks_live_browser.py`
- `gplinks_http_fast.py`
- `ROADMAP.md`
- `artifacts/active/2026-04-28-total-optimization-workframe.md`
- `artifacts/active/total-optimization/gplinks-batch3-profile.md`
- GPLinks active notes:
  - `artifacts/active/2026-04-28-gplinks-http-ledger-subagent.md`
  - `artifacts/active/2026-04-28-gplinks-final-contract-investigation.md`
  - `artifacts/active/2026-04-28-gplinks-final-js-analysis.md`
  - `artifacts/active/2026-04-28-gplinks-gpt-continuation.md`
  - `artifacts/active/2026-04-28-gplinks-final-push-workframe.md`
  - `references/probes/2026-04-24-gplinks-gpt-browser.md`
  - `references/probes/2026-04-24-gplinks-tracki-analysis.md`

## Artifacts created

- `artifacts/active/batch4-breakthrough/gplinks_delay_probe.py`
- `artifacts/active/batch4-breakthrough/gplinks-delay16-imps0.json`
- `artifacts/active/batch4-breakthrough/gplinks-follow-step3-exactcookie.json`
- `artifacts/active/batch4-breakthrough/gplinks-live-current-run.json`
- `artifacts/active/batch4-breakthrough/powergam-current.html`
- `references/lessons/cases/2026-04-29-gplinks-powergam-ledger.md`

## Executive result

No pure-HTTP ledger breakthrough was reached.

The current fastest proven lane remains the guarded live-browser helper:

- result artifact: `artifacts/active/batch4-breakthrough/gplinks-live-current-run.json`
- `status=1`
- `stage=live-browser-final-gate`
- `waited_seconds=150.1`
- `token_used=true`
- DOM sitekey used: `0x4AAAAAAAynCEcs0RV-UleY`
- final oracle reached: `http://tesskibidixxx.com/`

The strongest new negative result is that realistic HTTP timing does not satisfy the PowerGam/GPLinks server ledger:

- artifact: `artifacts/active/batch4-breakthrough/gplinks-delay16-imps0.json`
- raw encoded `vid` used as browser-like `visitor_id`
- `16.2s` waited before each of the three PowerGam posts
- `ad_impressions=0`, matching prior natural browser traces where `imps` stayed zero
- final candidate still returned:
  - `302 https://gplinks.co/link-error?alias=YVTC&error_code=not_enough_steps`

So the missing proof is not just:

- visible `adsForm` payload
- raw-vs-decoded `vid`
- elapsed wall time between submits
- synthetic `imps` / `adexp`
- Tracki pop/banner calls
- standalone `gplinks.com/track/data.php addConversion`

## Evidence ladder

### 1. PowerGam JS / GPT lifecycle

Previously established and re-used facts:

- `power-cdn.js` stores `visitor_id` from raw query `vid`, not decoded numeric `vid`.
- Browser-like PowerGam form payload should use:
  - `visitor_id=<raw encoded vid>`
- GPT-related local counter:
  - `imps` increments through `googletag.pubads().addEventListener('impressionViewable', AddImps)`.
- Prior CDP browser traces loaded Google/Tracki resources but did not emit useful GPT lifecycle events:
  - no `impressionViewable`
  - no `rewardedSlotReady`
  - no `rewardedSlotClosed`
  - `imps=0`

New interpretation after the latest successful browser run:

- GPT lifecycle is still suspicious, but not the only explanation.
- A browser helper can reach the final GPLinks page and downstream href even though earlier natural traces had `imps=0`.
- Therefore, the server ledger difference is more likely a broader browser-bound PowerGam side effect, request/header/resource sequence, or native navigation context, not merely a visible `imps > 0` value.

### 2. HTTP raw-vid replay

Prior subagent already proved that using raw encoded `vid` is more exact than decoded `vid`, but immediate raw-vid replay still failed.

This pass added a bounded timing probe:

```text
entry 302 -> https://powergam.online?lid=WVZUQw&pid=MTIyNDYyMg&vid=MTAxOTU3NDg2Mw&pages=Mw
post step 1 at t=17.921s -> 302 https://powergam.online
post step 2 at t=35.288s -> 302 https://powergam.online
post step 3 at t=52.520s -> 302 https://gplinks.co/YVTC?pid=1224622&vid=MTAxOTU3NDg2Mw
candidate direct at t=52.819s -> 302 https://gplinks.co/link-error?alias=YVTC&error_code=not_enough_steps
```

Conclusion: a simple “server requires 15 seconds per step” model is falsified.

### 3. Final GPLinks page / Turnstile gate

The live browser run created `artifacts/active/gplinks-final-probe/latest_before_unlock.json` and HTML.

Before unlock:

- page: `https://gplinks.co/YVTC?pid=1224622&vid=MTAxOTU3NTQ1MQ`
- `app_vars.captcha_links_go=yes`
- `app_vars.captcha_links_go_plan=yes`
- `app_vars.cloudflare_turnstile_on=yes`
- `app_vars.counter_value=3`
- `form#go-link action=/links/go method=post`
- hidden fields include `_csrfToken`, `cf-turnstile-response`, and encrypted form/token data
- `#captchaButton`:
  - text: `Please wait...`
  - class includes `disabled`
  - `href=javascript: void(0)`

After helper injects the Turnstile token into the page's own submission path:

- `#captchaButton` becomes `Get Link`
- `#captchaButton.href=http://tesskibidixxx.com/`
- helper returns success without final navigation by default

This boundary is closed for the browser lane. It is not closed for pure HTTP because HTTP replay cannot get the final page HTML until the PowerGam ledger is accepted.

## Hypotheses tested

### H1. The HTTP failure is caused by decoded `vid`

Status: falsified as sufficient.

Evidence:

- Prior report showed browser JS uses raw encoded `vid`.
- Raw-vid replay still returned `not_enough_steps`.
- This pass used raw encoded `vid` again with realistic delays and still failed.

### H2. The HTTP failure is caused by submitting too fast

Status: falsified.

Evidence:

- `gplinks-delay16-imps0.json` waited `16.2s` before each step.
- The third PowerGam post still redirected to the correct candidate.
- The candidate still returned `not_enough_steps`.

### H3. The final GPLinks page is blocked by captcha/timer after PowerGam succeeds

Status: supported and browser-solved.

Evidence:

- `latest_before_unlock.json` shows final page requires captcha plan and Turnstile.
- `gplinks_live_browser.py` uses `solve_turnstile()` then invokes the page's own submit path.
- Live run reached `#captchaButton.href=http://tesskibidixxx.com/`.

### H4. Tracki banner/pop impressions are the missing ledger

Status: falsified from previous notes, unchanged.

Evidence:

- Tracki `get-banner/imp` and pop `config/serve/track` were tested before and did not satisfy `not_enough_steps`.
- Current final GPLinks page does include Tracki click URLs with `vid`/`pid`, but these appear after the ledger has already accepted the candidate, not before.

### H5. A faster proven lane exists now

Status: no new faster lane proven.

Evidence:

- Current live-browser lane: `150.1s` final oracle.
- Batch 3 profile: about `151.3s`, with PowerGam ledger `~95-96s` and Turnstile solve `~50s`.
- HTTP delayed probe: `52.82s` to failure, no final oracle.

## Boundary catalog

| Boundary | Status | Evidence |
|---|---|---|
| Entry/session gate | narrowed | `gplinks.co/YVTC` sets `AppSession`/`csrfToken` and redirects to PowerGam with encoded `lid/pid/vid/pages`. |
| PowerGam visible form | narrowed, not sufficient | Three `adsForm` posts can produce the final candidate but HTTP still gets `not_enough_steps`. |
| PowerGam timer | falsified as sole blocker | `16.2s` per-step HTTP timing still fails. |
| PowerGam GPT/ad/resource side effect | primary open | Browser succeeds, HTTP fails. Prior GPT event hooks did not show clean lifecycle, so exact side effect remains unidentified. |
| GPLinks final Turnstile + `/links/go` | browser-closed | Browser helper solves Turnstile and page exposes downstream href. |
| Pure HTTP final candidate | blocked | Server rejects before final page HTML with `error_code=not_enough_steps`. |

## Exact next patch, if any

Do not patch production yet for full HTTP. No HTTP success oracle was reached.

The smallest useful next patch should be diagnostic and env-guarded, not behavior-changing:

1. Add optional GPLinks CDP capture mode around the existing live browser helper, gated by env such as `SHORTLINK_BYPASS_GPLINKS_TRACE_LEDGER=1`.
2. Capture for each native PowerGam submit:
   - request headers
   - response headers
   - redirect chain
   - posted form body
   - cookies for `powergam.online` and `gplinks.co`
   - `localStorage` and `sessionStorage`
   - visible JS globals: `readyToGo`, `rewardedAdReadyEvent`, `imps`, `step_count`, `adexp`
3. Capture the final candidate request that returns GPLinks 200 in the browser.
4. Diff this against `gplinks-delay16-imps0.json`.
5. If a minimal transferable proof is found, implement a hybrid:
   - browser only until PowerGam ledger candidate is accepted
   - transfer accepted GPLinks cookies/CSRF/form data into HTTP for final `/links/go`
   - keep current full-browser lane as fallback

Expected upside if this works: remove some browser time after candidate, not the full `~95s` ledger, unless the missing ledger side effect itself becomes replayable.

## Final oracle reached?

Yes, by current browser helper only.

- `artifacts/active/batch4-breakthrough/gplinks-live-current-run.json`
- `status=1`
- `final_url=http://tesskibidixxx.com/`

No, by pure HTTP or delay-based ledger replay.

- `artifacts/active/batch4-breakthrough/gplinks-delay16-imps0.json`
- final boundary: `not_enough_steps`
