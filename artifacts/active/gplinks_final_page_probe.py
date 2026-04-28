#!/usr/bin/env python3
from __future__ import annotations
import json, time, pathlib, sys, re, base64
from urllib.parse import urljoin
from curl_cffi import requests as curl_requests
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import undetected_chromedriver as uc
import xut_live_browser as xut

OUTDIR=ROOT/'artifacts/active/gplinks-final-probe'
OUTDIR.mkdir(parents=True, exist_ok=True)

def b64d(x):
    try: return base64.b64decode(x+'='*((4-len(x)%4)%4)).decode()
    except Exception: return x

def build_driver():
    opts=uc.ChromeOptions(); opts.binary_location=xut.CHROME_PATH
    for a in [
        '--no-sandbox','--disable-dev-shm-usage','--window-size=1365,900',
        '--disable-blink-features=AutomationControlled','--lang=en-US,en;q=0.9',
        '--disable-features=PrivacySandboxAdsAPIs,OptimizationHints,AutomationControlled',
        '--no-first-run','--no-default-browser-check',
    ]: opts.add_argument(a)
    opts.page_load_strategy='eager'
    d=uc.Chrome(options=opts,use_subprocess=True,headless=False,version_main=xut.detect_chrome_major())
    d.set_page_load_timeout(90)
    return d

def js(d, expr):
    return d.execute_script('return '+expr)

def state(d,label):
    data=d.execute_script(r"""
    const btn=document.querySelector('#captchaButton');
    return {
      label: arguments[0], href: location.href, title: document.title,
      text: document.body ? document.body.innerText.slice(0,1600) : '',
      cookies: document.cookie,
      localStorage: Object.fromEntries(Object.entries(localStorage||{})),
      sessionStorage: Object.fromEntries(Object.entries(sessionStorage||{})),
      button: btn ? {text:(btn.innerText||btn.textContent||'').trim(), href:btn.href||'', cls:btn.className, disabled:btn.disabled||btn.classList.contains('disabled'), attrs:Object.fromEntries([...btn.attributes].map(a=>[a.name,a.value]))} : null,
      scripts: [...document.scripts].map(s=>s.src||('inline:'+s.textContent.slice(0,120))).slice(-40),
      vars: {
        app_vars: window.app_vars || null,
        appVars: window.appVars || null,
        countdown: window.countdown || null,
        timer: window.timer || null,
        uid: window.uid || null,
        alias: window.alias || null,
        decoded: window.decoded || null,
        __gptEvents: window.__gptEvents || [],
        googletag: !!window.googletag,
        adsbygoogle: !!window.adsbygoogle,
      }
    };
    """, label)
    return data

def click_continue(d):
    return d.execute_script(r"""
    const c=[...document.querySelectorAll('a,button,input[type=submit]')].map((el,i)=>({i,el,t:(el.innerText||el.value||el.textContent||'').trim(),disabled:el.disabled||el.classList.contains('disabled')}));
    const target=c.find(x=>/continue|verify/i.test(x.t)&&!x.disabled) || c.find(x=>/continue|verify/i.test(x.t));
    if(!target) return {clicked:false,candidates:c.slice(0,20).map(x=>({i:x.i,t:x.t,disabled:x.disabled,tag:x.el.tagName,id:x.el.id,cls:x.el.className}))};
    target.el.scrollIntoView({block:'center'}); target.el.click(); return {clicked:true,text:target.t,idx:target.i};
    """)

def main():
    out={'started':time.time(),'states':[]}
    sess=curl_requests.Session(impersonate='chrome136')
    entry=sess.get('https://gplinks.co/YVTC',allow_redirects=False,timeout=40)
    power=entry.headers.get('location')
    out['entry']={'status':entry.status_code,'location':power,'cookies':sess.cookies.get_dict()}
    if power and '?' in power:
        q=dict(part.split('=',1) for part in power.split('?',1)[1].split('&') if '=' in part)
        out['decoded']={k:b64d(v) for k,v in q.items()}
    d=build_driver()
    try:
        d.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': r"""
        window.__gptEvents=[];
        window.__nativeSubmits=[];
        const oldSubmit=HTMLFormElement.prototype.submit;
        HTMLFormElement.prototype.submit=function(){try{window.__nativeSubmits.push({t:Date.now(), action:this.action, data:new URLSearchParams(new FormData(this)).toString(), href:location.href});}catch(e){} return oldSubmit.apply(this,arguments)};
        setInterval(()=>{try{if(window.googletag&&googletag.pubads&&!window.__gptHooked){window.__gptHooked=1; const pub=googletag.pubads(); ['slotRequested','slotResponseReceived','slotRenderEnded','impressionViewable','rewardedSlotReady','rewardedSlotClosed','rewardedSlotGranted','rewardedSlotVideoCompleted'].forEach(ev=>pub.addEventListener(ev,e=>{window.__gptEvents.push({t:Date.now(),type:ev,slot:e.slot&&e.slot.getAdUnitPath&&e.slot.getAdUnitPath(),empty:e.isEmpty}); if(ev==='rewardedSlotReady'){try{e.makeRewardedVisible(); window.__gptEvents.push({t:Date.now(),type:'makeRewardedVisible-called'});}catch(x){window.__gptEvents.push({t:Date.now(),type:'makeRewardedVisible-error',error:String(x)});}}}));}}catch(e){}},100);
        """})
        d.get(power)
        out['states'].append(state(d,'power-entry'))
        for i in range(1,5):
            time.sleep(12)
            out['states'].append(state(d,f'before-click-{i}'))
            out.setdefault('clicks',[]).append(click_continue(d))
            time.sleep(5)
            out['states'].append(state(d,f'after-click-{i}'))
            if 'gplinks.co/' in d.current_url and 'pid=' in d.current_url: break
        # final page deep inspection
        time.sleep(20)
        out['states'].append(state(d,'final-wait20'))
        html=d.page_source
        (OUTDIR/'final_page.html').write_text(html,encoding='utf-8')
        out['html_len']=len(html)
        out['script_srcs']=re.findall(r'<script[^>]+src=["\']([^"\']+)', html, flags=re.I)
        # try forced enabling as a diagnostic only
        out['force_click']=d.execute_script(r"""
        const b=document.querySelector('#captchaButton'); if(!b) return {found:false};
        b.classList.remove('disabled'); b.removeAttribute('disabled'); b.style.pointerEvents='auto';
        const before={text:b.innerText,href:b.href,cls:b.className};
        b.click(); return {found:true,before,afterHref:location.href};
        """)
        time.sleep(8)
        out['states'].append(state(d,'after-force-click'))
    finally:
        path=OUTDIR/f'gplinks_final_page_probe_{int(time.time())}.json'
        path.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
        print(path)
        try: d.quit()
        except Exception: pass
if __name__=='__main__': main()
