# GPLinks optimization report

Target: `https://gplinks.co/YVTC`  
Expected final oracle: `http://tesskibidixxx.com/`  
Scope: research only. No production code edited.

## Parent checklist

- [done] Read current GPLinks handler and active notes.
- [done] Measure current engine/HTTP-fast behavior on the live sample.
- [done] Identify removable steps and falsified skip hypotheses.
- [done] Save next implementation recommendation.

## Current baseline measured

### Engine end-to-end

Command:

```bash
cd /root/.openclaw/workspace/projects/shortlink-bypass-bot
.venv/bin/python engine.py https://gplinks.co/YVTC --pretty
```

Result:

- Wall time measured by shell: `178.84s`
- Engine status: `status=1`
- Stage: `live-browser`
- Final URL: `http://tesskibidixxx.com/`
- Engine facts:
  - `http_fast_stage=powergam-ledger`
  - `http_fast_message=HTTP_FAST_POWERGAM_LEDGER_REJECTED`
  - `http_fast_waited_seconds=2.64`
  - `live_stage=live-browser-final-gate`
  - `token_used=true`
  - `sitekey=0x4AAAAAAAynCEcs0RV-UleY`
  - `live waited_seconds=174.2`

Meaning: current production lane is correct but slow. It first spends ~2.5s proving the HTTP fast lane still fails, then falls back to the live browser path.

### HTTP fast lane only

Command:

```bash
.venv/bin/python gplinks_http_fast.py https://gplinks.co/YVTC --timeout 90
```

Result:

- `status=0`
- `stage=powergam-ledger`
- `message=HTTP_FAST_POWERGAM_LEDGER_REJECTED`
- `waited_seconds=2.44`
- Candidate: `https://gplinks.co/YVTC?pid=1224622&vid=<raw vid>`
- Final server response: `302 -> https://gplinks.co/link-error?alias=YVTC&error_code=not_enough_steps`

Meaning: HTTP fast remains useful as a diagnostic, but for this exact target it is currently an expected negative preflight.

### Extra direct helper probe

A direct helper run was attempted to inspect timeline, but it returned after `184.53s` with Selenium driver connection refused:

```text
HTTPConnectionPool(host='localhost', port=39821): Max retries exceeded ... Failed to establish a new connection: [Errno 111] Connection refused
```

Evidence still written by the helper before disconnect:

- `artifacts/active/gplinks-final-probe/latest_before_unlock.json`
- page was already at `https://gplinks.co/YVTC?pid=1224622&vid=<raw vid>`
- `form#go-link` existed
- Turnstile sitekey existed: `0x4AAAAAAAynCEcs0RV-UleY`
- `#captchaButton` was disabled and page said `Please wait for 0 seconds`
- adblock panel image was present in captured state

I am not treating this as an optimization conclusion. It only shows the helper can lose ChromeDriver late in the final-gate phase and should preserve timeline on exceptions.

## Current GPLinks flow in code

`engine.py` order:

1. `_resolve_gplinks_http_fast()`
2. if it fails, `_resolve_gplinks_live()`
3. if live fails, static PowerGam mapper fallback

`gplinks_live_browser.py` path:

1. curl_cffi entry request to get PowerGam URL and decode query.
2. launch undetected Chrome under Xvfb.
3. open original GPLinks URL.
4. wait fixed `12s`.
5. if not on PowerGam, navigate to PowerGam URL with referer and wait another fixed `12s`.
6. click PowerGam Verify/Continue loop, sleeping fixed `9s` after each click.
7. after GPLinks candidate, sleep fixed `8s`.
8. wait away Cloudflare, solve Turnstile, call page callback/form submit.
9. return success only if final URL is non-GPLinks/non-PowerGam/non-link-error.

## Candidate skips and optimizations

### 1. Skip HTTP-fast preflight by default for GPLinks YVTC

Expected saving: `~2.4s to ~2.7s` per successful run.

Evidence:

- Measured HTTP fast run failed in `2.44s` with `not_enough_steps`.
- Engine baseline also shows HTTP fast failed in `2.64s` before live success.
- Prior notes falsified visible form fields, cookies, Tracki pop/banner, conversion calls, raw `vid`, forced `imps/adexp`, and pure HTTP replay.

Recommendation:

- Add env switch such as `SHORTLINK_BYPASS_GPLINKS_HTTP_PREFLIGHT=0` or make live browser the default for `gplinks.co` while keeping HTTP fast as explicit diagnostic.
- This is safe because success still depends on the live browser final oracle.

### 2. Replace fixed browser sleeps with state-driven waits

Expected saving: likely `25s to 45s`, depending on page/network timing.

Current fixed waits that look removable or reducible:

- `time.sleep(12)` after initial `driver.get(url)`.
- possible second `time.sleep(12)` after direct PowerGam navigation.
- `time.sleep(9)` after every PowerGam click.
- `time.sleep(8)` before final candidate inspection.

