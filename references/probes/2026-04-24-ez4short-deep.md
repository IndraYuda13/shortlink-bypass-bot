# Deep probe: `ez4short.com/qSyPzeo`

Date: 2026-04-24 Asia/Jakarta  
Scope: safe HTTP replay only, using `.venv` `curl_cffi` Chrome impersonation. No engine/code edits.

## Result

Expected oracle is confirmed with preserved same-session final form replay:

```json
{"status":"success","message":"Go without Earn because Adblock","url":"https://tesskibidixxx.com"}
```

This family is ready for a small browserless handler.

## Full observed newwpsafelink sequence

Canonical multi-domain path:

1. `GET https://ez4short.com/qSyPzeo`
   - status: `307`
   - `Location: https://tech8s.net/safe.php?link=qSyPzeo`
   - sets `ez4short.com` cookie:
     - `AppSession=<hex>`
2. `GET https://tech8s.net/safe.php?link=qSyPzeo` with `Referer: https://ez4short.com/qSyPzeo`
   - status: `200`
   - sets `tech8s.net` cookie:
     - `tp=qSyPzeo; Max-Age=180`
   - body JS redirects via Google wrapper to a rotating `tech8s.net` article.
3. `GET <tech8s article>` with `Referer: https://tech8s.net/safe.php?link=qSyPzeo`
   - returns form with hidden `newwpsafelink=qSyPzeo`.
4. `POST <tech8s article>` with:
   - headers: `Origin: https://tech8s.net`, `Referer: <tech8s article>`
   - body: `newwpsafelink=qSyPzeo`
   - returns intermediate page containing `https://game5s.com/safe.php?link=qSyPzeo`.
5. `GET https://game5s.com/safe.php?link=qSyPzeo` with `Referer: <tech8s article>`
   - status: `200`
   - sets `game5s.com` cookie:
     - `tp=qSyPzeo; Max-Age=180`
   - body JS redirects via Bing wrapper (`u=a1<base64url>`) to a rotating `game5s.com` article.
6. `GET <game5s article>` with `Referer: https://game5s.com/safe.php?link=qSyPzeo`
   - returns form with hidden `newwpsafelink=qSyPzeo`.
7. `POST <game5s article>` with:
   - headers: `Origin: https://game5s.com`, `Referer: <game5s article>`
   - body: `newwpsafelink=qSyPzeo`
   - returns step `4/4` page containing link back to `https://ez4short.com/qSyPzeo` and JS timer `count3 = 3`.
8. `GET https://ez4short.com/qSyPzeo` with `Referer: <game5s article>` (or just `https://game5s.com/`)
   - status: `200`
   - returns final `form#go-link action="/links/go"`
   - sets/uses `ez4short.com` cookies:
     - `AppSession=<hex>`
     - `csrfToken=<long hex>`
     - `app_visitor=<Cake-style value>; Max-Age=86400`
   - hidden fields:
     - `_method=POST`
     - `_csrfToken=<same value as csrfToken cookie>`
     - `ad_form_data=<fresh same-session blob>`
     - `_Token[fields]=...%3Aad_form_data`
     - `_Token[unlocked]=adcopy_challenge%7Cadcopy_response%7Ccaptcha_code%7Ccaptcha_namespace%7Cg-recaptcha-response`
9. Wait for the final page timer, then `POST https://ez4short.com/links/go` with the exact hidden fields from step 8 and same `ez4short.com` cookie jar.
   - headers used successfully:
     - `Origin: https://ez4short.com`
     - `Referer: https://ez4short.com/qSyPzeo`
     - `X-Requested-With: XMLHttpRequest`
     - `Accept: application/json, text/javascript, */*; q=0.01`

## Exact cookie requirements

- `tech8s.net: tp=qSyPzeo` is part of the article-step path and should be preserved for canonical replay.
- `game5s.com: tp=qSyPzeo` is part of the article-step path and should be preserved for canonical replay.
- The final `/links/go` POST is same-origin to `ez4short.com`; only `ez4short.com` cookies are sent there:
  - `AppSession`
  - `csrfToken`
  - `app_visitor`
- The final POST also requires the fresh same-session hidden fields from `form#go-link`; cross-session/static `ad_form_data` should not be reused.
- Minimal shortcut proof: a fresh session `GET https://ez4short.com/qSyPzeo` with `Referer: https://game5s.com/` or `Referer: https://game5s.com/<article>/` directly returns the final `go-link` form, sets the three `ez4short.com` cookies, and the same `/links/go` replay succeeds. A `tech8s.net` referer does **not** unlock the final form.

## Final step condition

- Final page contains `<span id="timer" class="timer">3</span>`.
- Immediate `/links/go` POST returns:

```json
{"status":"error","message":"Bad Request.","url":""}
```

- After ~3 seconds from loading the final `go-link` page, `/links/go` returns the oracle URL. Safe handler wait: `3.2s` or more.

## Evidence snippets

Full replay run produced:

```text
chain: tech=https://tech8s.net/safe.php?link=qSyPzeo
tech_article=https://tech8s.net/mental-health-and-wellbeing/
game_safe=https://game5s.com/safe.php?link=qSyPzeo
game_article=https://game5s.com/nikke/
final_status=200
action=https://ez4short.com/links/go
hidden_names=["_method", "_csrfToken", "ad_form_data", "_Token[fields]", "_Token[unlocked]"]
SUBMIT 0s -> {"status":"error","message":"Bad Request.","url":""}
SUBMIT 3s -> {"status":"success","message":"Go without Earn because Adblock","url":"https://tesskibidixxx.com"}
```

Minimal shortcut run produced success for fresh sessions with any `game5s.com` referer tested:

```text
Referer: https://game5s.com/                     -> go-link form -> https://tesskibidixxx.com
Referer: https://game5s.com/nikke/               -> go-link form -> https://tesskibidixxx.com
Referer: https://game5s.com/danmachi-battle-chronicle/ -> go-link form -> https://tesskibidixxx.com
Referer: https://tech8s.net/mental-health-and-wellbeing/ -> 307 back to tech8s safe, no go-link form
```

## Commands used

```bash
.venv/bin/python tmp_ez_probe2.py | tee /tmp/ez_probe2_out.txt
.venv/bin/python tmp_ez_submit.py | tee /tmp/ez_submit_out.txt
.venv/bin/python tmp_ez_minimal.py | tee /tmp/ez_minimal_out.txt
```

Temporary scripts were local probes only and removed after writing this note.

## Handler recommendation

Implement a `ez4short.com` browserless handler using `curl_cffi` impersonation. The robust path can either:

1. canonical replay: follow `ez4short -> tech8s safe -> tech8s article POST -> game5s safe -> game5s article POST -> ez4short go-link -> /links/go`; or
2. fast path: `GET https://ez4short.com/<alias>` with `Referer: https://game5s.com/`, parse `form#go-link`, wait `>=3.2s`, POST `/links/go`.

Use option 2 as the primary fast lane if acceptable; keep option 1 as mapping/fallback evidence because it explains the real frontend chain.
