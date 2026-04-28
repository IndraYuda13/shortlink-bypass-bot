# 2026-04-28 GPLinks HTTP ledger subagent report

## Scope

Target: `https://gplinks.co/YVTC`

Read:

- `gplinks_http_fast.py`
- `gplinks_live_browser.py`
- `artifacts/active/2026-04-28-gplinks-final-push-workframe.md`
- `artifacts/active/2026-04-28-gplinks-final-contract-investigation.md`
- `artifacts/active/2026-04-28-gplinks-gpt-continuation.md`
- `artifacts/active/2026-04-28-gplinks-final-js-analysis.md`
- `references/probes/2026-04-24-gplinks-tracki-analysis.md`
- `references/probes/2026-04-24-gplinks-gpt-browser.md`
- `artifacts/active/http-optimization/power-cdn-2.0.0.5.pretty.js`

Scratch probe created only under artifacts:

- `artifacts/active/gplinks_http_ledger_probe.py`
- raw outputs:
  - `/tmp/gplinks_http_ledger_probe.json`
  - `/tmp/gplinks_http_ledger_rawvid.json`

No production file was modified.

## PowerGam boundary facts

`power-cdn.js` does **not** decode `vid` before storing/submitting it.

Relevant deobfuscated behavior:

```js
visitor_id = getQueryParam('vid')              // raw encoded value, e.g. MTAx...
Cookies.set('vid', visitor_id)
cookie_visitor_id = Cookies.get('vid')

$('#adsForm').on('submit', function(e) {
  e.preventDefault()
  step_id = cookie_step_count + 1
  ad_impressions = Number(Cookies.get('imps'))
  this.step_id.value = step_id
  this.ad_impressions.value = ad_impressions
  this.visitor_id.value = cookie_visitor_id    // raw encoded value
  this.next_target.value = next_target
  this.submit()
})
```

So the exact browser form payload uses:

```text
visitor_id=MTAx...   # encoded visitor id from query
```

not:

```text
visitor_id=1019...   # decoded numeric visitor id
```

This matters because the current `gplinks_http_fast.py` uses `decoded.get('vid')` for the PowerGam cookie and form `visitor_id`, which is not exact browser behavior.

## Experiments run

### Command 1, multi-variant HTTP replay

```bash
cd /root/.openclaw/workspace/projects/shortlink-bypass-bot
.venv/bin/python artifacts/active/gplinks_http_ledger_probe.py > /tmp/gplinks_http_ledger_probe.json
```

Variants:

1. `baseline_imps5`
2. `zero_imps_exact_js`
3. `tracki_then_imps5`
4. `conversion_then_imps5`
5. `xrw_imps5`

Common result:

```text
GET https://gplinks.co/YVTC
-> 302 Location: https://powergam.online?lid=WVZUQw&pid=MTIyNDYyMg&vid=<vid>&pages=Mw

GET PowerGam URL
-> 200 form#adsForm

POST 3 PowerGam steps
GET https://gplinks.co/YVTC?pid=1224622&vid=<vid>
-> 302 https://gplinks.co/link-error?alias=YVTC&error_code=not_enough_steps
```

Important variant outputs:

#### `baseline_imps5`

```text
entry: 302 -> https://powergam.online?lid=WVZUQw&pid=MTIyNDYyMg&vid=MTAxOTM5NDQyMQ&pages=Mw
power: 200 form#adsForm action=https://powergam.online/?lid=WVZUQw&pid=MTIyNDYyMg&vid=MTAxOTM5NDQyMQ&pages=Mw
post step 1: status=200 payload visitor_id=1019394421 ad_impressions=5 next_target=https://powergam.online
post step 2: status=200 payload visitor_id=1019394421 ad_impressions=5 next_target=https://powergam.online
post step 3: status=200 payload visitor_id=1019394421 ad_impressions=5 next_target=https://gplinks.co/YVTC?pid=1224622&vid=MTAxOTM5NDQyMQ
candidate: 302 -> https://gplinks.co/link-error?alias=YVTC&error_code=not_enough_steps
```

