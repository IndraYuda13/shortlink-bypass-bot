#!/usr/bin/env python3
from __future__ import annotations
import json, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
import gplinks_live_browser as glb
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
URL='https://gplinks.co/YVTC'
OUT=ROOT/'artifacts/active/total-optimization/gplinks-batch3-profile-selenium-raw.json'
events=[]; t0=time.monotonic()
def now(): return round(time.monotonic()-t0,3)
def ev(k,**d):
    item={'t':now(),'kind':k,**d}; events.append(item); print(json.dumps(item,ensure_ascii=False),flush=True)
def slim(st):
    st=st or {}; txt=st.get('text') or ''; btn=st.get('captchaButton') or {}
    return {'href':st.get('href'),'title':st.get('title'),'timerText':st.get('timerText'),'sitekey':st.get('sitekey'),'captchaInput':st.get('captchaInput'),'captchaButton':{'text':btn.get('text'),'href':btn.get('href'),'disabled':btn.get('disabled')} if btn else None,'text_head':txt[:120]}

def build_plain():
    s=time.monotonic(); ev('build_driver_start', mode='plain-selenium')
    opts=Options(); opts.binary_location=glb.CHROME_PATH
    for a in ['--no-sandbox','--disable-dev-shm-usage','--window-size=1365,900','--disable-blink-features=AutomationControlled','--lang=en-US,en;q=0.9','--disable-features=PrivacySandboxAdsAPIs,OptimizationHints,AutomationControlled','--no-first-run','--no-default-browser-check']:
        opts.add_argument(a)
    opts.page_load_strategy='eager'
    d=webdriver.Chrome(service=Service('/root/.local/share/undetected_chromedriver/undetected_chromedriver'), options=opts)
    d.set_page_load_timeout(90)
    ev('build_driver_end', duration=round(time.monotonic()-s,3))
    return d

orig_wait_doc=glb.wait_document_ready; orig_wait_cf=glb.wait_not_cloudflare; orig_click=glb.click_next_powergam; orig_unlock=glb.unlock_final_gate; orig_solve=glb.solve_turnstile; orig_state=glb.state

def wd(d,timeout=20,interval=0.5):
    s=time.monotonic(); ev('wait_document_ready_start', timeout=timeout, interval=interval, href=getattr(d,'current_url',None))
    out=orig_wait_doc(d,timeout,interval); ev('wait_document_ready_end', duration=round(time.monotonic()-s,3), state=slim(out)); return out

def wc(d,timeout):
    s=time.monotonic(); ev('wait_not_cloudflare_start', timeout=timeout)
    out=orig_wait_cf(d,timeout); ev('wait_not_cloudflare_end', duration=round(time.monotonic()-s,3), state=slim(out)); return out

def cl(d):
    s=time.monotonic(); out=orig_click(d); ev('click_next_powergam', duration=round(time.monotonic()-s,3), result=out); return out

def sol(*args):
    s=time.monotonic(); ev('solve_turnstile_start', sitekey=args[2] if len(args)>2 else None)
    out=orig_solve(*args); ev('solve_turnstile_end', duration=round(time.monotonic()-s,3), token_len=len(out or '')); return out

def un(d,solver_url,timeout_left):
    s=time.monotonic(); ev('unlock_final_gate_start', timeout_left=timeout_left)
    out=orig_unlock(d,solver_url,timeout_left); ev('unlock_final_gate_end', duration=round(time.monotonic()-s,3), final_href=out.get('final_href'), token_used=out.get('token_used'), sitekey=out.get('sitekey')); return out

def st(d,stage):
    out=orig_state(d,stage)
    if stage in {'entry','power-entry','loop','candidate','before-unlock','wait-final-href','after-unlock','final'}:
        ev('state', stage=stage, state=slim(out))
    return out

glb.build_driver=build_plain; glb.wait_document_ready=wd; glb.wait_not_cloudflare=wc; glb.click_next_powergam=cl; glb.unlock_final_gate=un; glb.solve_turnstile=sol; glb.state=st
start=time.monotonic(); result={}
try:
    ev('run_start', url=URL)
    result=glb.run(URL,360,'http://127.0.0.1:5000')
    ev('run_end', duration=round(time.monotonic()-start,3), status=result.get('status'), stage=result.get('stage'), final_url=result.get('final_url'), bypass_url=result.get('bypass_url'), waited_seconds=result.get('waited_seconds'))
except Exception as e:
    result={'status':0,'stage':'profile-exception','message':str(e)}; ev('run_exception', duration=round(time.monotonic()-start,3), error=str(e)[:1000])
finally:
    OUT.write_text(json.dumps({'url':URL,'events':events,'result':result},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'raw_out':str(OUT),'result':result},ensure_ascii=False),flush=True)
    raise SystemExit(0 if result.get('status')==1 else 1)
