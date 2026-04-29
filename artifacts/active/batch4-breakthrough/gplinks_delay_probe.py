#!/usr/bin/env python3
from __future__ import annotations

import base64, json, time, sys
from urllib.parse import parse_qs, urlparse
from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests

URL='https://gplinks.co/YVTC'
HEADERS={
 'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
 'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
 'Accept-Language':'en-US,en;q=0.9',
 'Upgrade-Insecure-Requests':'1',
}

def b64(v):
 try: return base64.b64decode(v + '='*((4-len(v)%4)%4)).decode()
 except Exception: return v

def forms(html, page):
 soup=BeautifulSoup(html,'html.parser')
 out=[]
 for f in soup.find_all('form'):
  payload={}
  for item in f.select('input,textarea,select'):
   n=item.get('name')
   if n: payload[n]=item.get('value') or ''
  out.append({'id':f.get('id') or '', 'action':f.get('action') or page, 'method':(f.get('method') or 'GET').upper(), 'payload':payload})
 return out

def run(delay=16.2, imps=0):
 t0=time.time(); tl=[]
 s=curl_requests.Session(impersonate='chrome136')
 entry=s.get(URL,headers=HEADERS,allow_redirects=False,timeout=40)
 power=entry.headers.get('location') or ''
 tl.append({'t':round(time.time()-t0,3),'stage':'entry','status':entry.status_code,'url':entry.url,'loc':power,'cookies':s.cookies.get_dict()})
 q=parse_qs(urlparse(power).query)
 raw={k:(q.get(k) or [''])[0] for k in ['lid','pid','vid','pages']}
 dec={k:b64(v) for k,v in raw.items()}
 target=f"https://gplinks.co/{dec['lid']}?pid={dec['pid']}&vid={raw['vid']}"
 p=s.get(power,headers={**HEADERS,'Referer':URL},allow_redirects=True,timeout=40)
 tl.append({'t':round(time.time()-t0,3),'stage':'power-get','status':p.status_code,'url':p.url,'forms':forms(p.text,p.url)[:1],'cookies':s.cookies.get_dict()})
 action=(forms(p.text,p.url)[:1] or [{'action':power}])[0]['action'] or power
 # set first party JS cookies exact enough for PowerGam path
 host=urlparse(p.url).hostname or 'powergam.online'
 for name,val in {'lid':dec['lid'],'pid':dec['pid'],'pages':dec['pages'],'vid':raw['vid'],'step_count':'0','imps':str(imps),'adexp':'1'}.items():
  try: s.cookies.set(name,val,domain=host,path='/')
  except Exception: s.cookies.set(name,val)
 for step in range(1,4):
  if delay and step > 1: time.sleep(delay)
  # also wait before first submit to test full timer realism
  if delay and step == 1: time.sleep(delay)
  next_target=target if step==3 else 'https://powergam.online'
  payload={'form_name':'ads-track-data','step_id':str(step),'ad_impressions':str(imps),'visitor_id':raw['vid'],'next_target':next_target}
  headers={**HEADERS,'Origin':'https://powergam.online','Referer':p.url,'Content-Type':'application/x-www-form-urlencoded'}
  r=s.post(action,data=payload,headers=headers,allow_redirects=False,timeout=40)
  tl.append({'t':round(time.time()-t0,3),'stage':f'post-{step}','status':r.status_code,'url':r.url,'loc':r.headers.get('location'),'payload':payload,'cookies':s.cookies.get_dict()})
  if r.headers.get('location') and step < 3:
   f=s.get(r.headers['location'],headers={**HEADERS,'Referer':p.url},allow_redirects=True,timeout=40)
   tl.append({'t':round(time.time()-t0,3),'stage':f'follow-{step}','status':f.status_code,'url':f.url,'text':f.text[:100]})
 cand=s.get(target,headers={**HEADERS,'Referer':p.url},allow_redirects=False,timeout=40)
 tl.append({'t':round(time.time()-t0,3),'stage':'candidate-direct','status':cand.status_code,'url':cand.url,'loc':cand.headers.get('location'),'text':cand.text[:200],'cookies':s.cookies.get_dict()})
 return {'delay':delay,'imps':imps,'target':target,'raw':raw,'decoded':dec,'timeline':tl,'elapsed':round(time.time()-t0,2)}

if __name__ == '__main__':
 delay=float(sys.argv[1]) if len(sys.argv)>1 else 16.2
 imps=int(sys.argv[2]) if len(sys.argv)>2 else 0
 print(json.dumps(run(delay, imps), ensure_ascii=False, indent=2))
