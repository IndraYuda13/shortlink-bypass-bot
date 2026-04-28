# Shortlink Bypass Bot Roadmap

## Scope
- Target awal:
  - `link.adlink.click`
  - `shrinkme.click`
  - `oii.la`
  - `xut.io`
- New sample batch captured on 2026-04-24:
  - `oii.la/BW8ntz` -> `onlyfaucet.com/links/back/.../LTC/...`
  - `xut.io/hd7AOJ` -> `tesskibidixxx.com`
  - `tpi.li/Dd5xka` -> `99faucet.com/links/back/...` (token handler now supported)
  - `ez4short.com/qSyPzeo` -> `tesskibidixxx.com` (fast live handler now supported)
  - `cuty.io/AfaX6jx` -> `google.com` (handler exists, but current live run is blocked by solver instability)
  - `gplinks.co/YVTC` -> `tesskibidixxx.com`
  - `sfl.gl/18PZXXI9` -> `google.com` (live via WARP proxy fallback + SafelinkU API flow)
  - `exe.io/vkRI1` -> `google.com`
  - `aii.sh/CBygg8fn2s3` -> `coinadster.com/shortlink.php?...` (token handler now supported)
  - `lnbz.la/Hmvp6` -> `cryptoearns.com/links/back/...` (browserless article-chain handler now supported)
- Durable sample catalog:
  - `references/target-sample-catalog.md`
- Contoh downstream yang sudah terlihat dari sampel:
  - `coinadster.com`
  - `99faucet.com`
  - `earn-pepe.com`

## Top-level checklist
- [in progress] 1. Petakan flow teknis per shortlink family
- [done] 2. Audit komponen solver/browser/flaresolverr yang sudah ada di workspace
- [in progress] 3. Tentukan boundary utama dan success oracle per family
- [done] 4. Rancang arsitektur bot bypass yang modular
- [done] 5. Buat POC runner untuk minimal 1 family yang bisa direplay
- [done] 6. Verifikasi POC pada sampel link nyata tanpa spam
- [done] 7. Dokumentasikan lesson reusable dan next patch list
- [done] 8. Deploy bot Telegram persist di Rawon

## Current known facts
- User menemukan bot pihak ketiga yang bisa mengembalikan URL verifikasi akhir dari beberapa shortlink.
- Failure contoh yang perlu dijelaskan/reproduce:
  - `TIMEOUT`
  - `ERROR_CAPTCHA_UNSOLVABLE`
- Workspace sudah punya aset solver/captcha terkait.
- Reusable base terkuat saat ini:
  - `projects/hcaptcha-challenger-codex`
  - `state/flaresolverr-exp/src`
  - `tmp-gh/turnstile-solver-api`
- `shrinkme.click` sample `kVJMw` sudah narrowed:
  - captcha aktif = reCAPTCHA
  - sitekey = `6LfFeLErAAAAAHYOQfqM3-7BpopXCbBQPAMEeh4B`
  - counter = `12`
  - continue clue = `https://themezon.net/link.php?link=kVJMw`
- `shrinkme.click` sample `ZTvkQYPJ` sekarang sudah punya lane final yang terverifikasi:
  - continue hint = `https://themezon.net/link.php?link=ZTvkQYPJ`
  - `ThemeZon` hop bisa direplay dengan referer shrinkme yang benar lalu di-advance lewat POST `newwpsafelink=<alias>` ke `https://themezon.net/?redirect_to=random`
  - next hop final yang valid = `https://en.mrproblogger.com/ZTvkQYPJ`
  - page `mrproblogger` memuat hidden form `action=/links/go` + `ad_form_data`
  - setelah timer `12s` lewat, POST AJAX ke `/links/go` mengembalikan final URL:
    - `https://claimcoin.in/links/back/kPw2COhFxD0pfQuGrXUz`
  - shortcut yang lebih cepat sekarang juga terbukti untuk sampel ini:
    1. langsung `GET https://en.mrproblogger.com/ZTvkQYPJ`
    2. pakai `Referer: https://themezon.net/`
    3. parse form `#go-link`
    4. submit final sekitar `11.2s` sampai `11.6s` setelah page load
  - artinya lower bound praktis sekarang bukan lagi `12-13s` full chain, tapi sekitar `11.4s+` dari page MrProBlogger, dengan margin aman implementasi `11.6s`
