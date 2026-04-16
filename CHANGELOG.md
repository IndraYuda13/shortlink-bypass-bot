# Changelog

## 2026-04-16

### shrinkme.click final chain fix
- Fixed the `shrinkme.click` handler so it no longer reports the first ThemeZon article as a successful bypass.
- Added a full HTTP replay for the verified chain:
  - `shrinkme.click/<alias>`
  - `themezon.net/link.php?link=<alias>`
  - ThemeZon next-hop POST `newwpsafelink=<alias>`
  - `en.mrproblogger.com/<alias>`
  - final AJAX POST to `/links/go`
- Verified live on sample `https://shrinkme.click/ZTvkQYPJ`.
- Verified final downstream result:
  - `https://claimcoin.in/links/back/kPw2COhFxD0pfQuGrXUz`

### Files changed
- `engine.py`
  - touched `_handle_shrinkme(...)`
  - added `_resolve_shrinkme_mrproblogger(...)`
  - now waits the observed MrProBlogger timer and submits the hidden final form before claiming success
- `tests/test_shrinkme.py`
  - added regression coverage so ThemeZon intermediate URLs stay non-final
  - added success coverage for the final claimcoin result
- `README.md`
  - support table now marks `shrinkme.click` as a live bypass lane
- `ROADMAP.md`
  - synced new shrinkme milestone and current next action
- `references/shortlink-family-initial-map.md`
  - recorded the verified ThemeZon -> MrProBlogger -> `/links/go` chain

### Why this exists
- User report showed the bot was returning a wrong intermediate URL like:
  - `https://themezon.net/what-is-linux-managed-vps/`
- That URL is only an interstitial article, not the reward-site target.
- The real success oracle for this sampled lane is the JSON response from `MrProBlogger /links/go`, not the first ThemeZon page.

### Guardrail
- Do not downgrade shrinkme success back to `ThemeZon` article extraction only.
- A result is only `status=1` if the final downstream URL is actually returned from the last `MrProBlogger /links/go` step.

### speed optimization pass
- Added a browserless `link.adlink.click` fast lane using `curl_cffi` TLS impersonation against `blog.adlink.click`.
- Kept `adlink_live_browser.py` only as fallback when the faster browserless lane fails.
- Added a direct `shrinkme.click` shortcut that starts from `https://en.mrproblogger.com/<alias>` with `Referer: https://themezon.net/` instead of replaying every ThemeZon hop first.
- Tightened the final wait windows based on live lower-bound probing:
  - `link.adlink.click` sample `CBr27fn4of3` now succeeds around `4.0s` after the blog page load
  - `shrinkme.click` sample `ZTvkQYPJ` now succeeds around `11.2s` to `11.6s` after the MrProBlogger page load

### Files changed
- `engine.py`
  - added `_resolve_adlink_http(...)`
  - added `_resolve_shrinkme_direct_mrproblogger(...)`
  - now prefers the faster browserless Adlink lane before falling back to Chromium
  - now prefers the direct MrProBlogger shortcut for shrinkme before the longer ThemeZon replay path
- `adlink_live_browser.py`
  - added faster direct blog-form submission so the fallback browser lane wastes less time
- `requirements.txt`
  - added `curl_cffi`
- `tests/test_adlink.py`
  - added regression coverage for Adlink fast-lane selection and browser fallback
- `tests/test_shrinkme.py`
  - added regression coverage for the direct MrProBlogger shortcut
- `README.md`, `ROADMAP.md`, `docs/FLOWS.md`, `references/shortlink-family-initial-map.md`
  - synced the new fast lanes, timer boundaries, and fallback rules

### Why this exists
- The earlier engine still spent too much time on avoidable hops:
  - Adlink kept launching a full browser even when a browserless TLS-impersonated blog hit was enough
  - ShrinkMe still replayed longer ThemeZon steps even though the real bottleneck lived at MrProBlogger
- The new code cuts that waste while keeping the same success oracle discipline.

### Guardrail
- Do not regress Adlink back to browser-only as the default unless TLS impersonation stops working on live samples.
- Do not assume `ad_form_data` can be replayed across sessions for ShrinkMe. The speed win comes from same-session early fetch plus tighter wait windows, not from cross-session blob reuse.
