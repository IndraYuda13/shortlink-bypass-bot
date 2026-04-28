# GPLinks HTTP Fast Lane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fast HTTP-first GPLinks lane that attempts to reproduce the proven live browser final path without launching Chrome, while keeping the current browser helper as fallback.

**Architecture:** Keep `_handle_gplinks` as the public family boundary. Add a focused `gplinks_http_fast.py` helper that owns HTTP session setup, PowerGam replay experiments, final candidate fetch, Turnstile token solving, and `/links/go` submit. `engine.py` tries HTTP fast first, then existing `gplinks_live_browser.py` fallback, then the old mapper.

**Tech Stack:** Python 3, `curl_cffi.requests`, BeautifulSoup, existing local Turnstile solver API at `127.0.0.1:5000`, existing unittest suite.

---

### Task 1: Add GPLinks HTTP fast helper skeleton and parser tests

**Files:**
- Create: `gplinks_http_fast.py`
- Create: `tests/test_gplinks_http_fast.py`

- [ ] **Step 1: Write tests for query decoding and final URL oracle**

```python
import unittest

from gplinks_http_fast import decoded_power_query, is_final_url


class GplinksHttpFastTests(unittest.TestCase):
    def test_decoded_power_query(self):
        url = 'https://powergam.online?lid=WVZUQw&pid=MTIyNDYyMg&vid=MTAxOTM2NTI2OQ&pages=Mw'
        self.assertEqual(decoded_power_query(url), {
            'lid': 'YVTC',
            'pid': '1224622',
            'vid': '1019365269',
            'pages': '3',
        })

    def test_final_url_oracle_rejects_internal_hosts(self):
        self.assertFalse(is_final_url('https://gplinks.co/YVTC?pid=1&vid=2'))
        self.assertFalse(is_final_url('https://powergam.online/'))
        self.assertFalse(is_final_url('chrome-error://chromewebdata/'))
        self.assertTrue(is_final_url('http://tesskibidixxx.com/'))


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run tests and verify failure**

Run: `.venv/bin/python -m unittest tests.test_gplinks_http_fast -v`

Expected: FAIL because `gplinks_http_fast` does not exist.

- [ ] **Step 3: Implement helper skeleton**

Create `gplinks_http_fast.py` with `decoded_power_query()`, `is_final_url()`, `run()`, and CLI `main()`. `run()` initially returns structured failure `HTTP_FAST_NOT_IMPLEMENTED`.

- [ ] **Step 4: Run tests and verify parser tests pass**

Run: `.venv/bin/python -m unittest tests.test_gplinks_http_fast -v`

Expected: PASS.

### Task 2: Implement HTTP session trace and final candidate fetch

**Files:**
- Modify: `gplinks_http_fast.py`
- Modify: `tests/test_gplinks_http_fast.py`

- [ ] **Step 1: Add mocked test for entry redirect and candidate URL construction**

Use `unittest.mock` to fake `curl_cffi.requests.Session.get()` returning a 302 entry redirect. Assert `run()` records `decoded_query` and `target_final_candidate`.

- [ ] **Step 2: Implement entry fetch**

`run(url, timeout, solver_url)` should:
1. create `curl_requests.Session(impersonate='chrome136')`,
2. GET original URL with redirects disabled,
3. decode PowerGam query,
4. build candidate `https://gplinks.co/{lid}?pid={pid}&vid={vid}`.

- [ ] **Step 3: Add live diagnostic CLI mode output**

The helper should always print one JSON object with `status`, `stage`, `message`, `facts`, and `timeline`.

### Task 3: Try HTTP PowerGam step replay

**Files:**
- Modify: `gplinks_http_fast.py`
- Update: `artifacts/active/2026-04-28-gplinks-final-push-workframe.md`

- [ ] **Step 1: Extract PowerGam forms and scripts**

GET PowerGam with `Referer: https://gplinks.co/YVTC`. Parse forms and hidden fields with BeautifulSoup. Store `adsForm` payload candidates in `timeline`.

- [ ] **Step 2: Replay conservative step candidates**

POST the discovered form with only DOM-provided fields first. Then try bounded candidate variants already falsified/known: step counter only if present, referer preserved, same cookies. Do not brute force arbitrary values.

- [ ] **Step 3: Fetch final candidate**

