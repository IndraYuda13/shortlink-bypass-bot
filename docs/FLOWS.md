# Flows

## High-level architecture

```mermaid
flowchart TD
    A[Telegram command] --> B[bot.py]
    B --> C[engine.py]
    C --> D{Family handler}
    D -->|Static analysis| E[Structured result]
    D -->|Browserless TLS impersonation| E
    D -->|Live browser fallback needed| F[adlink_live_browser.py]
    F --> E
    E --> B
    B --> G[Telegram status edit or final reply]
```

## Adlink live lane

```mermaid
flowchart TD
    A[link.adlink.click alias] --> B[Cold HTTP probe]
    B -->|Cloudflare 403 in plain requests| C[Open blog.adlink.click alias via curl_cffi impersonation]
    C --> D[Parse form#go-link and hidden ad_form_data]
    D --> E[Wait real timer boundary about 4 seconds]
    E --> F{POST /links/go returns final URL?}
    F -->|Yes| G[Return downstream verify URL]
    F -->|No| H[Fallback: launch live Chromium under xvfb]
    H --> I[Pass challenge and establish session]
    I --> J[Retry blog extraction in browser session]
    J --> G
```

## Current Adlink success oracle

A run is treated as successful only when the rendered blog page exposes the final downstream target, typically through:

- `a.get-link`
- `form.go-link`
- hidden `ad_form_data`
- final reward-site verify URL such as `.../member/shortlinks/verify/...`

Intermediate article pages and bare `https://adlink.click/` landings are not treated as success.

## ShrinkMe fast lane

```mermaid
flowchart TD
    A[shrinkme.click alias] --> B[Direct GET to en.mrproblogger.com alias]
    B --> C[Use Referer: https://themezon.net/]
    C --> D[Parse form#go-link and hidden inputs]
    D --> E[Wait real timer boundary about 11.6 seconds]
    E --> F[POST /links/go in same session]
    F --> G{JSON returns downstream /links/back URL?}
    G -->|Yes| H[Return final reward URL]
    G -->|No| I[Fallback to longer ThemeZon replay evidence lane]
```
