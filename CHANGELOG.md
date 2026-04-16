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
