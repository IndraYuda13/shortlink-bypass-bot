#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import gplinks_live_browser as glb  # noqa: E402

URL = "https://gplinks.co/YVTC"
OUT = ROOT / "artifacts" / "active" / "total-optimization" / "gplinks-batch3-profile-raw.json"

events: list[dict] = []
t0 = time.monotonic()

def now() -> float:
    return round(time.monotonic() - t0, 3)

def slim_state(st: dict | None) -> dict:
    st = st or {}
    body = st.get("text") or ""
    return {
        "href": st.get("href"),
        "title": st.get("title"),
        "timerText": st.get("timerText"),
        "sitekey": st.get("sitekey"),
        "captchaInput": st.get("captchaInput"),
        "captchaButton": st.get("captchaButton"),
        "forms_count": len(st.get("forms") or []),
        "buttons": (st.get("buttons") or [])[:6],
        "text_head": body[:220],
    }

def event(kind: str, **data):
    item = {"t": now(), "kind": kind, **data}
    events.append(item)
    print(json.dumps(item, ensure_ascii=False), flush=True)

orig_build_driver = glb.build_driver
orig_wait_doc = glb.wait_document_ready
orig_wait_cf = glb.wait_not_cloudflare
orig_click = glb.click_next_powergam
orig_unlock = glb.unlock_final_gate
orig_solve = glb.solve_turnstile
orig_state = glb.state
orig_import = glb.import_session_cookies

def build_driver_wrap(*args, **kwargs):
    s = time.monotonic(); event("build_driver_start")
    try:
        return orig_build_driver(*args, **kwargs)
    finally:
        event("build_driver_end", duration=round(time.monotonic()-s, 3))

def wait_doc_wrap(driver, timeout=20, interval=0.5):
    s = time.monotonic(); href = None
    try:
        href = driver.current_url
    except Exception:
        pass
    event("wait_document_ready_start", timeout=timeout, interval=interval, href=href)
    out = orig_wait_doc(driver, timeout, interval)
    event("wait_document_ready_end", duration=round(time.monotonic()-s, 3), state=slim_state(out))
    return out

def wait_cf_wrap(driver, timeout):
    s = time.monotonic(); event("wait_not_cloudflare_start", timeout=timeout)
    out = orig_wait_cf(driver, timeout)
    event("wait_not_cloudflare_end", duration=round(time.monotonic()-s, 3), state=slim_state(out))
    return out

def click_wrap(driver):
    s = time.monotonic(); event("click_next_powergam_start")
    out = orig_click(driver)
    event("click_next_powergam_end", duration=round(time.monotonic()-s, 3), result=out)
    return out

def unlock_wrap(driver, solver_url, timeout_left):
    s = time.monotonic(); event("unlock_final_gate_start", timeout_left=timeout_left)
    try:
        out = orig_unlock(driver, solver_url, timeout_left)
        event("unlock_final_gate_end", duration=round(time.monotonic()-s, 3), summary={k: out.get(k) for k in ["sitekey", "token_used", "captcha_required", "final_href"]})
        return out
    except Exception as exc:
        event("unlock_final_gate_exception", duration=round(time.monotonic()-s, 3), error=str(exc)[:500])
        raise

def solve_wrap(solver_url, page_url, sitekey, timeout):
    s = time.monotonic(); event("solve_turnstile_start", solver_url=solver_url, page_url=page_url, sitekey=sitekey, timeout=timeout)
    token = orig_solve(solver_url, page_url, sitekey, timeout)
    event("solve_turnstile_end", duration=round(time.monotonic()-s, 3), token_len=len(token or ""))
    return token

def import_wrap(driver, session, base_url):
    s = time.monotonic(); event("import_session_cookies_start", base_url=base_url)
    out = orig_import(driver, session, base_url)
    event("import_session_cookies_end", duration=round(time.monotonic()-s, 3), imported=out)
    return out

# Only log non-loop or milestone states to avoid huge noise.
def state_wrap(driver, stage):
    s = time.monotonic()
    out = orig_state(driver, stage)
    dur = round(time.monotonic()-s, 3)
    if stage != "cf-wait":
        event("state", stage=stage, duration=dur, state=slim_state(out))
    return out

glb.build_driver = build_driver_wrap
glb.wait_document_ready = wait_doc_wrap
glb.wait_not_cloudflare = wait_cf_wrap
glb.click_next_powergam = click_wrap
glb.unlock_final_gate = unlock_wrap
glb.solve_turnstile = solve_wrap
glb.import_session_cookies = import_wrap
glb.state = state_wrap

start = time.monotonic()
try:
    event("run_start", url=URL, direct_powergam=glb.GPLINKS_DIRECT_POWERGAM)
    result = glb.run(URL, 360, "http://127.0.0.1:5000")
    event("run_end", duration=round(time.monotonic()-start, 3), status=result.get("status"), stage=result.get("stage"), final_url=result.get("final_url"), bypass_url=result.get("bypass_url"), waited_seconds=result.get("waited_seconds"))
except Exception as exc:
    result = {"status": 0, "stage": "profile-exception", "message": str(exc)}
    event("run_exception", duration=round(time.monotonic()-start, 3), error=str(exc)[:1000])
finally:
    OUT.write_text(json.dumps({"url": URL, "events": events, "result": result}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"raw_out": str(OUT), "result": result}, ensure_ascii=False), flush=True)
    raise SystemExit(0 if result.get("status") == 1 else 1)
