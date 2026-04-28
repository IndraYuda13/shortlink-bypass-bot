# XUT optimization report

Scope: `https://xut.io/hd7AOJ` only. Production code was not edited.

Final oracle to preserve: `http://tesskibidixxx.com/`.

## Baseline

Current production lane is the all-browser helper through `xut_live_browser.py`, invoked by `engine.py` for the `autodime.cwsafelinkphp` family.

Current proven path:

1. Browser opens `https://xut.io/hd7AOJ`.
2. XUT wrapper redirects to `https://autodime.com/cwsafelinkphp/go.php?link=snpurl%2Fhd7AOJ`.
3. Autodime warmup lands on `https://autodime.com/`, `Step 1/6`.
4. Browser solves Step 1 IconCaptcha.
5. Browser clicks Step 2, Step 3, Step 4 timed transitions.
6. Browser reaches `gamescrate.app`, waits for `Open Final Page`.
7. Helper adds a fixed `14s` dwell to avoid `Error: too_fast`, then clicks `Open Final Page`.
8. Browser reaches XUT Step 6 and waits for exact visible `Get Link`.
9. Helper clicks exact `Get Link`, then returns the final href/current URL.

Prior live proof in `artifacts/active/2026-04-28-xut-continuation-workframe.md`:

- helper returned `status=1`, `message=XUT_FINAL_OK`, `stage=final-bypass`
- `bypass_url=http://tesskibidixxx.com/`
- engine live verification also returned the same final oracle

Prior timing baseline in `artifacts/active/2026-04-28-xut-http-hybrid-subagent.md`:

- all-browser helper run: `116.99s`
- run required 2 IconCaptcha attempts

Small fresh HTTP preflight for this report confirmed the front half is still the same contract:

- `GET https://xut.io/hd7AOJ` -> `302 https://autodime.com/cwsafelinkphp/go.php?link=snpurl%2Fhd7AOJ`
- `go.php` -> Google wrapper for `https://autodime.com/`
- warmed `https://autodime.com/` -> title `Step 1/6`
- cookies include `AppSession`, `refhd7AOJ`, `fexkomin`, `CWSLSESSID`
- page exposes `_iconcaptcha-token`
- `window.SL_CFG` still says `step:1`, `countdown:10`, `captchaProvider:'iconcaptcha'`, `iconcaptchaEndpoint:'/cwsafelinkphp/sl-iconcaptcha-request.php'`, `verifyUrl:'/cwsafelinkphp/sl-iconcaptcha-verify.php'`

## Boundary catalog

| Boundary | Status | Meaning for optimization |
|---|---:|---|
| XUT wrapper -> Autodime go.php | closed | Safe to do with HTTP. |
| Autodime warmup -> Step 1 | closed | Safe to do with HTTP. |
| Step 1 IconCaptcha protocol | closed for HTTP solving | HTTP LOAD/SELECTION/verify is proven in older report. |
| Autodime/Textfrog Steps 2-4 timers | HTTP-proven but handoff-risky | HTTP can advance them, but resulting gamescrate token rejected when opened in browser. |
| Gamescrate setcookie token | primary constraint | Token appears bound to client/fingerprint. Wrong client handoff gives `Forbidden.` |
| Gamescrate Cloudflare/page gate | browser required | Pure HTTP/curl path is not proven and previously hit Cloudflare/403. |
| Gamescrate too-fast guard | narrowed | Clicking exactly at timer flip can fail. Current `14s` dwell is safe but likely oversized. |
| XUT Step 6 final `Get Link` | closed | Once visible exact `Get Link` has final href, final oracle is already available. |

## Falsified or unsafe lanes

### 1. HTTP Steps 1-4 then browser at gamescrate

Status: falsified for current implementation shape.

Evidence from `artifacts/active/2026-04-28-xut-hybrid-integration-attempt.md`:

- HTTP warmup reached `gamescrate.app/cwsafelinkphp/setcookie.php?t=...`.
- Browser launched directly on that gamescrate setcookie URL.
- Gamescrate returned `Forbidden.`.
- Retrying with HTTP UA changed to installed Chrome major still returned `Forbidden.`.

Interpretation: the `t=` token generated after HTTP Step 4 is not portable to a later Chrome context. Do not wire this lane.

### 2. Pure HTTP gamescrate

Status: falsified/not worth repeating as first pass.

Evidence:

- Previous pure HTTP to gamescrate setcookie landed on Cloudflare `Just a moment...` or 403.
- No browserless oracle exists for gamescrate Step 5.

Interpretation: gamescrate remains the browser boundary.

### 3. Step 6 `/links/go` before gamescrate signed `sl=` URL

Status: impossible with current evidence.

Reason: the signed `xut.io/hd7AOJ?sl=...` URL is produced only after gamescrate Step 5. The final form cannot be reconstructed from XUT entry/static HTML.

## Candidate skips and faster lanes

### Candidate A: skip final Step 6 click once exact visible `Get Link` href is available

Expected gain: about `5s`, plus lower click risk.

