#!/usr/bin/env python3
from __future__ import annotations
import json, re, sys, time
from pathlib import Path
from urllib.parse import urljoin, urlparse
ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests
from cuty_live_browser import solve_turnstile

BASE_HEADERS={
 'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/147.0.0.0 Safari/537.36',
 'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
 'Accept-Language':'en-US,en;q=0.9','Upgrade-Insecure-Requests':'1'}
INTERNAL={'cuty.io','www.cuty.io','cuttlinks.com','www.cuttlinks.com'}

def form(html, selector='form'):
    soup=BeautifulSoup(html or '', 'html.parser'); f=soup.select_one(selector) or soup.find('form')
    if not f: return {'found':False,'data':{}}
    data={}
    for i in f.select('input,textarea,select'):
        n=i.get('name')
        if n: data[n]=i.get('value') or ''
    return {'found':True,'id':f.get('id') or '', 'action':f.get('action') or '', 'data':data}

def sitekey(html):
    soup=BeautifulSoup(html or '', 'html.parser'); el=soup.select_one('.cf-turnstile[data-sitekey]')
    return el.get('data-sitekey') if el else None

def post_form(s, action, data, referer, timeout=40):
    return s.post(action,data=data,headers={**BASE_HEADERS,'Origin':'null','Referer':referer,'Content-Type':'application/x-www-form-urlencoded'},allow_redirects=True,timeout=timeout)

def scripts(html):
    soup=BeautifulSoup(html or '', 'html.parser')
    return [sc.get('src') for sc in soup.find_all('script',src=True)]

def run(url, do_vhit=True):
    started=time.time(); tl=[]; s=curl_requests.Session(impersonate='chrome136')
    e=s.get(url,headers=BASE_HEADERS,allow_redirects=False,timeout=30); tl.append({'stage':'entry','status':e.status_code,'url':e.url,'loc':e.headers.get('location')})
    a=s.get(e.headers.get('location'),headers={**BASE_HEADERS,'Referer':url},allow_redirects=False,timeout=30); tl.append({'stage':'auth','status':a.status_code,'url':a.url,'loc':a.headers.get('location')})
    p=s.get(a.headers.get('location'),headers={**BASE_HEADERS,'Referer':a.url},timeout=30); tl.append({'stage':'first','status':p.status_code,'url':p.url,'scripts':scripts(p.text)})
    f=form(p.text,'form#free-submit-form')
    p2=post_form(s,urljoin(p.url,f['action']),f['data'],p.url); tl.append({'stage':'captcha','status':p2.status_code,'url':p2.url,'sitekey':sitekey(p2.text),'scripts':scripts(p2.text)})
    sk=sitekey(p2.text); token=solve_turnstile('http://127.0.0.1:5000',p2.url,sk,140)
    f2=form(p2.text,'form#free-submit-form'); d=dict(f2['data']); d['cf-turnstile-response']=token
    p3=post_form(s,urljoin(p2.url,f2['action']),d,p2.url,timeout=60); tl.append({'stage':'last','status':p3.status_code,'url':p3.url,'scripts':scripts(p3.text)})
    if do_vhit:
        # emulate the two server-visible VHit calls observed in CDP fetch log.
        vh=s.post('https://fp.vhit.io/',headers={'User-Agent':BASE_HEADERS['User-Agent'],'Accept':'*/*','Origin':'https://cuttlinks.com','Referer':p3.url},timeout=30)
        tl.append({'stage':'vhit-fp','status':vh.status_code,'url':vh.url,'text':vh.text[:250]})
        ar=s.get('https://vhit.io/api/request?f=c05f1bfbacf97684fd9fc9e742760250',headers={'User-Agent':BASE_HEADERS['User-Agent'],'Accept':'application/json','Content-Type':'application/json','Origin':'https://cuttlinks.com','Referer':p3.url},timeout=30)
        tl.append({'stage':'vhit-request','status':ar.status_code,'url':ar.url,'text':ar.text[:250]})
    time.sleep(9)
    gf=form(p3.text,'form#submit-form'); final=post_form(s,urljoin(p3.url,gf['action']),gf['data'],p3.url,timeout=60)
    tl.append({'stage':'final','status':final.status_code,'url':final.url,'loc':final.headers.get('location'),'text':final.text[:120]})
    host=urlparse(final.url).netloc.lower(); ok=host and host not in INTERNAL
    return {'status':1 if ok else 0,'stage':'http-final','final_url':final.url,'bypass_url':final.url if ok else None,'sitekey':sk,'timeline':tl,'waited_seconds':round(time.time()-started,1)}

if __name__=='__main__':
    payload=run(sys.argv[1] if len(sys.argv)>1 else 'https://cuty.io/AfaX6jx', '--no-vhit' not in sys.argv)
    print(json.dumps(payload,ensure_ascii=False))
    raise SystemExit(0 if payload.get('status') else 1)
