# Target Sample Catalog

Purpose: durable mapping of Boskuu-provided shortlink samples to their expected final targets. Use this before adding or debugging handlers so each family has a clear success oracle.

## Capture batch: 2026-04-24

| Shortlink | Family / host | Expected final target | Status in engine | Notes |
| --- | --- | --- | --- | --- |
| `https://oii.la/BW8ntz` | `oii.la` | `https://onlyfaucet.com/links/back/vYal1NZ2dtDFTr5cXqUi/LTC/208faecab92bd6cc094014e046df165d` | partial / analysis-only | Use as the new `oii.la` final-oracle sample. Prior oii lane can decode `links/back` targets, but final lane is not fully proven yet. |
| `https://xut.io/hd7AOJ` | `xut.io` -> likely wrapper family | `http://tesskibidixxx.com` | partial for existing xut/autodime sample | New sample target differs from previous `onlyfaucet` xut sample. First action is identify whether it still wraps into `autodime/cwsafelinkphp` or another backend. |
| `https://tpi.li/Dd5xka` | `tpi.li` | `https://99faucet.com/links/back/haBKjYrugRxDIVCpGqMo` | analysis-only supported | Shared token-tail handler now extracts the sampled faucet target. |
| `https://ez4short.com/qSyPzeo` | `ez4short.com` | `https://tesskibidixxx.com` | live bypass supported for sample | Fast `game5s.com` referer lane unlocks `form#go-link`, waits the 3s timer, then `/links/go` returns the oracle. |
| `https://cuty.io/AfaX6jx` | `cuty.io` | `https://google.com` | live bypass supported for sample | CDP Chrome helper solves Turnstile through local solver, reaches `last.js`/`/go`, and lands on Google. |
| `https://gplinks.co/YVTC` | `gplinks.co` | `http://tesskibidixxx.com` | partial mapper | PowerGam entry and JS target candidate are mapped; non-headless/Xvfb GPT probe still leaves `ad_impressions=0` and no rewarded/impression lifecycle events, so final remains unproven. |
| `https://sfl.gl/18PZXXI9` | `sfl.gl` | `https://google.com` | live bypass supported for sample | Direct VPS egress is Cloudflare-blocked, but WARP proxy fallback reaches SafelinkU API flow and extracts `window.location.href`. |
| `https://exe.io/vkRI1` | `exe.io` | `https://google.com` | partial mapper | Exeygo two-stage CakePHP gate is mapped; final remains blocked until a valid captcha token is submitted. |
| `https://lnbz.la/Hmvp6` | `lnbz.la` | `https://cryptoearns.com/links/back/AaDZLgKQsnhy423EIS9c` | live bypass supported for sample | Browserless same-session chain through `avnsgames.com` article steps and final `/links/go` returns the oracle. |
| `https://aii.sh/CBygg8fn2s3` | `aii.sh` | `https://coinadster.com/shortlink.php?short_key=1cnd9hq0nfbem5dr8vrmaz17f44pvh9a` | analysis-only supported | Final candidate discovered from ShrinkBixby hidden token. Still label as token extraction, not live Turnstile completion. |

## Immediate planning notes

- Treat the `Expected final target` column as the success oracle for each sample.
- Do not mark any new family as supported until the engine returns that exact final target or a directly equivalent downstream final URL.
- Prioritize families with known final targets first because they have a concrete oracle:
  1. `oii.la/BW8ntz`
  2. `tpi.li/Dd5xka`
  3. `xut.io/hd7AOJ`
  4. `ez4short.com/qSyPzeo`
  5. `cuty.io/AfaX6jx`
  6. `gplinks.co/YVTC`
  7. `sfl.gl/18PZXXI9`
  8. `exe.io/vkRI1`
- `aii.sh/CBygg8fn2s3` discovery is now done at token level. Next deeper work is live Turnstile/timer validation if needed.
