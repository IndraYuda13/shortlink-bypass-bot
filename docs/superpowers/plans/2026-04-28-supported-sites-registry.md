# Supported Sites Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a single source of truth for supported shortlink families so bot commands and future API endpoints can integrate without duplicated hardcoded lists.

**Architecture:** Add `supported_sites.py` as the canonical registry. `bot.py` consumes the registry for `/status` and `/supported`. Docs mirror the registry but are not the source of truth.

**Tech Stack:** Python 3.12, dataclasses, unittest, existing Telegram bot and engine modules.

---

### Task 1: Registry test and model

**Files:**
- Create: `tests/test_supported_sites_registry.py`
- Create: `supported_sites.py`

- [x] Write a failing unittest that imports `SUPPORTED_SITES`, `LIVE_BYPASS_HOSTS`, `registry_as_dicts`, and `status_lines`.
- [x] Verify it fails because `supported_sites` does not exist.
- [x] Implement `SupportedSite` dataclass and the current registry.
- [x] Verify the unittest passes.

### Task 2: Bot status integration

**Files:**
- Modify: `bot.py`

- [x] Import `status_lines` from `supported_sites`.
- [x] Replace the old hardcoded `/status` list with registry-derived output.
- [x] Add `/supported` as a status alias for future API/integration clarity.
- [x] Verify the bot status test passes.

### Task 3: Documentation sync

**Files:**
- Modify: `README.md`
- Modify: `ROADMAP.md`
- Create: `docs/SUPPORTED_SITES.md`
- Modify: `CHANGELOG.md`

- [x] Update README current support table so only currently stable/proven lanes are called `Live bypass`.
- [x] Mark stale/flaky lanes like `cuty.io` and `sfl.gl` as partial.
- [x] Document registry fields and API integration rule in `docs/SUPPORTED_SITES.md`.
- [x] Add changelog entry for the registry and current support-state correction.

### Task 4: Verification and deploy

**Files:**
- Runtime service: `shortlink-bypass-bot.service`

- [x] Run `python -m unittest discover -s tests -p 'test*.py' -v`.
- [x] Run live sample smoke checks for at least `shrinkme.click` and `link.adlink.click`.
- [x] Restart `shortlink-bypass-bot.service`.
- [x] Confirm service is active.
- [ ] Commit and push repo.
- [ ] Run workspace MyAiAgent autosync.
