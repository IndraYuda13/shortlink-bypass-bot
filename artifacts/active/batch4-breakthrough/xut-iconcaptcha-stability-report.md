# XUT IconCaptcha stability report

Date: 2026-04-29
Scope: XUT/autodime IconCaptcha Step 1 only. Production code was not edited.

## Files inspected

- `xut_live_browser.py`
- `iconcaptcha-solver/src/iconcaptcha_solver/solver.py`
- `iconcaptcha-solver/src/iconcaptcha_solver/api.py`
- `iconcaptcha-solver/tests/*`
- `iconcaptcha-solver/fixtures/autodime/live/labels.jsonl`
- `shortlink-bypass-bot/ROADMAP.md`
- `artifacts/active/total-optimization/xut-batch3-profile.md`
- `artifacts/active/total-optimization/xut-batch3-profile-raw*.json`

## Corpus found

- Existing preserved labeled XUT/autodime fixtures: **1** accepted/pass image.
- New live capture generated in this analysis: **1** accepted/pass image.
  - Capture dir: `artifacts/active/batch4-breakthrough/xut-captures/`
  - Run output: `artifacts/active/batch4-breakthrough/xut-live-capture-run1.json`
- Combined benchmark corpus: **2** accepted/pass images.
  - Combined temp corpus: `artifacts/active/batch4-breakthrough/combined-xut-fixtures/`
  - Benchmark output: `artifacts/active/batch4-breakthrough/combined-threshold-benchmark.json`

Important limitation: there are **zero preserved failed/wrong-selection images** with server verdict. This corpus can prove that the current solver handles two pass cases. It cannot prove first-attempt stability or identify a robust failure rule.

## Boundary catalog

| Boundary | Location | Evidence | Status |
|---|---|---|---|
| Step 1 widget readiness | Browser DOM `.iconcaptcha-widget`, `canvas.toDataURL()` | `xut_live_browser.py::solve_step1_until_step2` clicks widget then reads canvas | Open for timing optimization, not selection logic |
| Solver API contract | `http://127.0.0.1:8091/solve` | API returns `position/x/y`; current helper normalizes to `click_x/click_y` | Current code safe against old schema drift |
| Local solver contract | `solve_iconcaptcha_data_url(... similarity_threshold=20.0)` | Same algorithm exists in `claimcoin-autoclaim` and `iconcaptcha-solver` | Stable on available pass corpus |
| Server verdict | Page title/body changes to `Step 2/6` | Captures are labeled only after Step 2 appears | Strong verdict when present |
| Wrong selection reset | Widget returns new challenge when selection wrong | Documented in roadmap, but no fail images preserved | Needs data |

## Solver behavior observed

### Current algorithm

- Splits the canvas into 5 equal cells.
- Normalizes to grayscale/autocontrast.
- Trims 2 px border, resizes each cell to 32x32.
- Computes shift-aware mean absolute difference with max shift 10.
- Groups cells by distance threshold.
- Selects the smallest group, then highest distinctness inside that group.

### API vs local output

The live API at `127.0.0.1:8091` is healthy and returns the expected current shape.

For the two pass images, API output and local solver output agree at threshold `20.0`:

- `xut_autodime_1777348090667_attempt1_pass.png`
  - expected/pass position: 3
  - API/local selected: 3
  - confidence: 0.7293
  - groups at threshold 20: `[[0], [1], [2], [3], [4]]`
- `xut_autodime_1777398873404_attempt1_pass.png`
  - expected/pass position: 4
  - API/local selected: 4
  - confidence: 0.7209
  - groups at threshold 20: `[[0], [1], [2], [3], [4]]`

Older batch artifact `xut-batch3-profile-raw-3.json` showed an API shape without `click_x/click_y`, only `x/y`. Current `xut_live_browser.py::solve_canvas_via_local_api` already normalizes `x -> click_x`, `y -> click_y`, and `position -> selected_cell_number`, so that specific schema failure is already patched in current code.

## Threshold sweep

Command used:

```bash
PYTHONPATH=src .venv/bin/python scripts/benchmark_fixtures.py \
  /root/.openclaw/workspace/projects/shortlink-bypass-bot/artifacts/active/batch4-breakthrough/combined-xut-fixtures/labels.jsonl \
  --thresholds 3,5,8,12,16,20,22,24,28,32,40
```

Result summary on 2 pass samples:

- Thresholds `3,5,8,12,16,20,22`: 2/2 correct, avg confidence 0.7251.
- Threshold `24`: 2/2 correct, but confidence degrades because one sample collapses to a broad group.
- Threshold `28`: 2/2 correct, avg confidence 0.4751.
- Threshold `32`: 1/2 correct. The new pass sample is mis-solved as position 2 instead of position 4.
- Threshold `40`: 2/2 correct by all-group distinctness fallback, but confidence remains low and this is not a safe rule.

Conclusion: raising the threshold above the current `20.0` is unsafe. `20.0` is acceptable on available evidence. A lower threshold between `8` and `22` behaves the same on this tiny corpus, so there is no evidence-based reason to patch it.

## Live run performed

Command:

```bash
xvfb-run -a .venv/bin/python xut_live_browser.py https://xut.io/hd7AOJ \
  --timeout 300 \
  --iconcaptcha-capture-dir artifacts/active/batch4-breakthrough/xut-captures
```

Result:

- Step 1 passed on attempt 1.
- Solver provider: API.
- Selected position: 4.
- Confidence: 0.7209.
- Capture saved as `xut_autodime_1777398873404_attempt1_pass.png`.
- Later browser crashed after clicking `Open Final Page`, before final oracle. That is outside this Step 1 scope.

## Selection mistakes

No direct selection mistake was preserved in the available artifacts.

The only concrete instability clues are:

1. Roadmap says Step 1 sometimes needs several challenge refreshes.
2. Batch raw files show all captured Step 1 histories passed when a solver result was available.
3. One old artifact had API schema drift (`x/y` without `click_x/click_y`), already handled by current helper.
4. Threshold `32` creates a wrong answer on the new pass fixture, proving that aggressive threshold increases can reduce accuracy.

Because no failed challenge images exist, there is no safe way to infer whether real failures come from:

- the visual algorithm choosing the wrong cell,
- canvas capture timing before image settles,
- click coordinate scaling/offset,
- IconCaptcha server-side timing/session checks,
- or challenge refresh race after wrong/late click.

## Safe patch assessment

No production solver-rule patch is justified yet.

Safe changes if the main agent wants a production patch later:

1. **Data collection patch, safe:** preserve every attempt image, not only final recent history, and add `passed=false` rows when the page does not reach Step 2 after click. Current `save_iconcaptcha_capture()` already supports fail labels, so the main gap is running more live attempts with capture dir enabled and preserving labels.
2. **Debug payload patch, safe:** call API with `return_debug=true` or save local recomputed `pairwise_mad/distinctness` for every capture. Current API default omits `pairwise_mad`; this makes later failure triage weaker.
3. **Timing patch, safe but speed-focused:** replace fixed sleeps in Step 1 with polling for canvas non-empty and Step 2/reset state. This may reduce stale-canvas or post-click race risk, but it is not proven to improve first-attempt correctness.

Unsafe changes now:

- Do not raise `similarity_threshold` above `20.0` based on the current corpus. Threshold `32` failed on a known pass sample.
- Do not claim `95%` or first-attempt reliability. Corpus size is 2 pass samples and 0 fail samples.
- Do not promote all-group distinctness fallback as a rule. It was correct at threshold `40` here only by weak evidence and low confidence.

## Recommended next data plan

Collect at least 30 to 50 XUT Step 1 attempts before touching solver logic, and 100+ before making any `95%` claim.

Required label row per attempt:

```json
{
  "image": "...png",
  "attempt": 1,
  "passed": false,
  "selected_cell_number": 4,
  "click_x": 224,
  "click_y": 25,
  "confidence": 0.72,
  "groups": [[0], [1], [2], [3], [4]],
  "pairwise_mad": [[...]],
  "distinctness": [...],
  "threshold": 20.0,
  "provider": "api",
  "api_payload_keys": ["position", "x", "y"],
  "canvas_size": [320, 50],
  "canvas_rect": {"width": 320, "height": 50},
  "verdict": "step2|reset|timeout|exception"
}
```

Most useful probe matrix after enough fail images exist:

- thresholds: `8,12,16,20,22,24`
- max shifts: `6,8,10,12`
- crop border: `0,2,4`
- compare local result against API result for each image

## Bottom line

- Current `20.0` solver rule is the best safe rule from available evidence.
- First-attempt stability cannot be improved honestly from the current labeled corpus because there are no preserved wrong-selection failures.
- The next high-confidence move is data collection with debug fields, not a solver patch.
