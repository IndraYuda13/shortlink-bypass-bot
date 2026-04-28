# 2026-04-28 GPLinks final candidate JS analysis

Target final candidate: `https://gplinks.co/YVTC?pid=1224622&vid=<vid>` after PowerGam completion.

## Scope

Read and cross-checked:

- `artifacts/active/2026-04-28-gplinks-final-push-workframe.md`
- `artifacts/active/2026-04-28-gplinks-final-contract-investigation.md`
- `artifacts/active/2026-04-28-gplinks-gpt-continuation.md`
- CDP logs: `gplinks-cdp-natural*.log`, `gplinks-cdp-wait.log`, `gplinks-cdp-force.log`
- Fetched current JS:
  - `https://api.gplinks.com/track/js/main.js` -> saved as `main-fetched-2026-04-28.js`
  - `https://api.gplinks.com/track/js/power-cdn.js?v=2.0.0.5` -> saved as `gplinks-js-4.js`
  - `https://gplinks.co/js/ads.js?ver=6.4.3.8` -> saved as `gplinks-js-0.js`

No production files changed.

## Confirmed facts

### 1. The observed final page is a normal AdLinkFly/GPLinks banner page gate

The stuck DOM from the long CDP run repeatedly shows:

```json
{"tag":"A","text":"Please wait...","id":"captchaButton","cls":"btn btn-primary rounded get-link xclude-popad disabled"}
```

Page text says `Please wait for 0 seconds`, but the anchor remains classed `disabled` through loops 17-44 and final state.

### 2. `#captchaButton` unlock is controlled by `gplinks.co/js/ads.js`, not by PowerGam `power-cdn.js`

Fetched `gplinks.co/js/ads.js?ver=6.4.3.8` contains all relevant `#captchaButton` writes:

- lines 17-20 initialize gate state:

```js
var myTime = app_vars['counter_value'];
var isTimerEnd = false;
var isCaptchaFilled = false;
let captchaCompleted = false;
```

- lines 646-665, banner timer completion:

```js
if (app_vars['captcha_links_go'] === 'no' || app_vars['captcha_links_go_plan'] === 'no') {
  $('#go-link').addClass('go-link');
  $('#go-link.go-link').submit();
} else {
  if (app_vars['cloudflare_turnstile_on'] === 'no') {
    isTimerEnd = true;
    if (isCaptchaFilled) {
      $('#captchaButton').removeClass('disabled').text(app_vars['get_link']);
    }
  } else {
    isTimerEnd = true;
    checkAndSubmitForm();
  }
}
```

- lines 51-61, non-Turnstile captcha input unlock:

```js
$(document).on("input", "#captchaShortlink_captcha", function () {
  var captchaCode = $(this).val();
  if (captchaCode.length === 4) {
    isCaptchaFilled = true;
    if (isTimerEnd) {
      $('#captchaButton').removeClass('disabled').text(app_vars['get_link']);
    }
  }
});
```

- lines 1247-1256, Turnstile unlock path:

```js
function onTurnstileCompleted(token) {
  captchaCompleted = true;
  checkAndSubmitForm();
}

function checkAndSubmitForm() {
  if (isTimerEnd && captchaCompleted) {
    $('#go-link').addClass('go-link');
    $('#go-link.go-link').submit();
  }
}
```

### 3. In the stuck CDP run the timer condition is satisfied, but captcha completion is not

Evidence:

- DOM says `Please wait for 0 seconds`, so timer reached zero.
- `#captchaButton` text remains `Please wait...` and class remains `disabled`.
- CDP visible candidates show no successful `Get Link` state and no navigation to downstream.
- CDP state shows no form submissions from final page after reaching candidate: `forms: []`.

This matches `ads.js`: timer alone is not enough when `captcha_links_go === 'yes'` and `captcha_links_go_plan === 'yes'`. The page must also get either:

- `isCaptchaFilled = true` via `#captchaShortlink_captcha` length 4, or
- `captchaCompleted = true` via `onTurnstileCompleted(token)`.

### 4. PowerGam proof spoofing is not the direct final-button issue

`power-cdn.js` controls the PowerGam steps and posts `step_id/ad_impressions/visitor_id/next_target` via `#adsForm`. Current and fetched variants confirm that flow. Existing CDP logs prove PowerGam completed enough to land at the GPlinks candidate 200 page.

The final-page stuck state happens after PowerGam. It is now narrowed to the final page's captcha/timer gate in `ads.js`.

### 5. Current curl/curl_cffi cannot fetch candidate HTML as a final-page oracle

`curl_cffi` direct fetch of the browser candidate URL still returned Cloudflare `403 Just a moment...`, while the browser got `200`. So helper patch must operate in the live browser/CDP context, not pure replay.

## Hypotheses tested

### H1: The disabled button is waiting only for the countdown