Current code already calls `final_url_from_current_state(driver)` before clicking. That function returns the visible exact `Get Link` href if it is a non-blocklisted URL. For this target, prior final-state evidence showed that href is already `http://tesskibidixxx.com/`.

Safer optimized behavior:

- If exact visible `Get Link` href is present and host is not in the XUT blocklist, return it immediately.
- Do not click it.
- Keep click fallback only if href is missing or still blocklisted.

Why this is safe: the bot's oracle is the downstream URL, not a confirmed downstream page visit. Returning the already visible exact href preserves `http://tesskibidixxx.com/` and avoids ad-neighbor click risk.

### Candidate B: reduce fixed gamescrate dwell with a measured ladder

Expected gain: likely `5-9s` if stable.

Current code waits for `Open Final Page`, then sleeps a fixed `14s`. Prior root cause says clicking exactly when the timer flips can trigger `Error: too_fast`, so zero dwell is unsafe. But `14s` is probably conservative.

Recommended probe shape, not production-first:

- Create a temporary helper variant or env-controlled dwell.
- Test dwell values in order: `5s`, `8s`, `11s`, `14s`.
- Success oracle must be final `http://tesskibidixxx.com/`, not just navigation away from gamescrate.
- Promote the lowest dwell only after at least 2 consecutive successes.

Current recommendation: do not cut directly to 0-3s. The too-fast guard is real.

### Candidate C: replace Step 1 browser sleeps with state polling

Expected gain: small to moderate, usually `2-8s`, larger on failed captcha attempts.

Current Step 1 has fixed sleeps:

- `time.sleep(12)` after Step 1 page load, even though page config says `countdown:10`.
- `time.sleep(4)` after widget click before reading canvas.
- `time.sleep(6)` after canvas selection before checking Step 2.

Safer optimized behavior:

- Poll DOM/countdown/widget readiness instead of fixed `12s`.
- After widget click, poll until `canvas.toDataURL()` is available instead of fixed `4s`.
- After selection, poll for Step 2 title/body or a new challenge/reset instead of fixed `6s`.

This does not cross the gamescrate fingerprint boundary, so it is lower risk than HTTP Step 2-4 handoff.

### Candidate D: HTTP Step 1 only, then browser from Step 2 with imported cookies

Expected gain: possible stability gain more than raw speed. Speed gain depends on whether browser launch happens in parallel.

Shape:

1. HTTP does XUT entry, Autodime warmup, IconCaptcha LOAD/SELECTION/verify.
2. Launch browser separately, preferably while HTTP Step 1 is running.
3. Import relevant cookies into the browser for Autodime/Textfrog domains.
4. Browser starts at the verified Step 2 URL and generates Steps 2-4 and gamescrate token itself.

Why it may preserve gamescrate: Step 2-4 tokens would be generated by browser, not by requests, so the gamescrate `t=` token should match the browser fingerprint.

Status: not proven. A prior rough attempt timed out, but it did not falsify the lane. It needs better progress logging before promotion.

Risk: cookie path/domain import can be brittle, and `fexkomin` has an `fp` claim. If Autodime binds the Step 1 verification to the HTTP fingerprint, browser Step 2 may fail or later emit a mismatched gamescrate token.

### Candidate E: browser-started session plus HTTP IconCaptcha through browser cookies

Expected gain: mainly Step 1 reliability/debuggability, possibly `5-15s` on retries.

Shape:

- Browser performs wrapper and Step 1 page load, so cookies/fingerprint stay browser-native.
- Extract `_iconcaptcha-token` and cookies from the browser.
- Use HTTP inside the same runtime to call IconCaptcha LOAD/SELECTION/verify.
- Inject only the resulting navigation/redirect back into the browser.

This avoids the simple HTTP->browser token mismatch because the initial session is browser-born. It still needs proof because server-side session might compare request fingerprints on IconCaptcha endpoints.

## Recommendation

Best next optimization order:

1. **Implement/probe Candidate A first**: return the exact visible Step 6 `Get Link` href without clicking. This is the smallest change and should save about `5s` while preserving `http://tesskibidixxx.com/`.
2. **Probe Candidate B second**: add an env-controlled gamescrate dwell and find the lowest stable value. This is the largest safe-ish speed win inside the proven browser lane.
3. **Patch Candidate C third**: replace Step 1 fixed sleeps with polling. This should improve retries without changing protocol boundaries.
4. **Only then revisit HTTP hybrid**: do not use HTTP Steps 1-4 -> browser gamescrate. If hybrid is retried, use either HTTP Step 1 only then browser Step 2, or browser-born cookies plus HTTP IconCaptcha.

Do not remove the full-browser fallback. Current final success depends on browser-generated state through gamescrate.

## Expected impact

Without crossing risky boundaries:

- Candidate A: `~5s` faster.
- Candidate B: likely `~5-9s` faster if lower dwell works.
- Candidate C: `~2-8s` faster per successful run, more on failed Step 1 attempts.

Conservative target after safe optimizations: reduce the observed `~117s` baseline to roughly `95-105s` while keeping the same final oracle.

More aggressive hybrid target remains possible, but only after proving browser-generated gamescrate tokens stay valid.
