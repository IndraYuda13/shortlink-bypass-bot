#!/usr/bin/env python3
from __future__ import annotations
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from cuty_live_browser import CdpPage, detect_chrome_path, solve_turnstile, state
OUT=Path('artifacts/active/cuty-vhit/cuty_fetch_probe_latest.json')

def ev(page, expr): return (page.eval(expr).get('value'))

def snap(page, stage):
    return {"stage":stage, **state(page), "fetchLog": ev(page,"window.__fetchLog||[]"), "localStorage": ev(page,"Object.fromEntries(Object.keys(localStorage).map(k=>[k,localStorage.getItem(k)]))")}

INJECT = r"""
(() => {
  window.__fetchLog = [];
  const origFetch = window.fetch;
  window.fetch = async function(input, init) {
    const url = (typeof input === 'string') ? input : (input && input.url);
    const method = (init && init.method) || (input && input.method) || 'GET';
    let body = init && init.body;
    try { if (body && typeof body !== 'string') body = body.toString(); } catch(e) {}
    const item = {t: Date.now(), url, method, body: body || '', reqHeaders: init && init.headers || null};
    try {
      const res = await origFetch.apply(this, arguments);
      item.status = res.status;
      item.responseUrl = res.url;
      try { item.text = (await res.clone().text()).slice(0, 1200); } catch(e) { item.textError = String(e); }
      window.__fetchLog.push(item);
      return res;
    } catch(e) {
      item.error = String(e);
      window.__fetchLog.push(item);
      throw e;
    }
  };
})();
"""

def main():
    started=time.time(); timeline=[]
    with CdpPage(detect_chrome_path(),260) as page:
        page.send('Page.addScriptToEvaluateOnNewDocument', {'source': INJECT})
        page.navigate('https://cuty.io/AfaX6jx'); page.drain(28); timeline.append(snap(page,'entry'))
        page.eval("document.querySelector('#submit-button')?.click()"); page.drain(10); timeline.append(snap(page,'captcha'))
        sitekey=timeline[-1].get('site')
        token=solve_turnstile('http://127.0.0.1:5000', timeline[-1].get('href'), sitekey, 120)
        page.eval("""(()=>{const token=%s; const f=document.querySelector('form'); let ta=document.querySelector('[name=\"cf-turnstile-response\"]'); if(!ta){ta=document.createElement('textarea'); ta.name='cf-turnstile-response'; ta.style.display='none'; f.appendChild(ta)} ta.value=token; let b=document.querySelector('#submit-button'); if(b)b.disabled=false; b?.click(); return true;})()""" % json.dumps(token))
        page.drain(18); timeline.append(snap(page,'last-initial'))
        page.drain(12); timeline.append(snap(page,'last-after-wait'))
        page.eval("document.querySelector('#submit-form')?.submit()"); page.drain(18); timeline.append(snap(page,'final'))
    payload={'waited_seconds':round(time.time()-started,1),'timeline':timeline}
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False))
    print(json.dumps({'out':str(OUT),'waited_seconds':payload['waited_seconds'],'final':timeline[-1].get('href')}))
if __name__=='__main__': main()
