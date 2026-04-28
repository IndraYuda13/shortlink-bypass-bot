import json, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from bs4 import BeautifulSoup
try:
    from curl_cffi import requests as creq
except Exception as e:
    print(json.dumps({'error':'curl_cffi import failed','detail':repr(e)})); raise SystemExit(0)
from engine import ShortlinkBypassEngine
from supported_sites import SUPPORTED_SITES
samples=[s for s in SUPPORTED_SITES if s.host in {'oii.la','tpi.li','aii.sh'}]
for s in samples:
    res=ShortlinkBypassEngine(timeout=30).analyze(s.sample_url)
    out={'host':s.host,'target':res.bypass_url}
    if not res.bypass_url:
        print(json.dumps(out)); continue
    sess=creq.Session(impersonate='chrome136')
    sess.headers.update({'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'})
    try:
        t=time.perf_counter(); r=sess.get(res.bypass_url, timeout=30, allow_redirects=False); dt=time.perf_counter()-t
        soup=BeautifulSoup(r.text,'html.parser')
        out.update({'status':r.status_code,'location':r.headers.get('location'),'elapsed_sec':round(dt,3),'title':(soup.title.string.strip() if soup.title and soup.title.string else None),'server':r.headers.get('server'),'cf_mitigated':r.headers.get('cf-mitigated'),'len':len(r.text)})
    except Exception as e:
        out['error']=repr(e)
    print(json.dumps(out, ensure_ascii=False))