- `oii.la` sample set sekarang sudah cukup kuat secara static/lane evidence:
  - `TaVOKJleNN` token tail decode = `https://99faucet.com/links/back/SNcKa7f52qRk4xiA1gl6`
  - `FOT3p2HAVb` token tail decode = `https://claimcrypto.cc/links/back/wvCF7sRItpKGM2XrhoOj`
  - New Boskuu-provided oracle sample:
    - `BW8ntz` expected final = `https://onlyfaucet.com/links/back/vYal1NZ2dtDFTr5cXqUi/LTC/208faecab92bd6cc094014e046df165d`
  - captcha aktif tetap = Turnstile
  - sitekey = `0x4AAAAAABatM0GOBpAxBoeD`
  - counter = `15`
  - form action live yang teramati = `https://advertisingcamps.com/taboola2/landing/`
  - untuk dua sampel yang dites, POST ke endpoint itu tanpa token captcha pun tetap `302 -> https://www.taboola.com`, jadi endpoint tersebut bukan success oracle utama target akhir
- `link.adlink.click` sample set awalnya memang ketutup Cloudflare managed challenge:
  - pre-origin status = `403`
  - title = `Just a moment...`
  - `cf_clearance` tidak wajib muncul di cookie dump untuk bisa lolos
  - lane live yang terbukti di VPS ini adalah browser non-headless `undetected-chromedriver` di bawah `xvfb-run`, bukan one-shot HTTP requests biasa
- `link.adlink.click` sekarang sudah punya hasil live terverifikasi untuk beberapa sampel:
  - teruji: `6Omf`, `VnLS`, `SfRi`, `CBuahny8kxt`
  - browser live keluar dari host `link.adlink.click`
  - redirect chain terlihat menuju `https://www.maqal360.com/secure.php?id=<alias>&site=adlink.click`
  - interstitial `maqal360` ternyata bukan hasil akhir. Lane yang terbukti untuk `SfRi` adalah:
    1. tunggu sekitar 10 detik per step di page `maqal360`
    2. panggil `verify.php` untuk ambil URL step berikutnya
    3. ulang sampai gate `GO NEXT 7/7`
    4. jika `verify.php` terakhir mengembalikan `{"status":"error"}`, langsung pindah ke `https://blog.adlink.click/<alias>` dalam browser session yang sama
    5. ekstrak `a.get-link` dari page blog
  - success oracle terverifikasi untuk `SfRi` sekarang adalah:
    - `https://earn-pepe.com/member/shortlinks/verify/ca7c179027eb04abfb79`
  - page `blog.adlink.click/SfRi` yang benar memuat:
    - `form action = /links/go`
    - hidden `ad_form_data`
    - anchor `Get Link` menuju URL verify `earn-pepe`
- `xut.io` sekarang tidak lagi hanya berhenti di mapping Step 1 di level engine:
  - helper live `xut_live_browser.py` sudah dihubungkan ke `engine.py`
  - helper ini bisa melewati Step 1, maju ke `gamescrate`, lalu melakukan warm-browser handoff ke patched local FlareSolverr
  - status terbaru **live_bypass** untuk sample `https://xut.io/hd7AOJ` karena helper sudah live-proven sampai exact `Get Link` -> `http://tesskibidixxx.com/`
  - lane yang lebih cepat sekarang sudah terbukti:
    1. lolos Cloudflare sampai browser mendarat di article `maqal360`
    2. langsung lompat ke `https://blog.adlink.click/<alias>` dalam browser session yang sama
    3. ekstrak `Get Link` tanpa perlu menunggu 7 putaran `maqal360`
  - requests-only murni masih gagal untuk target ini:
    - `GET https://link.adlink.click/SfRi` -> `403 Just a moment...`
    - `GET https://blog.adlink.click/SfRi` -> `403 Just a moment...`
    - bahkan setelah cookie browser disalin ke `requests.Session`, request HTTP ke `blog.adlink.click` masih kena `403`
  - lane browserless baru sekarang sudah terbukti untuk sampel `CBr27fn4of3` dan sampel lain yang dites:
    1. skip Selenium
    2. pakai `curl_cffi` impersonation langsung ke `https://blog.adlink.click/<alias>`
    3. parse `form#go-link`
    4. submit final sekitar `4.0s` setelah page load
  - benchmark lokal untuk `CBr27fn4of3` sekarang turun ke sekitar `5.6s` sampai `5.9s` end-to-end di engine
