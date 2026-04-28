# Turnstile batch 3 profile: Cuty/Exe

Date: 2026-04-28 23:55-23:59 WIB  
Scope: local `turnstile-solver-api` latency for `cuty.io/AfaX6jx` and `exe.io/vkRI1`.  
Constraint: no production code edited.

## Workframe

Objective: isolate how much of current Cuty/Exe runtime is local Turnstile solving versus HTTP/browser flow overhead.

Success oracle:
- local solver returns `status=ready` with token for both known Cuty and Exe sitekeys
- task creation latency and result-ready latency are recorded
- service/browser-pool state is checked before making bottleneck claims

Known samples/sitekeys:
- Cuty: `https://cuttlinks.com/AfaX6jx`, sitekey `0x4AAAAAAABnHbN4cNchLhd_`
- Exe: `https://exeygo.com/vkRI1`, sitekey `0x4AAAAAACPCPhXQQr5wP1VW`

## Parent checklist

- [done] Inspect `cuty_http_fast.py`, `exe_http_fast.py`, and `cuty_live_browser.solve_turnstile()`.
- [done] Check `turnstile-solver-api.service` status and recent logs.
- [done] Measure direct `/turnstile` task creation and `/result` ready timing.
- [done] Compare measured solver latency against current Cuty/Exe engine baselines.
- [done] Write safe optimization recommendations.

## Code-path findings

### Shared solver client

`cuty_live_browser.solve_turnstile()` is reused by:
- `cuty_http_fast.py`
- `exe_http_fast.py`
- `cuty_live_browser.py`
- `exe_live_browser.py`

Client behavior:
- creates a solver task through `GET /turnstile?url=...&sitekey=...`
- polls `GET /result?id=...`
- polling interval is fixed at `5s`
- one retry is attempted only when the solver returns an error, not when it is merely slow

Meaning: if the solver becomes ready just after a poll, current caller can add up to about `5s` of avoidable wait.

### Cuty HTTP fast lane

Observed fixed waits in code:
- waits for local Turnstile token
- after successful captcha POST and `form#submit-form`, sleeps `9s`
- VHit calls are skipped by default because prior live ablation proved current sample can pass without them

Current baseline from `current-fast-token-baseline.jsonl`:
- `cuty.io/AfaX6jx`: `73.9s` wall, `73.2s` engine waited, final `https://www.google.com/`

### Exe HTTP fast lane

Observed fixed waits in code:
- waits for local Turnstile token
- sleeps `counter_value + 1`, usually `7s`, before posting `form#link-view`
- sleeps another `counter_value + 1`, usually `7s`, before posting `form#go-link`

Current baseline from `current-fast-token-baseline.jsonl`:
- `exe.io/vkRI1`: `72.2s` wall, final `https://www.google.com/?gws_rd=ssl`

## Service state

Service checked live:

```text
turnstile-solver-api.service active since 2026-04-28 22:42:21 WIB
ExecStart: api_solver.py --browser_type chrome --thread 2 --host 127.0.0.1 --port 5000
Drop-in: RuntimeMaxSec=21600, RestartSec=3
Browser pool initialized with 2 browsers
Memory around check: ~497M current, ~956M peak
```

Recent systemd evidence:
- service reached `RuntimeMaxSec` at `22:42:17`
- restarted cleanly at `22:42:21`
- this matches the earlier stabilization decision to refresh stale browser pools every 6h

Recent solver log evidence before this profile:
- successful solves after refresh were mostly `~42-53s`
- no instant `CAPTCHA_FAIL elapsed_time=0` seen in the checked tail
- from last ~200KB of solver log: `68` success rows, min `24.674s`, max `57.035s`, mean `43.492s`, median `45.45s`

## Direct measurement

Raw measurement artifact:
- `artifacts/active/total-optimization/turnstile-batch3-profile-raw.json`

Method:
- direct local HTTP calls with Python `requests`
- 1-second result polling to see actual ready time more precisely than production's 5-second poll
- two passes:
  1. sequential Cuty then Exe
  2. concurrent Cuty + Exe to test the 2-browser pool behavior

### Measured summary

| Mode | Target | Create latency | Ready latency | Token length | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| sequential | Cuty | `0.022s` | `54.119s` | `773` | ready |
| sequential | Exe | `0.039s` | `48.208s` | `752` | ready |
| concurrent | Cuty | `0.016s` | `55.518s` | `752` | ready |
| concurrent | Exe | `0.029s` | `53.078s` | `752` | ready |

Service log for the concurrent pass confirmed both browsers worked in parallel:

```text
23:59:07 Browser 2 solved in 52.038s
23:59:09 Browser 1 solved in 54.882s
```

## Bottleneck conclusion

Primary bottleneck: the solver browser challenge itself, not task creation or HTTP API overhead.

Evidence:
- task creation is effectively instant: `0.016-0.039s`
- `/result` HTTP calls are usually milliseconds
- ready latency is `48-56s` in this profile
- concurrent Cuty+Exe completed together in about `53-56s`, proving the 2-browser pool was not serializing these two jobs
- current full Cuty/Exe runtimes are `72-74s`, so Turnstile solving alone accounts for roughly `65-75%` of total runtime

Secondary overheads:
- `solve_turnstile()` production polling interval can add up to `~5s` extra latency per solve
- Exe has two hard waits totaling about `14s`
- Cuty has one hard wait of `9s`
- remaining time is normal network/form overhead

Not the current bottleneck:
- service startup or API request handling
- browser pool queueing for two concurrent jobs
- stale pool state, because current run returned tokens and logs show fresh successes after the scheduled refresh

## Safe optimization recommendations

1. **Reduce solver poll interval from `5s` to `1-2s`, or make it adaptive.**
   - Safe because it only checks local `/result` more often.
   - Expected gain: usually `0-4s`, worst-case close to `5s` per Turnstile solve.
   - Low risk, but avoid 1s polling if many callers will run at high concurrency. `2s` is a balanced default.

2. **Keep `--thread 2` for now.**
   - The concurrent test proved two simultaneous solves complete in parallel.
   - Increasing threads may help only when more than two `/bypass` Turnstile jobs run at once.
   - Do not increase blindly: each browser is heavy and current service already peaks near `~956M` memory.

3. **If queueing appears in production later, add a lightweight queue/active-task metric before raising thread count.**
   - Success oracle: third simultaneous task waits much longer than first two while first two keep normal `~50s` solve time.
   - Only then test `--thread 3` with memory/CPU monitoring.

4. **Do not try to optimize Cuty/Exe by touching Turnstile tokens or reusing tokens.**
   - Tokens are ephemeral and bound to page/sitekey/session context.
   - Reuse/caching is likely invalid and unsafe for correctness.

5. **Potential Exe-only timing probe: test whether either `counter_value + 1` sleep can be shortened.**
   - Current code pays about `14s` after token readiness.
   - This must be live-oracle tested because those waits protect CakePHP/timer state.
   - Suggested env-guard first, not direct default change.

6. **Potential Cuty-only timing probe: test reducing the `9s` final sleep.**
   - This is smaller than the solver cost but may save a few seconds.
   - Must preserve downstream final URL oracle.

## Bottom line

Current local solver is healthy but inherently slow: expect about `50s` per Cuty/Exe token. The service/browser pool is not the bottleneck for one or two concurrent jobs. The safest immediate optimization is caller-side polling reduction, followed by guarded live probes of the Cuty/Exe fixed timer sleeps.