GET `target_final_candidate` in the same session. If page contains `form#go-link` and Turnstile sitekey, continue. If `/link-error?error_code=not_enough_steps`, return `HTTP_FAST_POWERGAM_LEDGER_REJECTED` and fallback remains browser.

- [ ] **Step 4: Record evidence**

Append exact live result to `artifacts/active/2026-04-28-gplinks-final-push-workframe.md`.

### Task 4: Submit final GPLinks page over HTTP if candidate is accepted

**Files:**
- Modify: `gplinks_http_fast.py`
- Modify: `tests/test_gplinks_http_fast.py`

- [ ] **Step 1: Add unit test for final form extraction**

Fixture HTML should include `form#go-link`, `_csrfToken`, `.cf-turnstile data-sitekey`, and expected action `/links/go`. Assert extraction returns action URL, CSRF payload, and sitekey.

- [ ] **Step 2: Implement final form extraction**

Add `extract_final_gate(html, page_url)` returning `{action, payload, sitekey}`.

- [ ] **Step 3: Solve Turnstile and post `/links/go`**

Reuse local solver API contract from `cuty_live_browser.solve_turnstile`. POST with `X-Requested-With: XMLHttpRequest`, same-origin referer, form fields, and both `cf-turnstile-response` and `g-recaptcha-response`.

- [ ] **Step 4: Success oracle**

Only return `status=1` if JSON has `url` and `is_final_url(url)` is true. Otherwise return structured failure.

### Task 5: Wire engine HTTP-first fallback chain

**Files:**
- Modify: `engine.py`
- Modify: `tests/test_gplinks.py`

- [ ] **Step 1: Add `_resolve_gplinks_http_fast()` unit test**

Mock it returning `{'status': 1, 'bypass_url': 'http://tesskibidixxx.com/', 'waited_seconds': 31.2}` and assert `_handle_gplinks` returns `status=1`, stage `http-fast`, before invoking live browser.

- [ ] **Step 2: Implement helper constants and subprocess wrapper**

Add `GPLINKS_HTTP_FAST_HELPER`, `GPLINKS_HTTP_FAST_TIMEOUT`, and `_resolve_gplinks_http_fast()` matching existing helper wrapper style.

- [ ] **Step 3: Update `_handle_gplinks` order**

Order must be:
1. HTTP fast helper,
2. live browser helper,
3. old browserless mapper fallback.

### Task 6: Verify, document, deploy, and push

**Files:**
- Modify: `README.md`
- Modify: `ROADMAP.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/SUPPORTED_SITES.md` if status wording changes

- [ ] **Step 1: Run unit tests**

Run: `.venv/bin/python -m unittest discover -s tests -v`

Expected: all tests pass.

- [ ] **Step 2: Run live helper test**

Run: `.venv/bin/python gplinks_http_fast.py https://gplinks.co/YVTC --timeout 90`

Expected if successful: status `1`, final `http://tesskibidixxx.com/`, waited below browser helper. If unsuccessful due PowerGam ledger, documented structured failure and browser fallback remains active.

- [ ] **Step 3: Run live engine test**

Run: `.venv/bin/python engine.py https://gplinks.co/YVTC --pretty`

Expected: final target still returned. Preferred stage is `http-fast`; acceptable fallback is `live-browser` with documented HTTP blocker.

- [ ] **Step 4: Restart bot and verify service**

Run: `systemctl restart shortlink-bypass-bot.service && systemctl is-active shortlink-bypass-bot.service`

Expected: `active`.

- [ ] **Step 5: Commit and push**

Run:
```bash
git add gplinks_http_fast.py tests/test_gplinks_http_fast.py engine.py tests/test_gplinks.py README.md ROADMAP.md CHANGELOG.md docs/SUPPORTED_SITES.md artifacts/active/2026-04-28-gplinks-final-push-workframe.md
git commit -m "Add gplinks HTTP fast lane"
git push
```

- [ ] **Step 6: Sync MyAiAgent backup**

Run: `/root/.openclaw/workspace/scripts/myaiagent-autosync.sh`

Expected: pushed commit SHA printed.

## Self-review

- Scope is one subsystem: GPLinks HTTP-first optimization.
- Browser fallback remains mandatory until HTTP fast has a live final oracle.
- No status promotion should be based on candidate URL only.
- Tests cover parser, final oracle, form extraction, and engine ordering.