- `xut.io` sample baru `https://xut.io/3lid` sudah dipetakan sebagai wrapper awal ke family `autodime.com/cwsafelinkphp`:
  - `GET https://xut.io/3lid` memberi `302 -> https://autodime.com/cwsafelinkphp/go.php?link=snpurl%2F3lid`
  - entry `xut.io` set cookie `AppSession` dan `ref3lid`
  - hop `autodime ... go.php` set cookie `fexkomin` yang payloadnya memuat `step=1` dan `sid=/3lid`, lalu `302` ke Google wrapper untuk `https://autodime.com/`
  - setelah cookie + referer Google dipakai ke `https://autodime.com/`, page yang muncul adalah `Step 1/6`
  - runtime config live yang teramati:
    - `countdown = 10`
    - `captchaProvider = iconcaptcha`
    - `iconcaptchaEndpoint = /cwsafelinkphp/sl-iconcaptcha-request.php`
    - `verifyUrl = /cwsafelinkphp/sl-iconcaptcha-verify.php`
  - contract load Step 1 sekarang sudah terverifikasi lebih dalam:
    - browser mengirim `X-Requested-With: XMLHttpRequest`
    - browser juga mengirim `X-IconCaptcha-Token` yang nilainya sama dengan hidden `_iconcaptcha-token`
    - browser session punya cookie path-scoped `CWSLSESSID` di `/cwsafelinkphp/`
    - replay HTTP di luar browser sekarang bisa memuat challenge lagi kalau pakai cookie penuh + `X-IconCaptcha-Token`
    - replay yang sama tanpa header token itu jatuh ke error `invalid form token`
  - contract selection Step 1 sekarang juga sudah kebuka:
    - klik user dikirim sebagai `action = SELECTION` ke `/cwsafelinkphp/sl-iconcaptcha-request.php`
    - payload membawa `challengeId`, `x`, `y`, `width`, `token`, `timestamp`, `initTimestamp`
    - kalau pilihan salah, respons tidak mengandung `completed=true` dan widget reset ke challenge baru
  - solver IconCaptcha lama ternyata belum cocok untuk varian autodime ini:
    - solver bisa baca canvas, tapi pada sample live yang diuji hasil pilihannya sering salah
    - brute-force live menunjukkan sel benar berubah per challenge dan minimal satu pilihan valid memang bisa meloloskan Step 1
  - progres live sesudah Step 1 sekarang sudah terbukti:
    - `Step 2/6` di `autodime.com/blog/...`
    - `Step 3/6` di `textfrog.com/links/...`
    - `Step 4/6` di `textfrog.com/links/...`
    - handoff ke `https://gamescrate.app/cwsafelinkphp/setcookie.php?t=...`
  - sample downstream final yang Boskuu kasih untuk alias ini:
    - `https://onlyfaucet.com/links/back/s7tM4CWuTNyfUkOLoqjR/USDT/b67127d45564acfeb4ef509e8a682ff5`
  - update live terbaru:
    - local `indra-api-hub` IconCaptcha lane sempat masih pakai default lama `similarity_threshold = 5.0`; sekarang sudah disamakan ke `20.0` dan service sudah direstart
    - setelah reload itu, Step 1 kembali bisa auto-lolos di browser live via API solver lokal
    - verifikasi baru menunjukkan Step 1 kadang lolos di attempt pertama, kadang butuh beberapa refresh challenge, jadi lane ini sudah lebih kuat tetapi belum 100% stabil
    - same-session browser replay sekarang sudah terbukti bisa menyeberang lagi sampai `gamescrate.app/cwsafelinkphp/setcookie.php?t=...` setelah solver reload
    - probe DOM headless di `gamescrate` menunjukkan page memuat challenge platform Cloudflare dan placeholder hidden input `cf-turnstile-response`, tetapi tidak mengekspos iframe/checkbox selector biasa ke Selenium
    - namun blind click ke sisi kiri container widget `#GQTnq7` mengubah state page dari `Performing security verification` menjadi `Verifying you are human. This may take a few seconds.`
    - artinya widget Cloudflare itu benar-benar ada dan merespons pointer input, hanya saja boundary DOM/selector-nya tersembunyi atau tidak dirender seperti elemen checkbox biasa di probe ini
  - arti praktis saat ini: blocker utama sudah pindah lagi, dari `Step 1 captcha` ke `gamescrate Cloudflare gate` sebelum oracle final
- Supported-sites registry milestone:
  - `supported_sites.py` sekarang menjadi sumber data resmi untuk status family, sample URL, expected final, handler, proof, blockers, dan command alias
  - `/status` dan `/supported` di bot sekarang mengambil data dari registry ini, bukan daftar hardcoded lama
  - status saat ini sengaja ketat: hanya family yang terbukti stabil/live saat ini diberi label `live_bypass`; token extraction dan partial lane tidak dinaikkan jadi working hanya karena pernah mengeluarkan candidate URL
