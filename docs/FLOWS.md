# Flows

## High-level architecture

```mermaid
flowchart TD
    A[Telegram command] --> B[bot.py]
    B --> C[engine.py]
    C --> D{Family handler}
    D -->|Static analysis| E[Structured result]
    D -->|Live browser needed| F[adlink_live_browser.py]
    F --> E
    E --> B
    B --> G[Telegram status edit or final reply]
```

## Adlink live lane

```mermaid
flowchart TD
    A[link.adlink.click alias] --> B[Cold HTTP probe]
    B -->|Cloudflare 403| C[Launch live Chromium under xvfb]
    C --> D[Pass challenge and establish session]
    D --> E[First external hop appears]
    E --> F[Fast lane: open blog.adlink.click alias]
    F --> G{Get Link anchor found?}
    G -->|Yes| H[Return downstream verify URL]
    G -->|No| I[Fallback: follow maqal360 verify.php chain]
    I --> J[Retry blog page extraction in same session]
    J --> H
```

## Current Adlink success oracle

A run is treated as successful only when the rendered blog page exposes the final downstream target, typically through:

- `a.get-link`
- `form.go-link`
- hidden `ad_form_data`
- final reward-site verify URL such as `.../member/shortlinks/verify/...`

Intermediate article pages and bare `https://adlink.click/` landings are not treated as success.
