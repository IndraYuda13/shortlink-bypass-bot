# Shortlink Bypass Bot Roadmap

## Scope
- Target awal:
  - `link.adlink.click`
  - `shrinkme.click`
  - `oii.la`
- Contoh downstream yang sudah terlihat dari sampel:
  - `coinadster.com`
  - `99faucet.com`
  - `earn-pepe.com`

## Top-level checklist
- [in progress] 1. Petakan flow teknis per shortlink family
- [done] 2. Audit komponen solver/browser/flaresolverr yang sudah ada di workspace
- [in progress] 3. Tentukan boundary utama dan success oracle per family
- [in progress] 4. Rancang arsitektur bot bypass yang modular
- [done] 5. Buat POC runner untuk minimal 1 family yang bisa direplay
- [done] 6. Verifikasi POC pada sampel link nyata tanpa spam
- [in progress] 7. Dokumentasikan lesson reusable dan next patch list
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
- New implementation milestone:
  - `projects/shortlink-bypass-bot/engine.py` sekarang sudah ada sebagai core analyzer modular per family
  - `projects/shortlink-bypass-bot/bot.py` sudah ada sebagai wrapper Telegram sederhana untuk `/bypass` dan `/adlink`
  - engine saat ini sudah bisa:
    - deteksi `adlink.click` sebagai `CLOUDFLARE_CHALLENGE`
    - extract `oii.la` token-decoded downstream target
    - replay `shrinkme.click` chain `ThemeZon -> MrProBlogger -> /links/go` untuk sampel yang sudah terverifikasi
    - bedain hasil `embedded target extracted` vs `captcha/timer flow belum replayed`
- Deployment milestone:
  - bot sudah dideploy sebagai systemd service `shortlink-bypass-bot.service`
  - username bot terverifikasi: `@OfficialWafferBot`
  - command bot terpasang: `/bypass`, `/adlink`, `/help`
  - UX update baru:
    - bot sekarang kirim ack cepat saat command masuk
    - untuk proses lama, bot mengedit pesan status yang sama tiap ~8 detik agar user bisa lihat tahap aktif tanpa spam pesan baru
- Packaging milestone:
  - repo lokal sudah dirapikan untuk publish
  - dependency live-helper dan TLS impersonation sekarang ikut didaftarkan di `requirements.txt`
  - helper Adlink sekarang default ke interpreter aktif, jadi tidak hardcode lagi ke path workspace Rawon
  - file deploy contoh dipisah ke `systemd/shortlink-bypass-bot.service.example`
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

## Boundary catalog
- `entry shortlink` -> status: narrowed
- `redirect/session cookie gate` -> status: primary
- `timer/wait gate` -> status: narrowed
- `captcha gate` -> status: primary
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
