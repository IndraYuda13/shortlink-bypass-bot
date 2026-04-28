# Token family optimization report

Scope: `oii.la`, `tpi.li`, `aii.sh` only. No production code edited.

## Workframe

- Objective: decide whether the token families can be upgraded from `token_bypass` to `live_bypass`, whether the existing token extraction is already the fastest final-skip lane, and whether any gate is unnecessary.
- Success oracle for `live_bypass`: a live flow proves the downstream final URL after the active timer/captcha/form boundary, not only a decoded payload.
- Evidence files created:
  - `artifacts/active/total-optimization/token_probe.py`
  - `artifacts/active/total-optimization/token_probe_results.jsonl`
  - `artifacts/active/total-optimization/token_gate_probe.py`
  - `artifacts/active/total-optimization/token_gate_probe_results.jsonl`
  - `artifacts/active/total-optimization/token_target_curl_probe.py`
  - `artifacts/active/total-optimization/token_target_curl_probe_results.jsonl`

## Current implementation read

- `supported_sites.py` marks all three as `token_bypass`.
- `engine.py` routes `oii.la`, `tpi.li`, and `aii.sh` into `_handle_token_landing()`.
- `_handle_token_landing()`:
  1. fetches the entry page,
  2. parses the first form and hidden fields,
  3. extracts the base64 URL tail from hidden `token` via `_extract_oii_token_target()`,
  4. returns `status=1`, `message=TOKEN_TARGET_EXTRACTED`, `stage=token-target`.
- Existing unit coverage confirms `tpi.li` and `aii.sh` token extraction. Verification command used because pytest is not installed:
  - `.venv/bin/python -m unittest tests.test_token_landing tests.test_supported_sites_registry`
  - result: `Ran 7 tests in 0.006s OK`.

## Live sample timings

Measured with `ShortlinkBypassEngine(timeout=30).analyze()` on the registry samples.

| Host | Sample | Current result | Extracted URL | Time |
| --- | --- | --- | --- | --- |
| `oii.la` | `https://oii.la/BW8ntz` | `status=1`, `TOKEN_TARGET_EXTRACTED` | `https://onlyfaucet.com/links/back/vYal1NZ2dtDFTr5cXqUi/LTC/208faecab92bd6cc094014e046df165d` | `1.985s` in token probe, `1.909s` in gate probe |
| `tpi.li` | `https://tpi.li/Dd5xka` | `status=1`, `TOKEN_TARGET_EXTRACTED` | `https://99faucet.com/links/back/haBKjYrugRxDIVCpGqMo` | `2.000s` in token probe, `1.457s` in gate probe |
| `aii.sh` | `https://aii.sh/CBygg8fn2s3` | `status=1`, `TOKEN_TARGET_EXTRACTED` | `https://coinadster.com/shortlink.php?short_key=1cnd9hq0nfbem5dr8vrmaz17f44pvh9a` | `0.963s` in token probe, `1.052s` in gate probe |

All three still expose active Turnstile config and a 15 second counter on the entry page:

| Host | Captcha | Counter | Sitekey |
| --- | --- | --- | --- |
| `oii.la` | `turnstile` | `15` | `0x4AAAAAABatM0GOBpAxBoeD` |
| `tpi.li` | `turnstile` | `15` | `0x4AAAAAABpMIvjgfpDTfgEj` |
| `aii.sh` | `turnstile` | `15` | `0x4AAAAAABde2R5F8ZlSAQ3R` |

## Gate tests

### Form submit without captcha

I replayed each parsed hidden form without any Turnstile response.

| Host | Form action | Result | Time | Meaning |
| --- | --- | --- | --- | --- |
| `oii.la` | `https://advertisingcamps.com/taboola2/landing/` | `302 -> https://www.taboola.com` | `0.848s` | This is an ad handoff, not the downstream final oracle. |
| `tpi.li` | `https://advertisingcamps.com/taboola1/landing/` | `302 -> https://www.taboola.com` | `0.268s` | Same as `oii.la`: not a useful final gate. |
| `aii.sh` | rotating `https://techbixby.com/.../` article | `200`, no redirect | `2.600s` | Article handoff accepted the POST but did not prove final target. |

Conclusion: no-captcha form replay does **not** upgrade the family to live bypass. For `oii.la` and `tpi.li`, the active form is only an ad landing boundary. For `aii.sh`, article handoff needs more mapping before any live claim.

