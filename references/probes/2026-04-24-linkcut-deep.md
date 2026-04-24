# linkcut.pro deep probe - 2026-04-24

## Scope

Target family: `linkcut.pro`.

Task constraints:
- no production-code edits
- find existing samples in docs/references first
- map redirects, forms, scripts, API/captcha requirements
- be strict: do not claim a downstream final URL unless the exact target is proven

## Existing local references checked

Commands/paths checked:
- `grep -RInE "linkcut\.pro|linkcut|link cut|link-cut" docs references .`
- `references/target-sample-catalog.md`
- `references/shortlink-family-initial-map.md`
- `docs/FLOWS.md`

Result:
- No prior probe/sample/final-oracle entry for `linkcut.pro` exists in `docs/` or `references/`.
- Only local mention before this probe was `bot.py` status text listing `linkcut.pro` under unsupported/no handler.

## Samples found during live probing

No local sample was available, so I probed likely short aliases. These aliases are valid entry pages:

| URL | Entry status | Observed page title | OG title | Final URL proven? |
| --- | ---: | --- | --- | --- |
| `https://linkcut.pro/1` | 200 | `Linkcut.pro` | Arabic beIN Sports live page title | No |
| `https://linkcut.pro/free` | 200 | `Linkcut.pro` | `Car: Toyota` | No |

Invalid aliases tested:
- `https://linkcut.pro/test` -> 404 `Error`
- `https://linkcut.pro/google` -> 404 `Error`
- `https://linkcut.pro/abc` -> 404 `Error`
- `https://linkcut.pro/a` -> 404 `Error`
- `https://linkcut.pro/link` -> 404 `Error`
- `https://linkcut.pro/hello` -> 404 `Error`

Root behavior:
- `http://linkcut.pro` -> `301` to `https://linkcut.pro/`
- `https://www.linkcut.pro/` -> `301` to `https://linkcut.pro/`
- `https://linkcut.pro/` -> `200`, public landing page

## Platform/family fingerprint

`linkcut.pro` is an AdLinkFly-style deployment.

Evidence:
- frontend assets include `https://linkcut.pro/js/app.js?ver=6.4.0`
- `app_vars` contains standard AdLinkFly keys:
  - `base_url`
  - `enable_captcha`
  - `captcha_type`
  - `reCAPTCHA_site_key`
  - `captcha_shortlink`
  - `counter_value`
  - `counter_start`
  - `get_link`
  - `skip_ad`
- cookies set on entry:
  - `AppSession`
  - `csrfToken`
- CakePHP-style form fields:
  - `_method=POST`
  - `_csrfToken`
  - `_Token[fields]`
  - `_Token[unlocked]`

Cloudflare note:
- server header is `cloudflare`, but plain `requests` received origin pages normally.
- No Cloudflare managed challenge was observed on sampled entry pages.

## Entry page flow

For both `https://linkcut.pro/1` and `https://linkcut.pro/free`:

Initial response:
- `200 OK`
- no HTTP redirect
- body has `layout-top-nav skin-blue`
- not an interstitial `go-link` page yet

Visible protection UI:
1. Step One: `#firstStepButton` text `Click to Continue`
2. Step Two: `#secondStepButton` text `Click to Confirm`
3. Step Three: hidden `#captchaSection`, then final submit button `#invisibleCaptchaShortlink`

Important client-side script details:
- Step buttons only update `protectionStep` and reveal the captcha section.
- Step timing checks are client-side alerts only:
  - Step one sets a 15s warning timer if step two is not clicked.
  - Step two sets a 50s warning timer if captcha is not completed.
- The form submit handler only sets `protectionStep = 3` and returns true.

Conclusion for the step UI:
- The two click steps are cosmetic/client-side only.
- The real gate is the server-side captcha check on the POST.

## Captcha boundary

Active captcha config from `app_vars`:

```json
{
  "enable_captcha": "yes",
  "captcha_type": "recaptcha",
  "reCAPTCHA_site_key": "6LeQy4UrAAAAAOJRR7taiWW0-nveuVcrN2hNa3IT",
  "invisible_reCAPTCHA_site_key": "6LeQy4UrAAAAAOJRR7taiWW0-nveuVcrN2hNa3IT",
  "captcha_shortlink": "yes",
  "counter_value": "7",
  "counter_start": "DOMContentLoaded"
}
```

Loaded captcha script:
- `https://www.recaptcha.net/recaptcha/api.js?onload=onloadRecaptchaCallback&render=explicit`

DOM captcha container:
- `<div id="captchaShortlink" style="display: inline-block;"></div>`

`app.js` behavior:
- renders `captchaShortlink` with reCAPTCHA v2 when `captcha_type === 'recaptcha'`
- disables `#link-view .btn-captcha` until the reCAPTCHA callback removes the disabled state

Server replay proof:
- POSTing the hidden fields with blank `g-recaptcha-response` redirects back to the same alias and displays:
  - `The CAPTCHA was incorrect. Try again`
  - `Please check the captcha box to proceed to the destination page.`
- This happened for `https://linkcut.pro/free`; same shape observed for `https://linkcut.pro/1`.

POST shape tested:

```http
POST /free HTTP/1.1
Origin: https://linkcut.pro
Referer: https://linkcut.pro/free
Content-Type: application/x-www-form-urlencoded

_method=POST
&_csrfToken=<fresh csrf>
&ref=
&f_n=slc
&_Token[fields]=<fresh token fields>
&_Token[unlocked]=adcopy_challenge%7Cadcopy_response%7Ccaptcha_code%7Ccaptcha_namespace%7Cg-recaptcha-response
&g-recaptcha-response=
```

Observed result:

```text
302 Location: https://linkcut.pro/free
body after follow still contains form#link-view and captcha error
```

## Expected next boundary after captcha

Not proven live because no valid reCAPTCHA token was supplied.

Based on `app.js?ver=6.4.0`, after a successful captcha POST the AdLinkFly flow is expected to move to an interstitial/banner page that contains:
- `form#go-link`
- `action` likely `/links/go`
- hidden form fields / CSRF values
- timer controlled by `counter_value`, currently `7`
- AJAX POST to the `form#go-link` action
- JSON response with `url`

Important strictness:
- This is an expected AdLinkFly next stage from the shared frontend code, not a proven live stage for `linkcut.pro` because the captcha boundary blocked access.
- No exact downstream final target was proven for `/1` or `/free`.

## API/script map

Entry resources observed:
- `https://linkcut.pro/js/ads.js`
- `https://linkcut.pro/vendor/jquery.min.js?ver=6.4.0`
- `https://linkcut.pro/vendor/bootstrap/js/bootstrap.min.js?ver=6.4.0`
- `https://linkcut.pro/vendor/clipboard.min.js?ver=6.4.0`
- `https://linkcut.pro/js/app.js?ver=6.4.0`
- `https://linkcut.pro/vendor/dashboard/js/app.min.js?ver=6.4.0`
- `https://www.recaptcha.net/recaptcha/api.js?onload=onloadRecaptchaCallback&render=explicit`
- ad scripts:
  - `https://s0-greate.net/p/2565100`
  - `//wy.replansquiz.com/rYw9ZCruJQQQx/77584`
  - `https://a.pemsrv.com/popunder1000.js`

App.js relevant behavior:
- `#link-view` handles first captcha/shortlink POST.
- `#go-link` handler is AJAX-only and expects JSON.
- For `interstitial` pages it writes `result.url` into `.skip-ad a`.
- For `banner` pages it writes `result.url` into `a.get-link`.

No custom signing/header API was observed on the entry page beyond CakePHP CSRF/security form tokens.

## Boundary catalog

| Boundary | Location | Relevance | Evidence | Status |
| --- | --- | --- | --- | --- |
| Alias existence | `GET /<alias>` | Distinguishes valid shortlink from 404 | `/1` and `/free` return 200; common invalid aliases return 404 | closed |
| Session/CSRF | `AppSession`, `csrfToken`, hidden `_csrfToken`, `_Token[...]` | Required for POST replay | Entry page sets cookies and hidden CakePHP fields | narrowed |
| Human-step UI | inline protection script around `#firstStepButton`, `#secondStepButton`, `#captchaSection` | Looks like a gate but only client-side | POST can be sent directly; errors are captcha-specific, not step-specific | falsified as primary |
| Captcha gate | `#captchaShortlink`, reCAPTCHA v2 sitekey `6LeQy4UrAAAAAOJRR7taiWW0-nveuVcrN2hNa3IT` | Blocks first POST and prevents reaching timer/go-link page | blank token returns captcha error | primary/open |
| Timer/go-link | expected `form#go-link` + `/links/go` from `app.js` | Likely final URL release boundary after captcha | frontend code exists, but not reached live for this host | open/unproven |
| Final downstream URL | JSON `url` from expected `/links/go` response | Success oracle | Not reached; no exact final URL observed | open/unproven |

## Browserless feasibility

Without a valid reCAPTCHA token:
- A pure browserless handler is not feasible for final bypass.
- It can only return analysis-stage facts: valid alias, captcha config, sitekey, cookies/forms, and blocker.

With a valid external reCAPTCHA v2 solver token:
- Browserless completion is likely feasible, because the initial steps are static/client-side and server state is standard CakePHP session + CSRF.
- The handler would need to:
  1. `GET https://linkcut.pro/<alias>`
  2. parse fresh hidden fields from `form#link-view`
  3. obtain reCAPTCHA v2 token for sitekey `6LeQy4UrAAAAAOJRR7taiWW0-nveuVcrN2hNa3IT` on the exact alias URL
  4. `POST /<alias>` with hidden fields + `g-recaptcha-response`
  5. parse the returned/redirected interstitial page for `form#go-link`
  6. wait the real timer, likely `7s` plus safety margin
  7. `POST /links/go` with fresh same-session hidden fields
  8. accept success only if JSON contains a concrete external `url`

Caveat:
- Step 5 onward is inferred from shared `app.js`, not proven for `linkcut.pro` because captcha blocked the live path.

## Strict final status

`linkcut.pro` is mapped as an AdLinkFly/reCAPTCHA family, but no final downstream URL is proven.

Recommended engine status:
- `analysis-only / captcha-gated`

Do not label `linkcut.pro` as live bypass supported until a run returns the exact downstream final URL from the post-captcha `go-link` flow.
