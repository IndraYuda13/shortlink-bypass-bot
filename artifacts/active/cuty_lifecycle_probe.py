#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cuty_live_browser import CdpPage, detect_chrome_path, solve_turnstile, state

OUT = Path('artifacts/active/cuty-vhit/cuty_lifecycle_probe_latest.json')


def eval_value(page: CdpPage, expr: str):
    raw = page.eval(expr)
    return raw.get('value')


def snapshot(page: CdpPage, stage: str) -> dict:
    perf = eval_value(page, """performance.getEntriesByType('resource').map(e => ({name:e.name, initiatorType:e.initiatorType, duration:Math.round(e.duration)}))""") or []
    storage = eval_value(page, """({
      localStorage: Object.fromEntries(Object.keys(localStorage).map(k => [k, localStorage.getItem(k)])),
      sessionStorage: Object.fromEntries(Object.keys(sessionStorage).map(k => [k, sessionStorage.getItem(k)])),
      scripts: [...document.scripts].map(s => s.src).filter(Boolean),
      cookies: document.cookie,
      hiddenInputs: [...document.querySelectorAll('input[type=hidden], textarea')].map(i => ({name:i.name, value:(i.value||'').slice(0,160)})),
    })""") or {}
    return {"stage": stage, **state(page), "perf": perf, **storage}


def main():
    started = time.time()
    timeline = []
    with CdpPage(detect_chrome_path(), 260) as page:
        page.navigate('https://cuty.io/AfaX6jx')
        page.drain(28)
        timeline.append(snapshot(page, 'entry'))

        page.eval("document.querySelector('#submit-button')?.click()")
        page.drain(10)
        captcha_state = snapshot(page, 'captcha')
        timeline.append(captcha_state)
        sitekey = captcha_state.get('site')
        token = solve_turnstile('http://127.0.0.1:5000', captcha_state.get('href') or 'https://cuttlinks.com/AfaX6jx', sitekey, 120)
        page.eval("""(()=>{const token=%s; const f=document.querySelector('form'); if(!f) return false; let ta=document.querySelector('[name=\"cf-turnstile-response\"]'); if(!ta){ta=document.createElement('textarea'); ta.name='cf-turnstile-response'; ta.style.display='none'; f.appendChild(ta)} ta.value=token; let b=document.querySelector('#submit-button'); if(b)b.disabled=false; return true;})()""" % json.dumps(token))
        page.eval("document.querySelector('#submit-button')?.click()")
        page.drain(16)
        timeline.append(snapshot(page, 'last-initial'))
        page.drain(12)
        timeline.append(snapshot(page, 'last-after-wait'))
        page.eval("document.querySelector('#submit-form')?.submit()")
        page.drain(20)
        timeline.append(snapshot(page, 'final'))
    payload = {"waited_seconds": round(time.time()-started,1), "timeline": timeline}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(json.dumps({"out": str(OUT), "waited_seconds": payload['waited_seconds'], "final": timeline[-1].get('href')}, ensure_ascii=False))

if __name__ == '__main__':
    main()
