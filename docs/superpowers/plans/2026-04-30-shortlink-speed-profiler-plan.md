# Shortlink Speed Profiler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add measurable speed profiling and a benchmark matrix for shortlink handlers without weakening final URL accuracy.

**Architecture:** Keep the first implementation small: helpers already emit `timeline` and `waited_seconds`, so add a shared timeline profiler that derives per-stage timing when timestamps exist and summarizes existing timeline stages when they do not. Add a CLI benchmark runner that executes selected sample URLs through `engine.py` and writes JSONL records for comparison. Preserve `final_url_validator.py` as the canonical downstream oracle for final submit responses.

**Tech Stack:** Python 3.11+, unittest, existing `ShortlinkBypassEngine`, JSON/JSONL artifacts.

---

### Task 1: Shared timeline profiler

**Files:**
- Create: `timeline_profiler.py`
- Create: `tests/test_timeline_profiler.py`

- [ ] Add tests for stage summary and elapsed durations.
- [ ] Implement `summarize_timeline(timeline)` and `profile_result(payload)`.
- [ ] Verify targeted tests.

### Task 2: Benchmark matrix runner

**Files:**
- Create: `benchmark_matrix.py`
- Create: `tests/test_benchmark_matrix.py`

- [ ] Add tests for sample selection and JSONL record shaping.
- [ ] Implement CLI with `--family`, `--limit`, `--output`, `--timeout`.
- [ ] Use `supported_sites.SUPPORTED_SITES` samples and `ShortlinkBypassEngine`.
- [ ] Verify targeted tests.

### Task 3: Docs and status updates

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `supported_sites.py` only if live benchmark values change.

- [ ] Document benchmark command and profiler purpose.
- [ ] Record live verification outputs.
- [ ] Run full unittest suite.
- [ ] Restart `shortlink-bypass-bot.service` only if runtime files used by bot changed.
- [ ] Commit and push.