- New implementation milestone:
  - `projects/shortlink-bypass-bot/engine.py` sekarang sudah ada sebagai core analyzer modular per family
  - `projects/shortlink-bypass-bot/bot.py` sudah ada sebagai wrapper Telegram sederhana untuk `/bypass` dan `/adlink`
  - engine saat ini sudah bisa:
    - deteksi `xut.io` atau direct `autodime.com/cwsafelinkphp/go.php` sebagai family `autodime.cwsafelinkphp`
    - replay warmup wrapper sampai `https://autodime.com/` lalu mengembalikan mapping terstruktur untuk gate `Step 1/6`
    - deteksi `adlink.click` sebagai `CLOUDFLARE_CHALLENGE`
    - extract `oii.la` token-decoded downstream target
    - replay `shrinkme.click` chain `ThemeZon -> MrProBlogger -> /links/go` untuk sampel yang sudah terverifikasi
    - bedain hasil `embedded target extracted` vs `captcha/timer flow belum replayed`
- Deployment milestone:
  - bot sudah dideploy sebagai systemd service `shortlink-bypass-bot.service`
  - username bot terverifikasi: `@OfficialWafferBot`
  - command bot terpasang: `/start`, `/help`, `/status`, `/ping`, `/bypass`, `/adlink`
  - UX update baru:
    - bot sekarang kirim ack cepat saat command masuk
    - plain URL sekarang otomatis diperlakukan seperti `/bypass URL`
    - untuk proses lama, bot mengedit pesan status yang sama tiap ~8 detik agar user bisa lihat tahap aktif tanpa spam pesan baru
  - access gate baru:
    - user wajib join grup `Cari Garapan` dulu sebelum bot melayani command
    - gate diverifikasi pakai `getChatMember` ke supergroup `-1003843116263`
    - blocked user dapat tombol `Join Cari Garapan` dan `Sudah join, cek lagi`
- Packaging milestone:
  - repo lokal sudah dirapikan untuk publish
  - dependency live-helper dan TLS impersonation sekarang ikut didaftarkan di `requirements.txt`
  - helper Adlink sekarang default ke interpreter aktif, jadi tidak hardcode lagi ke path workspace Rawon
  - file deploy contoh dipisah ke `systemd/shortlink-bypass-bot.service.example`
  - starter env sekarang juga mencakup gate config untuk grup wajib join
  - repo GitHub sudah dibuat di `IndraLawliet13/shortlink-bypass-bot` dengan visibility `private`
- Turnstile solver ops milestone:
  - public repo `IndraLawliet13/turnstile-solver-api` sudah di-clone ke `tmp-gh/turnstile-solver-api`
  - solver API sudah hidup sebagai systemd service `turnstile-solver-api.service`
  - bind lokal: `127.0.0.1:5000`
  - contract terverifikasi:
    - `GET /turnstile?url=<url>&sitekey=<sitekey>[&action=...][&cdata=...]`
    - `GET /result?id=<taskId>`

## Retrieval preflight
### What is already known
- Workspace punya lane captcha/solver yang cukup maju, termasuk hCaptcha-related work dan FlareSolverr experiments.
- Ada jejak riset faucet/bypass lama, tapi belum ada case note spesifik untuk family shortlink ini.

### Last blocker
- `adlink.click` sekarang sudah ada runner lokal yang bisa menembus challenge untuk sampel `6Omf` lewat browser live non-headless.
- Boundary sesudah clearance mulai terlihat untuk family `adlink.click`, tetapi generalisasi ke sampel lain masih perlu verifikasi.
- Belum ada satu runner lokal yang mengikat semua family ke session, captcha, timer, dan final redirect verification dalam satu jalur umum.

### Next best action
- Pertahankan lane live `adlink.click` yang sekarang sudah proven di beberapa sampel, lalu rapikan supaya stabil untuk dipanggil bot.
- Jadikan lane browserless `curl_cffi -> blog.adlink.click -> /links/go` sebagai default utama untuk `link.adlink.click`, lalu simpan Chromium sebagai fallback saja.
- Pertahankan lane `oii.la` berbasis hidden-token decode sebagai lane utama yang paling murah dan paling reproducible.
- Jika riset `oii.la` dilanjut, fokuskan ke success oracle setelah URL `links/back/...`, bukan ke POST `advertisingcamps` yang saat ini terbukti hanya ad handoff.
- Untuk `shrinkme.click`, fokus lanjutan sekarang bukan lagi proof-of-concept, tapi validasi apakah lane direct `MrProBlogger` dengan ThemeZon referer ini konsisten di alias lain juga.
- Untuk `xut.io`, narrow action sekarang sudah bergeser lagi:
  - pertahankan lane Step 1 yang sekarang lebih konsisten lewat solver API lokal yang sudah direload
  - fokus utama berikutnya adalah boundary `gamescrate` Cloudflare managed challenge, bukan lagi sekadar mapping `SELECTION`
  - cek apakah challenge itu butuh lane non-headless / xvfb / real Chrome profile / interaksi widget berbasis koordinat atau shadow boundary yang tidak muncul di probe selector biasa