This used decoded numeric `visitor_id`, matching current `gplinks_http_fast.py`, but not the browser JS.

#### `tracki_then_imps5`

```text
tracki-get-banner 336x280: 200 {"ok":true,"banners":[...]}
tracki-imp cid=14: 200 image/gif, no Set-Cookie
tracki-imp cid=16: 200 image/gif, no Set-Cookie
tracki-imp cid=8: 200 image/gif, no Set-Cookie
tracki-imp cid=10: 200 image/gif, no Set-Cookie
tracki-imp cid=9: 200 image/gif, no Set-Cookie
tracki-get-banner 300x250: 200 {"ok":true,"banner":null,"exhausted":true}
candidate: 302 -> https://gplinks.co/link-error?alias=YVTC&error_code=not_enough_steps
```

Tracki banner impressions still do not update the GPLinks enough-steps ledger.

#### `conversion_then_imps5`

All tested conversion helper calls returned 500 and did not help:

```text
GET  https://gplinks.com/track/data.php?request=addConversion&pid=MTIyNDYyMg&vid=MTAxOTM5NDQ2MQ&o_id=3&o_type=2 -> 500
POST https://gplinks.com/track/data.php request=addConversion pid=MTIyNDYyMg vid=MTAxOTM5NDQ2MQ o_id=3 o_type=2 -> 500
GET/POST with o_id=4,o_type=3 -> 500
GET/POST with decoded vid=1019394461 -> 500
candidate: 302 -> https://gplinks.co/link-error?alias=YVTC&error_code=not_enough_steps
```

Note: this variant used encoded `pid` in the scratch call. Prior saved notes already tested decoded `pid=1224622` and also got 500, so `data.php` remains falsified as the standalone missing proof.

### Command 2, raw `vid` exact-browser replay

Because `power-cdn.js` uses raw encoded `vid`, I ran a second bounded curl_cffi replay with:

- `Cookies.vid = raw query vid`
- `visitor_id = raw query vid`
- candidate URL keeps raw `vid`

Command:

```bash
cd /root/.openclaw/workspace/projects/shortlink-bypass-bot
.venv/bin/python - <<'PY'
# imported artifacts/active/gplinks_http_ledger_probe.py and overrode only vid handling
# output written to /tmp/gplinks_http_ledger_rawvid.json
PY
```

Output:

```text
entry 302 https://powergam.online?lid=WVZUQw&pid=MTIyNDYyMg&vid=MTAxOTM5NTAxNw&pages=Mw
raw:     lid=WVZUQw pid=MTIyNDYyMg vid=MTAxOTM5NTAxNw pages=Mw
decoded: lid=YVTC  pid=1224622  vid=1019395017 pages=3

power 200 https://powergam.online/?lid=WVZUQw&pid=MTIyNDYyMg&vid=MTAxOTM5NTAxNw&pages=Mw
form#adsForm action=https://powergam.online/?lid=WVZUQw&pid=MTIyNDYyMg&vid=MTAxOTM5NTAxNw&pages=Mw

post-step 1:
  status=302
  Location=https://powergam.online
  payload={form_name: ads-track-data, step_id: 1, ad_impressions: 5, visitor_id: MTAxOTM5NTAxNw, next_target: https://powergam.online}
follow-step 1:
  status=200 url=https://powergam.online/

post-step 2:
  status=302
  Location=https://powergam.online
  payload={form_name: ads-track-data, step_id: 2, ad_impressions: 5, visitor_id: MTAxOTM5NTAxNw, next_target: https://powergam.online}
follow-step 2:
  status=200 url=https://powergam.online/

post-step 3:
  status=302
  Location=https://gplinks.co/YVTC?pid=1224622&vid=MTAxOTM5NTAxNw
  payload={form_name: ads-track-data, step_id: 3, ad_impressions: 5, visitor_id: MTAxOTM5NTAxNw, next_target: https://gplinks.co/YVTC?pid=1224622&vid=MTAxOTM5NTAxNw}
follow-step 3:
  status=200 url=https://gplinks.com/link-error?alias=YVTC&error_code=not_enough_steps

candidate direct:
  status=302
  Location=https://gplinks.co/link-error?alias=YVTC&error_code=not_enough_steps
```

