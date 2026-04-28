# Supported Sites Registry

This document mirrors `supported_sites.py`, which is the canonical machine-readable registry for bot commands and future API integration.

## Status meanings

- `live_bypass`: current lane is considered working for the captured sample and returns the downstream final URL.
- `token_bypass`: handler returns the downstream target from a decoded token or embedded payload, but full live gate execution is not proven.
- `analysis_only`: handler maps useful facts but does not return a final target.
- `partial`: handler or mapped flow exists, but a current blocker prevents final success.
- `unsupported`: sample/oracle is known, but no handler exists yet.

## Current registry

| Host | Status | Command alias | Handler | Sample | Expected final | Current blocker / proof |
| --- | --- | --- | --- | --- | --- | --- |
| `link.adlink.click` | `live_bypass` | `adlink` | `_handle_adlink_click` | `https://link.adlink.click/SfRi` | `https://earn-pepe.com/member/shortlinks/verify/ca7c179027eb04abfb79` | Live recheck on 2026-04-28 returned the final URL. |
| `shrinkme.click` | `live_bypass` | `shrinkme` | `_handle_shrinkme` | `https://shrinkme.click/ZTvkQYPJ` | `https://claimcoin.in/links/back/kPw2COhFxD0pfQuGrXUz` | Live recheck on 2026-04-28 returned the final URL. |
| `ez4short.com` | `live_bypass` | `ez4short` | `_handle_ez4short` | `https://ez4short.com/qSyPzeo` | `https://tesskibidixxx.com` | User live bot run returned the expected final URL. |
| `lnbz.la` | `live_bypass` | `lnbz` | `_handle_lnbz` | `https://lnbz.la/Hmvp6` | `https://cryptoearns.com/links/back/AaDZLgKQsnhy423EIS9c` | Prior live run returned the expected final URL. |
| `oii.la` | `token_bypass` | `oii` | `_handle_token_landing` | `https://oii.la/BW8ntz` | `https://onlyfaucet.com/links/back/vYal1NZ2dtDFTr5cXqUi/LTC/208faecab92bd6cc094014e046df165d` | Token extraction works, full Turnstile/timer lane not proven. |
| `tpi.li` | `token_bypass` | `tpi` | `_handle_token_landing` | `https://tpi.li/Dd5xka` | `https://99faucet.com/links/back/haBKjYrugRxDIVCpGqMo` | Token extraction works, full Turnstile/timer lane not proven. |
| `aii.sh` | `token_bypass` | `aii` | `_handle_token_landing` | `https://aii.sh/CBygg8fn2s3` | `https://coinadster.com/shortlink.php?short_key=1cnd9h...h9a` | Token extraction only. Fresh full oracle should be captured before marking live. |
| `xut.io` | `live_bypass` | `xut` | `_handle_autodime_cwsafelink` | `https://xut.io/hd7AOJ` | `http://tesskibidixxx.com` | Live helper returned final after IconCaptcha Step 1, gamescrate Step 5, xut Step 6, and exact `Get Link` click. |
| `cuty.io` | `live_bypass` | `cuty` | `_handle_cuty` | `https://cuty.io/AfaX6jx` | `https://google.com` | HTTP fast helper now returns `https://www.google.com/` via Cuttlinks form replay + local Turnstile solver; VHit replay is opt-in and CDP browser remains fallback. |
| `gplinks.co` | `live_bypass` | `gplinks` | `_handle_gplinks` | `https://gplinks.co/YVTC` | `http://tesskibidixxx.com` | Live engine recheck on 2026-04-28 returned the final URL through the PowerGam browser lane and final Turnstile callback. |
| `sfl.gl` | `live_bypass` | `sfl` | `_handle_sfl` | `https://sfl.gl/18PZXXI9` | `https://google.com` | WARP proxy fallback reaches SafelinkU API flow and returns the expected final target. |
| `exe.io` | `live_bypass` | `exe` | `_handle_exe` | `https://exe.io/vkRI1` | `https://google.com` | Live engine recheck on 2026-04-28 returned the final URL after Turnstile solve and go-link submit. |

## Supported timing display

`/supported` and `/status` render the canonical speed-ranked list from `supported_sites.status_lines()`:

1. `aii.sh` `±0.9s`
2. `oii.la / tpi.li` `±1.8s`
3. `ez4short.com` `±3.9s`
4. `link.adlink.click` `±5.5s`
5. `sfl.gl` `±13.1s`
6. `shrinkme.click` `±13.3s`
7. `lnbz.la` `±19.7s`
8. `exe.io` `±69s`
9. `cuty.io` `±72s`
10. `xut.io` `±97-109s`
11. `gplinks.co` `±149-150s`

Each individual registry entry also exposes `method_summary`, `solve_time_label`, `solve_time_seconds_min`, and `solve_time_seconds_max` for API consumers. The grouped display list is exposed through `supported_sites.display_groups_as_dicts()`.

## Integration rule

Use `supported_sites.registry_as_dicts()` for per-host API-style JSON. Use `supported_sites.display_groups_as_dicts()` for the grouped speed-ranked API view. Use `supported_sites.status_lines()` for bot/status text. Avoid adding new hardcoded supported-site lists in `bot.py`, `README.md`, or future API handlers.
