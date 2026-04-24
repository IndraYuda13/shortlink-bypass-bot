# Target Sample Catalog

Purpose: durable mapping of Boskuu-provided shortlink samples to their expected final targets. Use this before adding or debugging handlers so each family has a clear success oracle.

## Capture batch: 2026-04-24

| Shortlink | Family / host | Expected final target | Status in engine | Notes |
| --- | --- | --- | --- | --- |
| `https://oii.la/BW8ntz` | `oii.la` | `https://onlyfaucet.com/links/back/vYal1NZ2dtDFTr5cXqUi/LTC/208faecab92bd6cc094014e046df165d` | partial / analysis-only | Use as the new `oii.la` final-oracle sample. Prior oii lane can decode `links/back` targets, but final lane is not fully proven yet. |
| `https://xut.io/hd7AOJ` | `xut.io` -> likely wrapper family | `http://tesskibidixxx.com` | partial for existing xut/autodime sample | New sample target differs from previous `onlyfaucet` xut sample. First action is identify whether it still wraps into `autodime/cwsafelinkphp` or another backend. |
| `https://tpi.li/Dd5xka` | `tpi.li` | `https://99faucet.com/links/back/haBKjYrugRxDIVCpGqMo` | unsupported | New family to map. Expected output is a faucet `links/back` URL. |
| `https://ez4short.com/qSyPzeo` | `ez4short.com` | `https://tesskibidixxx.com` | unsupported | New family to map. |
| `https://cuty.io/AfaX6jx` | `cuty.io` | `https://google.com` | unsupported | New family to map. |
| `https://gplinks.co/YVTC` | `gplinks.co` | `http://tesskibidixxx.com` | unsupported | New family to map. |
| `https://sfl.gl/18PZXXI9` | `sfl.gl` | `https://google.com` | unsupported | New family to map. |
| `https://exe.io/vkRI1` | `exe.io` | `https://google.com` | unsupported | New family to map. |
| `https://aii.sh/CBygg8fn2s3` | `aii.sh` | unknown, target akhir not supplied yet | unsupported | Boskuu marked this as `target akhir`. Need run mapping to discover or verify final target. |

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
- `aii.sh/CBygg8fn2s3` needs discovery first because the final target is not yet known.
