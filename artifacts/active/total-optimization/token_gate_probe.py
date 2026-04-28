import json, sys, time
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from bs4 import BeautifulSoup
import requests
from engine import ShortlinkBypassEngine, DEFAULT_HEADERS
from supported_sites import SUPPORTED_SITES

samples=[s for s in SUPPORTED_SITES if s.host in {'oii.la','tpi.li','aii.sh'}]
for s in samples:
    eng=ShortlinkBypassEngine(timeout=30)
    t=time.perf_counter(); res=eng.analyze(s.sample_url); analyze_dt=time.perf_counter()-t
    facts=res.facts
    hidden=facts.get('hidden_inputs') or {}
    form_action=facts.get('form_action')
    out={'host':s.host,'sample_url':s.sample_url,'expected_final':s.expected_final,'engine_status':res.status,'engine_message':res.message,'engine_bypass_url':res.bypass_url,'engine_elapsed_sec':round(analyze_dt,3),'form_action':form_action,'captcha_type':facts.get('captcha_type'),'counter_value':facts.get('counter_value'),'sitekey':facts.get('sitekey')}
    # POST hidden fields without any captcha token.
    if form_action:
        try:
            t=time.perf_counter(); r=eng.session.post(form_action, data=hidden, headers={'Referer':s.sample_url, **DEFAULT_HEADERS}, timeout=30, allow_redirects=False); dt=time.perf_counter()-t
            out.update({'post_no_captcha_status':r.status_code,'post_no_captcha_location':r.headers.get('location'),'post_no_captcha_elapsed_sec':round(dt,3),'post_no_captcha_title':(BeautifulSoup(r.text,'html.parser').title.string.strip() if BeautifulSoup(r.text,'html.parser').title and BeautifulSoup(r.text,'html.parser').title.string else None)})
        except Exception as e:
            out['post_no_captcha_error']=repr(e)
    # Probe extracted target lightly without following redirects.
    if res.bypass_url:
        try:
            t=time.perf_counter(); tr=requests.get(res.bypass_url, headers=DEFAULT_HEADERS, timeout=30, allow_redirects=False); dt=time.perf_counter()-t
            out.update({'target_get_status':tr.status_code,'target_get_location':tr.headers.get('location'),'target_get_elapsed_sec':round(dt,3),'target_get_title':(BeautifulSoup(tr.text,'html.parser').title.string.strip() if BeautifulSoup(tr.text,'html.parser').title and BeautifulSoup(tr.text,'html.parser').title.string else None),'target_get_len':len(tr.text)})
        except Exception as e:
            out['target_get_error']=repr(e)
    print(json.dumps(out, ensure_ascii=False))
