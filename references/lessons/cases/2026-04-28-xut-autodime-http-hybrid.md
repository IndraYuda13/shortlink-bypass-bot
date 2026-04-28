# 2026-04-28 xut/autodime HTTP hybrid case note

## Proven
- `xut.io/hd7AOJ` still wraps into `autodime.com/cwsafelinkphp`.
- Autodime IconCaptcha can be solved without a browser once the Step 1 page is warmed and `_iconcaptcha-token` + `CWSLSESSID` are present.
- IconCaptcha v4 client payload is base64 JSON, not encrypted:
  - `LOAD`: `{widgetId, action:"LOAD", theme, token, timestamp, initTimestamp}`
  - `SELECTION`: `{widgetId, challengeId, action:"SELECTION", x, y, width, token, timestamp, initTimestamp}`
  - header: `X-IconCaptcha-Token`.
- HTTP `/sl-iconcaptcha-verify.php` with `_iconcaptcha-token`, `ic-rq`, `ic-wid`, `ic-cid`, `ic-hp` returned Step 2 redirect.
- HTTP can advance Step 2, Step 3, and Step 4 by parsing `window.SL_CFG.nextUrl`, waiting countdown, and POSTing `1=1`.
- Pure HTTP to gamescrate setcookie still lands on Cloudflare `Just a moment...`.
- After gamescrate produces `xut.io?...sl=...`, XUT Step 6 can be completed over HTTP by posting `form#go-link` to `/links/go` after the 5s wait.

## Not proven
- Browserless gamescrate Step 5 is not proven.
- Exporting gamescrate cookies after browser clearance and completing Step 5 by HTTP is plausible but not live-proven yet.

## Failed / do not repeat blindly
- Do not spend the first optimization pass trying pure HTTP against gamescrate. It already returned Cloudflare challenge.
- Do not keep using Selenium for autodime Steps 1-4 as the only lane; those parts are now HTTP-proven and are the low-risk speed win.

## Next best action
Implement an optional hybrid helper mode: HTTP through autodime/textfrog to gamescrate, browser only for gamescrate Cloudflare/Step 5, then HTTP for xut `/links/go`.

Main report: `artifacts/active/2026-04-28-xut-http-hybrid-subagent.md`.

## Optimization update 2026-04-28
- The simple `HTTP Steps 1-4 -> browser gamescrate` lane was later falsified: gamescrate returned `Forbidden.` even after matching HTTP UA to installed Chrome major. Treat the gamescrate `t=` token as browser/fingerprint-bound until proven otherwise.
- Do not promote a hybrid that generates Step 2-4 tokens in requests and opens gamescrate in Chrome.
- Safer optimization order is now:
  1. return visible exact XUT Step 6 `Get Link` href without clicking when it already equals the downstream oracle;
  2. probe lower gamescrate dwell values with an env-controlled temporary helper before reducing the current safe `14s` wait;
  3. replace Step 1 fixed sleeps with DOM/state polling;
  4. only retry hybrid as HTTP Step 1 only -> browser Step 2, or browser-born cookies -> HTTP IconCaptcha.
- Detailed report: `artifacts/active/total-optimization/xut-optimization-report.md`.