### Direct extracted target probe

I probed the extracted targets without following redirects.

| Host | Target probe result | Meaning |
| --- | --- | --- |
| `oii.la` | plain `requests`: `403 Just a moment`; `curl_cffi`: `403`, `server=cloudflare`, `cf-mitigated=challenge` | Downstream target exists as a URL, but live downstream access is Cloudflare-blocked from this VPS lane. |
| `tpi.li` | plain `requests`: `403 Attention Required`; `curl_cffi`: `403`, `server=cloudflare` | Same. Target extraction is valid, but downstream live proof is blocked. |
| `aii.sh` | plain `requests`: `403 Just a moment`; `curl_cffi`: `302 -> https://coinadster.com/shortlink.html` | Extracted URL reaches Coinadster infrastructure, but this is not a final success proof for a reward/claim flow. |

## Can `token_bypass` be upgraded to `live_bypass`?

Recommendation: **No, not yet. Keep all three as `token_bypass`.**

Reason:
- The engine already returns the correct downstream candidate quickly from the entry payload.
- The active Turnstile/timer boundary is still present on all three entry pages.
- No measured live flow proved that solving or skipping that boundary causes a downstream final success state.
- The no-captcha form replay either goes to Taboola (`oii.la`, `tpi.li`) or only reaches an article page (`aii.sh`).
- Direct target probes hit downstream Cloudflare or a generic Coinadster redirect, not a reliable success oracle.

Marking these as `live_bypass` would overclaim the evidence. The current registry wording is accurate.

## Is there a faster final skip?

Recommendation: **The current token extraction is already the fastest proven final-skip lane.**

Evidence:
- Current extraction completes in roughly `1.0-2.0s`.
- The visible live gate has a `15s` timer before any captcha/form completion work.
- Any true live lane would also need Turnstile handling and probably downstream Cloudflare handling.
- The extracted token directly contains the target candidate, so solving the gate is unnecessary if the product goal is only to return the URL to the user.

Estimated saved time versus a full gate path: at least `15s` plus captcha solver latency. On the measured samples, token extraction is roughly `8x-15x` faster than just waiting the timer, before counting captcha and downstream checks.

## Is any gate unnecessary?

Depends on the success definition:

- For bot output URL extraction: **yes**. The Turnstile/timer/ad gate is unnecessary because the downstream candidate is embedded in hidden `token` before the gate.
- For a strict `live_bypass` proof: **no**. The gate cannot be declared unnecessary because no downstream success effect was proven after bypassing it.
- For `oii.la` and `tpi.li`: the `advertisingcamps.com/taboola*` POST should not be used as a success gate. It consistently behaves as an ad handoff.
- For `aii.sh`: the TechBixby article POST may be part of the intended ad flow, but it is slower than token extraction and did not produce a final oracle in this probe.

## Exact implementation recommendation

Do not edit production code for this lane right now except optional docs/wording later.

Recommended behavior:
1. Keep `oii.la`, `tpi.li`, and `aii.sh` at `status="token_bypass"` in `supported_sites.py`.
2. Keep `_handle_token_landing()` as the primary path.
3. Do **not** add live Turnstile solving for these families unless a future requirement needs downstream success verification instead of URL return.
4. If optimizing user-facing speed, make sure the bot does not try any form replay or downstream fetch after token extraction. Return immediately once `TOKEN_TARGET_EXTRACTED` is found.
5. Optional small cleanup later: rename `_extract_oii_token_target()` to a generic name like `_extract_token_tail_target()` because it now serves `oii.la`, `tpi.li`, and `aii.sh`. This is code clarity only, not performance-critical.
6. Optional docs update later: explicitly state that token families intentionally skip the visible 15s Turnstile/ad gate because the final candidate is embedded in the entry payload, but they remain `token_bypass` until a live downstream success oracle is proven.

## Blockers for future live upgrade

- Need a reliable success oracle for downstream hosts:
  - `onlyfaucet.com/links/back/...`
  - `99faucet.com/links/back/...`
  - `coinadster.com/shortlink.php?...`
- Need a lane through downstream Cloudflare for OnlyFaucet/99Faucet if strict live validation is required.
- Need full TechBixby/ShrinkBixby article flow mapping for `aii.sh` if live gate completion becomes necessary.
- Need to distinguish URL extraction success from reward/claim success. Current evidence proves the former, not the latter.