This is the most exact pure HTTP PowerGam form replay I could produce with curl_cffi. It reproduces browser-like PowerGam redirects but still fails the GPLinks server ledger.

## Feasibility conclusion

Full HTTP is **not proven feasible** for this target from the current evidence.

What is proven:

- Exact raw-`vid` PowerGam HTTP replay can make PowerGam return the expected step redirects.
- The server still rejects the final candidate with `error_code=not_enough_steps`.
- Tracki banner impressions are not sufficient.
- Tracki pop/config/serve/track was already falsified in saved notes.
- `gplinks.com/track/data.php request=addConversion` is not sufficient and returns 500 in this context.
- Local cookies and visible form fields are not the whole contract.

Most likely missing proof:

- A server-side ad/GPT ledger event tied to the visitor, not just the visible `adsForm` fields.
- The strongest candidate remains Google Publisher Tag lifecycle proof, especially `impressionViewable` and/or the final-step rewarded out-of-page lifecycle:
  - `rewardedSlotReady`
  - `makeRewardedVisible()`
  - `rewardedSlotClosed` / `rewardedSlotGranted` / `rewardedSlotVideoCompleted`

Saved browser traces show Google/Tracki resources load, but the VPS browser does not emit those GPT lifecycle events. Forced local `imps/adexp` does not satisfy the server.

## Smallest concrete patch proposal

### Patch goal

Do **not** promote GPLinks full HTTP as solved. Fix the HTTP probe so it matches browser payloads, then keep it as diagnostic/preflight only unless it actually reaches a downstream final URL.

### Minimal code change in `gplinks_http_fast.py`

Use decoded values for `lid`, `pid`, `pages`, but raw encoded query value for PowerGam `vid` cookie and `visitor_id` form field.

Suggested snippet:

```python
raw = raw_power_query(power_url)
decoded = decoded_power_query(power_url)

lid = decoded.get("lid") or ""
pid = decoded.get("pid") or ""
raw_vid = raw.get("vid") or ""

# final candidate already expects raw vid
target_final_candidate = (
    f"https://gplinks.co/{lid}?pid={pid}&vid={raw_vid}"
    if lid and pid and raw_vid else None
)

visitor_id = raw_vid
```

Change cookie setter to accept raw `vid`:

```python
def _set_powergam_cookies(session, decoded, raw, host_url, step_count=0, imps=5):
    host = urlparse(host_url).hostname or "powergam.online"
    cookie_values = {
        "lid": decoded.get("lid") or "",
        "pid": decoded.get("pid") or "",
        "pages": decoded.get("pages") or "",
        "vid": raw.get("vid") or "",          # raw encoded vid
        "step_count": str(step_count),
        "imps": str(imps),
        "adexp": "1",
    }
```

And build step payloads with raw `visitor_id`:

```python
payload = {
    "form_name": "ads-track-data",
    "step_id": str(step),
    "ad_impressions": str(imps),
    "visitor_id": raw_vid,                  # raw encoded vid
    "next_target": target_final if step >= pages else fallback_target,
}
```

### Guardrail

Even after this patch, success must remain gated by the final oracle:

```python
if "error_code=not_enough_steps" in final_location:
    return {
        "status": 0,
        "stage": "powergam-ledger",
        "message": "HTTP_FAST_POWERGAM_LEDGER_REJECTED",
        ...
    }
```

### Browser fallback

Keep `gplinks_live_browser.py` as the only possible success lane right now. The browser lane should return `status=1` only when it observes a non-GPlinks/non-PowerGam downstream URL, e.g. `http://tesskibidixxx.com/`, or captures `/links/go` returning that URL.

## Clear blocker

The remaining blocker is not in the visible PowerGam form contract. It is the hidden server-side enough-steps ledger. Current curl_cffi cannot produce the missing ad/GPT proof. A successful next step would require a browser trace from an environment where GPT rewarded/viewable events actually fire, then comparing server requests around that event against the failing raw HTTP replay.