Falsified. CDP shows `Please wait for 0 seconds` for many loops while `#captchaButton.disabled` remains.

### H2: The disabled button is waiting for PowerGam `imps` / GPT events

Partially related upstream but not the direct final DOM cause. Existing forced runs set `imps/adexp` and completed visible PowerGam submits, but final candidate still reached a separate GPlinks gate. The final JS unlock condition is captcha state plus timer, not GPT state.

### H3: The final page requires captcha completion

Supported by exact code in `ads.js`. `#captchaButton` is only enabled in the captcha branch after `isTimerEnd && isCaptchaFilled`. In the Turnstile branch it bypasses the button and submits `#go-link` after `isTimerEnd && captchaCompleted`.

## Exact cause of stuck `#captchaButton`

The final GPlinks page has entered the captcha-protected links-go branch:

```js
app_vars['captcha_links_go'] === 'yes'
app_vars['captcha_links_go_plan'] === 'yes'
```

The countdown finished, but no captcha completion state was produced in the page JS:

- non-Turnstile branch: no `#captchaShortlink_captcha` input event set `isCaptchaFilled = true`
- Turnstile branch: no `onTurnstileCompleted(token)` callback set lexical `captchaCompleted = true`

Therefore `ads.js` never executes either:

```js
$('#captchaButton').removeClass('disabled').text(app_vars['get_link']);
```

or:

```js
$('#go-link').addClass('go-link');
$('#go-link.go-link').submit();
```

## Smallest browser helper patch proposal

Patch only the GPLinks browser-helper lane, not the HTTP replay path.

### Guard condition

Run this helper only after all are true:

1. browser URL matches `https://gplinks.co/<alias>?pid=<pid>&vid=<vid>`
2. DOM has `#captchaButton.disabled`
3. page text or `#myTimer` indicates countdown reached `0`
4. page has `form#go-link`
5. still no downstream navigation after a short grace wait

### Hook 1: inspect final gate vars

In the live CDP page, evaluate:

```js
(() => ({
  href: location.href,
  app_vars: window.app_vars || null,
  button: document.querySelector('#captchaButton')?.outerHTML || null,
  captchaInput: !!document.querySelector('#captchaShortlink_captcha'),
  captchaLinksGo: window.app_vars?.captcha_links_go,
  captchaLinksGoPlan: window.app_vars?.captcha_links_go_plan,
  turnstileOn: window.app_vars?.cloudflare_turnstile_on,
  timerText: document.querySelector('#myTimer')?.textContent || null,
  goLinkAction: document.querySelector('#go-link')?.action || null,
}))();
```

### Hook 2A: non-Turnstile captcha branch

If:

```js
app_vars.captcha_links_go === 'yes' &&
app_vars.captcha_links_go_plan === 'yes' &&
app_vars.cloudflare_turnstile_on === 'no'
```

then the smallest live-browser unlock is:

```js
(() => {
  window.isTimerEnd = true;
  window.isCaptchaFilled = true;
  const btn = document.querySelector('#captchaButton');
  if (btn) {
    btn.classList.remove('disabled');
    btn.textContent = window.app_vars?.get_link || 'Get Link';
  }
})();
```

Then click `#captchaButton`. Its existing site handler will add `.go-link` and submit `#go-link`.

### Hook 2B: Turnstile branch

If:

```js
app_vars.captcha_links_go === 'yes' &&
app_vars.captcha_links_go_plan === 'yes' &&
app_vars.cloudflare_turnstile_on !== 'no'
```

then do not try to mutate `captchaCompleted` directly because it is declared with `let` and is not a `window` property. Use the page's own global function if present:

```js
(() => {
  window.isTimerEnd = true;
  if (typeof window.onTurnstileCompleted === 'function') {
    window.onTurnstileCompleted('__helper_token__');
  }
})();
```

If `onTurnstileCompleted` is not exposed, fallback is direct form submission through the same endpoint:

```js
(() => {
  const form = document.querySelector('#go-link');
  if (form && window.jQuery) {
    window.jQuery(form).addClass('go-link').trigger('submit');
  }
})();
```

### Hook 3: success oracle

After the helper action, capture:

- `Network.requestWillBeSent` and response body for `POST /links/go`
- any JSON `{url: ...}` returned by that request
- final navigation URL

Return success only when browser reaches a non-`gplinks.co`, non-`link-error`, non-`powergam.online` URL, expected for this sample: `http://tesskibidixxx.com`.

## Patch risk notes

- Do not mark HTTP replay as solved. Curl candidate still hits Cloudflare 403.
- Do not blindly click disabled buttons before countdown zero.
- Do not promote unless `/links/go` returns `result.url` or browser navigates to downstream.
- This is a helper patch around the final-page gate only. It does not prove or replace the earlier server-side PowerGam ledger.