Safer faster lane:

- After navigation, poll every `0.5s to 1s` for:
  - host becomes `powergam.online`, or
  - `form#adsForm` exists, or
  - clickable `Verify` / `Continue` exists.
- In PowerGam loop, click immediately when `Verify` is enabled or `Continue` is enabled and `waitLeft <= 0`.
- After each click, poll for URL/body/button change instead of always sleeping 9s.
- After reaching GPLinks candidate, poll for `form#go-link`, `window.app_vars`, or Turnstile sitekey instead of sleeping 8s.

Do not lower any server-side wait blindly. Keep the polling bounded and success-oracle gated.

### 3. Start browser directly at PowerGam URL, with GPLinks entry cookies imported

Expected saving: possible `~10s to ~12s` if verified.

Reasoning:

- Helper already performs a curl_cffi entry request before Chrome launch and obtains the PowerGam URL.
- Current browser still opens the original GPLinks URL first, then waits 12s.
- A safer shortcut is:
  1. curl_cffi `GET https://gplinks.co/YVTC` as now.
  2. copy `AppSession` and `csrfToken` from curl session into Chrome for `.gplinks.co`.
  3. enable CDP extra header `Referer: https://gplinks.co/YVTC`.
  4. navigate Chrome directly to the PowerGam URL.

Risk:

- If GPLinks/Cloudflare binds entry cookies to browser TLS/client fingerprint, imported curl cookies may not be enough.
- Therefore implement behind a flag first, e.g. `SHORTLINK_BYPASS_GPLINKS_DIRECT_POWERGAM=1`, and fall back to current original-URL browser route if final candidate or `/links/go` fails.

### 4. Preserve helper timeline on exception

Expected speed saving: none. Debug value: high.

Evidence:

- Direct helper probe reached final gate artifacts but returned only top-level exception JSON, losing timeline.

Recommendation:

- Wrap the late final-gate section inside `run()` so exceptions return `status=0`, `stage=<actual stage>`, `timeline=<captured timeline>`, and `last_state=<state if available>`.
- This makes future optimization attempts cheaper because a failed live probe still tells us which wait/gate failed.

## Hypotheses falsified

- Pure HTTP PowerGam form replay is enough. Falsified by current `gplinks_http_fast.py` and prior ledger probes. Result remains `not_enough_steps`.
- Visible cookies/fields like `step_count`, `imps`, `adexp`, `visitor_id`, `next_target` are enough. Falsified.
- Using raw encoded `vid` instead of decoded numeric `vid` solves HTTP replay. Falsified in prior raw-vid probe.
- Tracki pop/config/serve/track or banner impressions satisfy the ledger. Falsified.
- `gplinks.com/track/data.php addConversion` is the missing proof. Falsified, returned 500 and did not fix ledger.
- Final GPLinks disabled button waits only for countdown. Falsified. Page can show `Please wait for 0 seconds` while `#captchaButton` remains disabled.
- The final Turnstile/callback can be removed. Falsified by `ads.js` analysis and live success: final oracle requires the final gate to submit `/links/go` and expose the downstream URL.

## What should not be removed

- Do not remove the PowerGam 3-step browser path yet. It is still the only proven path to a valid GPLinks candidate before final gate.
- Do not treat `target_final_candidate` as success. It can still redirect to `link-error?error_code=not_enough_steps`.
- Do not remove final Turnstile solving or `onTurnstileCompleted` callback path.
- Do not promote HTTP fast to success for this sample.

## Exact next implementation recommendation

Implement a guarded GPLinks live-helper optimization branch, not a broad refactor:

1. Add `SHORTLINK_BYPASS_GPLINKS_HTTP_PREFLIGHT=0` default for GPLinks, or skip HTTP fast when host is `gplinks.co` and target is known to require PowerGam ledger.
2. In `gplinks_live_browser.py`, replace fixed sleeps with bounded state polling:
   - `wait_for_powergam_ready(max=15)`
   - `wait_for_clickable_powergam_action(max=15)`
   - `wait_for_gplinks_candidate(max=20)`
   - `wait_for_final_gate_ready(max=15)`
3. Add optional direct-PowerGam start behind env flag:
   - copy entry cookies into Chrome
   - navigate directly to PowerGam URL with referer
   - fallback to current original URL route if any oracle fails
4. Keep final success oracle unchanged:
   - success only if `/links/go` or browser state exposes a non-`gplinks.co`, non-`powergam.online`, non-`link-error` URL
   - expected sample target: `http://tesskibidixxx.com/`
5. Add timeline-on-exception return so failed optimization probes remain diagnosable.

Best first patch order:

1. Sleep-to-poll conversion in live helper.
2. Disable/skippable HTTP fast preflight.
3. Direct-PowerGam start as an experimental flag only after 1 and 2 are verified.

This keeps the current final oracle intact while targeting the real waste: fixed sleeps and a known-negative HTTP preflight.
