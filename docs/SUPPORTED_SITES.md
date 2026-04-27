# Supported Sites Registry

This document mirrors `supported_sites.py`, which is the canonical machine-readable registry for bot commands and future API integration.

## Status meanings

- `live_bypass`: current lane is considered working for the captured sample and returns the downstream final URL.
- `analysis_only`: handler can extract a final candidate from static/token data, but the full live gate flow is not proven.
- `partial`: handler or mapped flow exists, but a current blocker prevents final success.
- `unsupported`: sample/oracle is known, but no handler exists yet.

## Current registry

| Host | Status | Command alias | Handler | Sample | Expected final | Current blocker / proof |
| --- | --- | --- | --- | --- | --- | --- |
| `link.adlink.click` | `live_bypass` | `adlink` | `_handle_adlink_click` | `https://link.adlink.click/SfRi` | `https://earn-pepe.com/member/shortlinks/verify/ca7c179027eb04abfb79` | Live recheck on 2026-04-28 returned the final URL. |
| `shrinkme.click` | `live_bypass` | `shrinkme` | `_handle_shrinkme` | `https://shrinkme.click/ZTvkQYPJ` | `https://claimcoin.in/links/back/kPw2COhFxD0pfQuGrXUz` | Live recheck on 2026-04-28 returned the final URL. |
| `ez4short.com` | `live_bypass` | `ez4short` | `_handle_ez4short` | `https://ez4short.com/qSyPzeo` | `https://tesskibidixxx.com` | User live bot run returned the expected final URL. |
| `lnbz.la` | `live_bypass` | `lnbz` | `_handle_lnbz` | `https://lnbz.la/Hmvp6` | `https://cryptoearns.com/links/back/AaDZLgKQsnhy423EIS9c` | Prior live run returned the expected final URL. |
| `oii.la` | `analysis_only` | `oii` | `_handle_token_landing` | `https://oii.la/BW8ntz` | `https://onlyfaucet.com/links/back/vYal1NZ2dtDFTr5cXqUi/LTC/208faecab92bd6cc094014e046df165d` | Token extraction works, full Turnstile/timer lane not proven. |
| `tpi.li` | `analysis_only` | `tpi` | `_handle_token_landing` | `https://tpi.li/Dd5xka` | `https://99faucet.com/links/back/haBKjYrugRxDIVCpGqMo` | Token extraction works, full Turnstile/timer lane not proven. |
| `aii.sh` | `analysis_only` | `aii` | `_handle_token_landing` | `https://aii.sh/CBygg8fn2s3` | `https://coinadster.com/shortlink.php?short_key=1cnd9h...h9a` | Token extraction only. Fresh full oracle should be captured before marking live. |
| `xut.io` | `partial` | `xut` | `_handle_autodime_cwsafelink` | `https://xut.io/hd7AOJ` | `http://tesskibidixxx.com` | Current bot run fails because `xut_live_browser.py` cannot import `dtos`; later gates are still not closed. |
| `cuty.io` | `partial` | `cuty` | `_handle_cuty` | `https://cuty.io/AfaX6jx` | `https://google.com` | Current bot run can fail with `ERROR_CAPTCHA_UNSOLVABLE`. |
| `gplinks.co` | `partial` | `gplinks` | `_handle_gplinks` | `https://gplinks.co/YVTC` | `http://tesskibidixxx.com` | PowerGam flow mapped, but final still fails `not_enough_steps`. |
| `sfl.gl` | `partial` | `sfl` | `_handle_sfl` | `https://sfl.gl/18PZXXI9` | `https://google.com` | Current bot run fails because the expected entry form is missing. |
| `exe.io` | `unsupported` | `exe` | none | `https://exe.io/vkRI1` | `https://google.com` | No handler yet. |

## Integration rule

Use `supported_sites.registry_as_dicts()` for API-style JSON. Use `supported_sites.status_lines()` for bot/status text. Avoid adding new hardcoded supported-site lists in `bot.py`, `README.md`, or future API handlers.