- Engine sudah punya handler awal untuk family ini, tapi masih jujur berhenti di `ICONCAPTCHA_STEP1_MAPPED` sampai success oracle final benar-benar ketemu.
- New sample target implementation status:
  - `tpi.li` and `aii.sh` now use the shared token-tail landing handler
  - `sfl.gl` now has a browserless SafelinkU API handler with WARP proxy fallback for Cloudflare-blocked VPS egress
  - `ez4short.com` now has a fast live handler through the `game5s.com` referer lane
  - `gplinks.co` now has a partial PowerGam mapper, but final remains blocked by missing ad-impression/conversion state
  - `cuty.io` now has a live CDP Chrome + local Turnstile solver helper that reaches the sampled `google.com` oracle
  - `lnbz.la` now has a browserless article/survey-chain handler that reaches the sampled `cryptoearns.com` oracle
  - `exe.io` now has a gated mapper through the two-stage exeygo CakePHP forms, but final remains blocked by Turnstile/reCAPTCHA token validity

## Boundary catalog
- `entry shortlink` -> status: narrowed
- `redirect/session cookie gate` -> status: primary
- `timer/wait gate` -> status: narrowed
- `captcha gate` -> status: in progress
- `final verify/back endpoint` -> status: narrowed
- `downstream reward-site callback/state mutation` -> status: open

### Current top-level status after Adlink fix
- [in progress] 1. Petakan flow teknis per shortlink family
- [done] 2. Audit komponen solver/browser/flaresolverr yang sudah ada di workspace
- [in progress] 3. Tentukan boundary utama dan success oracle per family
- [in progress] 4. Rancang arsitektur bot bypass yang modular
- [done] 5. Buat POC runner untuk minimal 1 family yang bisa direplay
- [done] 6. Verifikasi POC pada sampel link nyata tanpa spam
- [in progress] 7. Dokumentasikan lesson reusable dan next patch list
- [done] 8. Deploy bot Telegram persist di Rawon

## Structured notes
- Family map:
  - `projects/shortlink-bypass-bot/references/shortlink-family-initial-map.md`
- Current code:
  - `projects/shortlink-bypass-bot/engine.py`
  - `projects/shortlink-bypass-bot/bot.py`
  - `projects/shortlink-bypass-bot/README.md`

## 2026-04-28 shared-blocker phase
- Restored `state/flaresolverr-exp/src` source files after they were accidentally deleted from the worktree, which fixed `xut_live_browser.py` imports for `dtos` and `flaresolverr_service`.
- Pinned xut live helper ChromeDriver to the installed Chrome major version so undetected-chromedriver does not pull a mismatched major.
- Added a local Python IconCaptcha fallback for xut using the proven ClaimCoin solver when the old API hub endpoint returns 404.
- xut runtime/dependency blockers are repaired. One live run reached `gamescrate.app` Cloudflare after Step 1-4, but a later repeat still failed at Step 1, so the active blocker is solver stability plus gamescrate final gate.
- Added SFL WARP proxy fallback; `sfl.gl/18PZXXI9` now returns `https://google.com` again.
- Turnstile root cause found: stale long-lived browser pool returned instant `CAPTCHA_FAIL` with `elapsed_time=0`. Service refresh + retry fixed cuty and raw solver tokens for cuty/exe; exe still needs final token submission integration.

## 2026-04-28 xut.io final lane update
- `xut.io` is now live-proven for sample `https://xut.io/hd7AOJ`.
- Verified final oracle: `http://tesskibidixxx.com/` from xut Step 6 `Get Link` href.
- Remaining improvement is stability, not unknown flow mapping: Step 1 IconCaptcha and ChromeDriver can still fail intermittently, so retries and structured failure reports stay important.
- `gplinks.co` remains the last partial family, blocked by PowerGam/GPT enough-step proof.


## 2026-04-28 xut.io final update
- `xut.io` sample `https://xut.io/hd7AOJ` sekarang live-proven. Chain yang terbukti: IconCaptcha Step 1 -> Step 2/3/4 -> gamescrate Step 5 -> xut Step 6 -> exact visible `Get Link` -> `http://tesskibidixxx.com/`.
- Catatan stabilitas: IconCaptcha masih flaky dan Chrome/driver kadang mati, jadi helper tetap harus mengembalikan structured failure facts saat run gagal. Tetapi status family boleh naik karena ada live engine/helper final oracle yang jelas.
