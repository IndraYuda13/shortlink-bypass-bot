#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from curl_cffi import requests as curl_requests
import undetected_chromedriver as uc

from cuty_live_browser import solve_turnstile
from gplinks_http_fast import _post_final_gate as post_gplinks_final_gate_http

PROJECT_ROOT = Path(__file__).resolve().parent
CHROME_PATH = "/usr/bin/google-chrome" if Path("/usr/bin/google-chrome").exists() else "/usr/bin/google-chrome-stable"
GPLINKS_HOSTS = {"gplinks.co", "www.gplinks.co"}
POWERGAM_HOSTS = {"powergam.online", "www.powergam.online"}
GPLINKS_DIRECT_POWERGAM = os.getenv("SHORTLINK_BYPASS_GPLINKS_DIRECT_POWERGAM", "0").strip().lower() in {"1", "true", "yes", "on"}
GPLINKS_NAVIGATE_FINAL = os.getenv("SHORTLINK_BYPASS_GPLINKS_NAVIGATE_FINAL", "0").strip().lower() in {"1", "true", "yes", "on"}
GPLINKS_EARLY_CONTINUE_SECONDS = max(0, int(os.getenv("SHORTLINK_BYPASS_GPLINKS_EARLY_CONTINUE_SECONDS", "0") or "0"))
GPLINKS_HTTP_FINAL_HANDOFF = os.getenv("SHORTLINK_BYPASS_GPLINKS_HTTP_FINAL_HANDOFF", "0").strip().lower() in {"1", "true", "yes", "on"}


def detect_chrome_major() -> int | None:
    try:
        output = subprocess.check_output([CHROME_PATH, "--version"], text=True, timeout=10)
    except Exception:
        return None
    match = re.search(r"(\d+)\.", output)
    return int(match.group(1)) if match else None


def build_driver():
    opts = uc.ChromeOptions()
    opts.binary_location = CHROME_PATH
    for arg in [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--window-size=1365,900",
        "--disable-blink-features=AutomationControlled",
        "--lang=en-US,en;q=0.9",
        "--disable-features=PrivacySandboxAdsAPIs,OptimizationHints,AutomationControlled",
        "--disable-background-timer-throttling",
        "--disable-renderer-backgrounding",
        "--disable-backgrounding-occluded-windows",
        "--no-first-run",
        "--no-default-browser-check",
    ]:
        opts.add_argument(arg)
    opts.page_load_strategy = "eager"
    driver = uc.Chrome(options=opts, use_subprocess=True, headless=False, version_main=detect_chrome_major())
    driver.set_page_load_timeout(90)
    return driver


def _b64_decode(value: str) -> str:
    try:
        return base64.b64decode(value + "=" * ((4 - len(value) % 4) % 4)).decode()
    except Exception:
        return value


def decoded_power_query(power_url: str) -> dict[str, str | None]:
    query = parse_qs(urlparse(power_url).query)
    return {key: _b64_decode((query.get(key) or [""])[0]) or None for key in ["lid", "pid", "vid", "pages"]}


def js(driver, script: str, *args):
    return driver.execute_script(script, *args)


def install_gpt_lifecycle_probe(driver) -> dict:
    return js(
        driver,
        r"""
        window.__gplinks_gpt_lifecycle = window.__gplinks_gpt_lifecycle || [];
        window.__gplinks_gpt_probe_installed = window.__gplinks_gpt_probe_installed || false;
        const eventNames = ['slotRequested','slotResponseReceived','slotRenderEnded','impressionViewable','rewardedSlotReady','rewardedSlotClosed','rewardedSlotGranted','rewardedSlotVideoCompleted'];
        function safeSlotId(ev){ try { return ev && ev.slot && ev.slot.getSlotElementId ? ev.slot.getSlotElementId() : null; } catch(e) { return null; } }
        function record(name, ev){
          try {
            window.__gplinks_gpt_lifecycle.push({
              name,
              ts: Date.now(),
              href: location.href,
              slot: safeSlotId(ev),
              size: ev && ev.size ? String(ev.size) : null,
              isEmpty: ev && typeof ev.isEmpty !== 'undefined' ? !!ev.isEmpty : null,
              payloadKeys: ev ? Object.keys(ev).slice(0, 12) : []
            });
          } catch(e) {}
        }
        window.__gplinks_gpt_record = record;
        if (!window.__gplinks_gpt_probe_installed) {
          window.__gplinks_gpt_probe_installed = true;
          const install = () => {
            try {
              if (!window.googletag || !googletag.pubads) return false;
              const pubads = googletag.pubads();
              eventNames.forEach(name => { try { pubads.addEventListener(name, ev => record(name, ev)); } catch(e) {} });
              record('probe-installed', null);
              return true;
            } catch(e) { return false; }
          };
          window.googletag = window.googletag || {cmd: []};
          try { window.googletag.cmd = window.googletag.cmd || []; window.googletag.cmd.push(install); } catch(e) {}
          install();
        }
        return {installed: !!window.__gplinks_gpt_probe_installed, count: window.__gplinks_gpt_lifecycle.length};
        """,
    ) or {}


def collect_gpt_lifecycle_events(driver, stage: str) -> dict:
    try:
        payload = js(
            driver,
            r"""
            const events = (window.__gplinks_gpt_lifecycle || []).slice(-80);
            const counts = {};
            for (const ev of events) counts[ev.name] = (counts[ev.name] || 0) + 1;
            const resources = performance.getEntriesByType('resource').map(r => r.name).filter(name =>
              name.includes('securepubads.g.doubleclick.net') || name.includes('googlesyndication.com') || name.includes('doubleclick.net') || name.includes('pagead2.googlesyndication.com')
            ).slice(-40);
            return {
              stage: arguments[0],
              gpt_lifecycle: events,
              gpt_lifecycle_counts: counts,
              gpt_resource_hints: resources,
              googletag_present: !!window.googletag,
              installed: !!window.__gplinks_gpt_probe_installed
            };
            """,
            stage,
        )
        return payload or {"stage": stage, "gpt_lifecycle": [], "gpt_lifecycle_counts": {}, "gpt_resource_hints": []}
    except Exception as exc:
        return {"stage": stage, "gpt_lifecycle_error": str(exc)[:240], "gpt_lifecycle": [], "gpt_lifecycle_counts": {}, "gpt_resource_hints": []}


NETWORK_LEDGER_RECORDER_SCRIPT = r"""
(() => {
  window.__gplinks_network_ledger = window.__gplinks_network_ledger || [];
  if (!window.__gplinks_network_ledger_installed) {
    window.__gplinks_network_ledger_installed = true;
    let seq = window.__gplinks_network_ledger_seq || 0;
    const preview = value => {
      try {
        if (value == null) return null;
        if (typeof value === 'string') return value.slice(0, 1200);
        if (value instanceof URLSearchParams) return value.toString().slice(0, 1200);
        if (value instanceof FormData) return new URLSearchParams(value).toString().slice(0, 1200);
        return String(value).slice(0, 1200);
      } catch(e) { return '[unserializable]'; }
    };
    const storageDump = store => {
      const out = {};
      try { for (let i=0; i<store.length; i++) { const k = store.key(i); out[k] = store.getItem(k); } } catch(e) {}
      return out;
    };
    const record = (kind, data) => {
      try {
        window.__gplinks_network_ledger_seq = ++seq;
        window.__gplinks_network_ledger.push(Object.assign({
          kind,
          seq,
          ts: Date.now(),
          href: location.href,
          cookie_snapshot: document.cookie || '',
          local_storage: storageDump(localStorage),
          session_storage: storageDump(sessionStorage)
        }, data || {}));
      } catch(e) {}
    };
    window.__gplinks_record_network_ledger = record;

    const oldFetch = window.fetch;
    if (oldFetch) {
      window.fetch = function(input, init) {
        const url = typeof input === 'string' ? input : (input && input.url) || '';
        record('fetch', {url, method: (init && init.method) || (input && input.method) || 'GET', body: preview(init && init.body)});
        return oldFetch.apply(this, arguments).then(resp => { record('fetch-response', {url: resp.url || url, status: resp.status}); return resp; });
      };
    }

    const oldBeacon = navigator.sendBeacon;
    if (oldBeacon) {
      navigator.sendBeacon = function(url, data) {
        record('sendBeacon', {url: String(url || ''), body: preview(data)});
        return oldBeacon.apply(this, arguments);
      };
    }

    const oldOpen = XMLHttpRequest.prototype.open;
    const oldSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function(method, url) { this.__gplinks_method = method; this.__gplinks_url = url; return oldOpen.apply(this, arguments); };
    XMLHttpRequest.prototype.send = function(body) {
      record('xhr', {url: String(this.__gplinks_url || ''), method: String(this.__gplinks_method || 'GET'), body: preview(body)});
      this.addEventListener('loadend', () => record('xhr-response', {url: String(this.responseURL || this.__gplinks_url || ''), status: this.status}));
      return oldSend.apply(this, arguments);
    };

    const oldSubmit = HTMLFormElement.prototype.submit;
    HTMLFormElement.prototype.submit = function() {
      try { record('form-submit', {action: this.action || '', method: this.method || 'GET', data: preview(new FormData(this))}); } catch(e) {}
      return oldSubmit.apply(this, arguments);
    };
    document.addEventListener('submit', ev => {
      const f = ev.target;
      if (f && f.tagName === 'FORM') {
        try { record('form-submit-event', {action: f.action || '', method: f.method || 'GET', data: preview(new FormData(f))}); } catch(e) {}
      }
    }, true);

    try {
      const cookieDescriptor = Object.getOwnPropertyDescriptor(Document.prototype, 'cookie') || Object.getOwnPropertyDescriptor(HTMLDocument.prototype, 'cookie');
      if (cookieDescriptor && cookieDescriptor.configurable) {
        Object.defineProperty(document, 'cookie', {
          configurable: true,
          get: function(){ return cookieDescriptor.get.call(document); },
          set: function(value){ record('cookie-change', {value: preview(value), before: cookieDescriptor.get.call(document)}); return cookieDescriptor.set.call(document, value); }
        });
      }
    } catch(e) {}

    const wrapStorage = (name, store) => {
      try {
        const oldSet = store.setItem, oldRemove = store.removeItem, oldClear = store.clear;
        store.setItem = function(k, v){ record(name + '.setItem', {key: String(k), value: preview(v)}); return oldSet.apply(this, arguments); };
        store.removeItem = function(k){ record(name + '.removeItem', {key: String(k)}); return oldRemove.apply(this, arguments); };
        store.clear = function(){ record(name + '.clear', {}); return oldClear.apply(this, arguments); };
      } catch(e) {}
    };
    wrapStorage('localStorage', localStorage);
    wrapStorage('sessionStorage', sessionStorage);

    try {
      const po = new PerformanceObserver(list => {
        for (const r of list.getEntries()) {
          if ((r.name || '').match(/powergam|gplinks|doubleclick|googlesyndication|track|beacon|verify|pubnotify|b7510|bvtpk/i)) {
            record('resource', {url: r.name, initiatorType: r.initiatorType, duration: Math.round(r.duration), transferSize: r.transferSize || 0});
          }
        }
      });
      po.observe({entryTypes: ['resource']});
    } catch(e) {}

    record('network-ledger-installed', {});
  }
  return {installed: !!window.__gplinks_network_ledger_installed, count: window.__gplinks_network_ledger.length};
})();
"""


def install_pre_navigation_recorders(driver) -> dict:
    result = {"network": False}
    try:
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": NETWORK_LEDGER_RECORDER_SCRIPT})
        result["network"] = True
    except Exception as exc:
        result["network_error"] = str(exc)[:240]
    return result


def install_network_ledger_recorder(driver) -> dict:
    return js(driver, "return " + NETWORK_LEDGER_RECORDER_SCRIPT) or {}


def collect_network_ledger_events(driver, stage: str) -> dict:
    try:
        payload = js(
            driver,
            r"""
            const events = (window.__gplinks_network_ledger || []).slice(-160);
            const counts = {};
            for (const ev of events) counts[ev.kind] = (counts[ev.kind] || 0) + 1;
            const resources = performance.getEntriesByType('resource').map(r => ({name:r.name, initiatorType:r.initiatorType, duration:Math.round(r.duration), transferSize:r.transferSize || 0})).filter(r =>
              r.name.includes('powergam') || r.name.includes('gplinks') || r.name.includes('doubleclick') || r.name.includes('googlesyndication') || r.name.includes('ad') || r.name.includes('beacon') || r.name.includes('track') || r.name.includes('verify')
            ).slice(-80);
            return {stage: arguments[0], network_ledger: events, network_ledger_counts: counts, network_resources: resources, cookie_snapshot: document.cookie || '', installed: !!window.__gplinks_network_ledger_installed};
            """,
            stage,
        )
        return payload or {"stage": stage, "network_ledger": [], "network_ledger_counts": {}, "network_resources": [], "cookie_snapshot": ""}
    except Exception as exc:
        return {"stage": stage, "network_ledger_error": str(exc)[:240], "network_ledger": [], "network_ledger_counts": {}, "network_resources": [], "cookie_snapshot": ""}


def state(driver, stage: str) -> dict:
    data = js(
        driver,
        r"""
        const btn=document.querySelector('#captchaButton');
        return {
          stage: arguments[0],
          href: location.href,
          title: document.title,
          text: document.body ? document.body.innerText.slice(0,1200) : '',
          app_vars: window.app_vars || null,
          timerText: document.querySelector('#myTimer')?.textContent || null,
          captchaButton: btn ? {text:(btn.innerText||btn.textContent||'').trim(), href:btn.href||'', cls:btn.className, disabled:!!btn.disabled||btn.classList.contains('disabled')} : null,
          sitekey: document.querySelector('.cf-turnstile')?.dataset.sitekey || (window.app_vars && (window.app_vars.turnstile_site_key || window.app_vars.cloudflare_turnstile_site_key)) || null,
          captchaInput: !!document.querySelector('#captchaShortlink_captcha'),
          captchaImages: [...document.querySelectorAll('img')].map(img=>({id:img.id||'', cls:img.className||'', src:img.src||'', alt:img.alt||'', w:img.naturalWidth||img.width||0, h:img.naturalHeight||img.height||0})).slice(0,20),
          forms: [...document.forms].map(f=>({id:f.id, action:f.action, method:f.method, data:new URLSearchParams(new FormData(f)).toString()})),
          buttons: [...document.querySelectorAll('a,button,input[type=submit]')].slice(0,28).map(el=>({tag:el.tagName,id:el.id,text:(el.innerText||el.value||el.textContent||'').trim(),href:el.href||'',cls:el.className||'',disabled:!!el.disabled||el.classList.contains('disabled')}))
        };
        """,
        stage,
    )
    data = data or {"stage": stage}
    try:
        gpt = collect_gpt_lifecycle_events(driver, stage)
        data["gpt_lifecycle_counts"] = gpt.get("gpt_lifecycle_counts") or {}
        data["gpt_resource_hints"] = gpt.get("gpt_resource_hints") or []
        data["googletag_present"] = gpt.get("googletag_present")
        if gpt.get("gpt_lifecycle"):
            data["gpt_lifecycle_tail"] = gpt.get("gpt_lifecycle")[-8:]
    except Exception:
        pass
    try:
        ledger = collect_network_ledger_events(driver, stage)
        data["network_ledger_counts"] = ledger.get("network_ledger_counts") or {}
        data["network_ledger_tail"] = (ledger.get("network_ledger") or [])[-10:]
        data["network_resources_tail"] = (ledger.get("network_resources") or [])[-10:]
        data["cookie_snapshot"] = ledger.get("cookie_snapshot") or ""
    except Exception:
        pass
    return data


def close_extra_windows(driver):
    try:
        handles = driver.window_handles
        keep = handles[0]
        for h in handles[1:]:
            driver.switch_to.window(h)
            driver.close()
        driver.switch_to.window(keep)
    except Exception:
        pass


def import_session_cookies(driver, session, base_url: str) -> list[dict]:
    imported: list[dict] = []
    try:
        driver.get(base_url)
        wait_document_ready(driver, 8)
        for cookie in getattr(session.cookies, "jar", []):
            domain = (cookie.domain or "").lstrip(".")
            if "gplinks.co" not in domain:
                continue
            item = {"name": cookie.name, "value": cookie.value, "path": cookie.path or "/"}
            if domain:
                item["domain"] = domain
            try:
                driver.add_cookie(item)
                imported.append({"name": cookie.name, "domain": domain, "path": cookie.path or "/"})
            except Exception as exc:
                imported.append({"name": cookie.name, "domain": domain, "error": str(exc)[:160]})
    except Exception as exc:
        imported.append({"error": str(exc)[:240]})
    return imported


def click_next_powergam(driver) -> dict:
    result = js(
        driver,
        r"""
        const els=[...document.querySelectorAll('a,button,input[type=submit]')].map((el,i)=>({i,el,t:(el.innerText||el.value||el.textContent||'').trim(),disabled:!!el.disabled||el.classList.contains('disabled'),tag:el.tagName,id:el.id,cls:el.className||''}));
        const body=(document.body?.innerText||'');
        const waitMatch=body.match(/Please wait\s+(\d+)\s+Seconds/i);
        const waitLeft=waitMatch ? parseInt(waitMatch[1],10) : 0;
        const timerText = document.querySelector('#myTimer')?.textContent || null;
        const form = document.querySelector('form#adsForm');
        const formData = form ? new URLSearchParams(new FormData(form)).toString() : '';
        const diagnostics = {
          readyToGo: window.readyToGo,
          timerText,
          cookies: document.cookie || '',
          adsForm: formData,
          nextBtnVisible: !!document.querySelector('#GoNewxtDiv:not([style*="display: none"]) #NextBtn'),
          nextBtnHref: document.querySelector('#NextBtn')?.href || ''
        };
        const earlyContinueSeconds = Number(arguments[0] || 0);
        const continueAllowed = waitLeft <= earlyContinueSeconds;
        const verify=els.find(x=>/^verify$/i.test(x.t)&&!x.disabled);
        const cont=els.find(x=>/^continue$/i.test(x.t)&&!x.disabled);
        let target=verify || (continueAllowed ? cont : null) || els.find(x=>/verify/i.test(x.t)&&!x.disabled) || (continueAllowed ? els.find(x=>/continue/i.test(x.t)&&!x.disabled) : null);
        if(!target) return {clicked:false, waitLeft, diagnostics, candidates:els.slice(0,24).map(x=>({i:x.i,t:x.t,disabled:x.disabled,tag:x.tag,id:x.id,cls:x.cls}))};
        if(/continue/i.test(target.t)) {
          window.scrollTo(0, document.body.scrollHeight);
          document.dispatchEvent(new Event('scroll', {bubbles:true}));
        }
        target.el.scrollIntoView({block:'center'});
        target.el.click();
        return {clicked:true,text:target.t,idx:target.i,disabled:target.disabled,tag:target.tag,id:target.id,cls:target.cls,waitLeft,diagnostics};
        """,
        GPLINKS_EARLY_CONTINUE_SECONDS,
    )
    close_extra_windows(driver)
    if result:
        result["earlyContinueSeconds"] = GPLINKS_EARLY_CONTINUE_SECONDS
    return result or {}


def is_final_url(url: str | None) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = parsed.netloc.lower()
    if not host or host in GPLINKS_HOSTS or host in POWERGAM_HOSTS:
        return False
    if parsed.path.startswith("/link-error"):
        return False
    return True


def wait_not_cloudflare(driver, timeout: float) -> dict:
    end = time.time() + timeout
    last = state(driver, "cf-wait")
    while time.time() < end:
        last = state(driver, "cf-wait")
        txt = (last.get("text") or "").lower()
        if "performing security verification" not in txt and "just a moment" not in (last.get("title") or "").lower():
            return last
        time.sleep(2)
    return last


def wait_powergam_continue_ready(driver, timeout: float, interval: float = 0.25, early_continue_seconds: int = 0) -> dict:
    """Poll PowerGam readiness instead of sleeping coarse chunks.

    This does not bypass the timer. It only wakes the loop as soon as the page
    exposes a safe Continue condition or navigation state changes.
    """
    end = time.time() + max(0.1, timeout)
    last: dict = {}
    while time.time() < end:
        last = js(
            driver,
            r"""
            const body = document.body?.innerText || '';
            const waitMatch = body.match(/Please wait\s+(\d+)\s+Seconds/i);
            const waitLeft = waitMatch ? parseInt(waitMatch[1], 10) : 0;
            const buttons = [...document.querySelectorAll('a,button,input[type=submit]')].map(el => ({text:(el.innerText||el.value||el.textContent||'').trim(), disabled:!!el.disabled||el.classList.contains('disabled'), id:el.id, href:el.href||''}));
            const earlyContinueSeconds = Number(arguments[0] || 0);
            const continueReady = buttons.some(b => /^continue$/i.test(b.text) && !b.disabled) && waitLeft <= earlyContinueSeconds;
            return {stage:'powergam-readiness-poll', href: location.href, waitLeft, timerText: document.querySelector('#myTimer')?.textContent || null, continueReady, readyToGo: window.readyToGo, earlyContinueSeconds, buttons: buttons.slice(0, 12), cookies: document.cookie || ''};
            """,
            early_continue_seconds,
        ) or {}
        if last.get("continueReady") or urlparse(last.get("href") or "").netloc.lower() in GPLINKS_HOSTS:
            return last
        time.sleep(interval)
    return last


def wait_document_ready(driver, timeout: float = 20, interval: float = 0.5) -> dict:
    """Wait until the current page has enough DOM to inspect.

    The old helper used large fixed sleeps after navigation. This keeps the
    same success oracle but returns as soon as the browser has a body and is not
    visibly sitting on Cloudflare's interstitial.
    """
    end = time.time() + timeout
    last = state(driver, "ready-wait")
    while time.time() < end:
        last = state(driver, "ready-wait")
        text = (last.get("text") or "").strip().lower()
        title = (last.get("title") or "").strip().lower()
        if text and "performing security verification" not in text and "just a moment" not in title:
            return last
        time.sleep(interval)
    return last


def import_driver_cookies_to_session(driver, session, allowed_hosts: set[str] | None = None) -> list[dict]:
    allowed_hosts = allowed_hosts or GPLINKS_HOSTS
    imported: list[dict] = []
    for cookie in driver.get_cookies():
        name = cookie.get("name")
        value = cookie.get("value")
        domain = str(cookie.get("domain") or "").lstrip(".")
        if not name or value is None or domain not in allowed_hosts:
            continue
        path = cookie.get("path") or "/"
        try:
            session.cookies.set(name, value, domain=domain, path=path)
            imported.append({"name": name, "domain": domain, "path": path})
        except Exception as exc:
            imported.append({"name": name, "domain": domain, "path": path, "error": str(exc)[:160]})
    return imported


def try_http_final_gate_from_browser(driver, solver_url: str, timeout_left: int, timeline: list[dict]) -> dict:
    session = curl_requests.Session(impersonate="chrome136")
    try:
        ua = js(driver, "return navigator.userAgent") or DEFAULT_HEADERS.get("User-Agent") if "DEFAULT_HEADERS" in globals() else None
    except Exception:
        ua = None
    if ua:
        try:
            session.headers.update({"User-Agent": ua})
        except Exception:
            pass
    imported = import_driver_cookies_to_session(driver, session, allowed_hosts=GPLINKS_HOSTS)
    page_url = driver.current_url
    html = driver.page_source or ""
    local_timeline: list[dict] = []
    timeline.append({"stage": "http-final-gate-start", "page_url": page_url, "imported_cookies": imported})
    try:
        result = post_gplinks_final_gate_http(session, page_url, html, solver_url, max(60, timeout_left), local_timeline)
    except Exception as exc:
        result = {"status": 0, "stage": "http-final-gate", "message": str(exc)}
    result = dict(result)
    result["stage"] = "http-final-gate"
    timeline.append({"stage": "http-final-gate-result", "status": result.get("status"), "message": result.get("message"), "bypass_url": result.get("bypass_url"), "timeline": local_timeline})
    return result


def unlock_final_gate(driver, solver_url: str, timeout_left: int) -> dict:
    actions: list[dict] = []
    before = wait_not_cloudflare(driver, 35)
    before["stage"] = "before-unlock"
    actions.append(before)
    try:
        outdir = PROJECT_ROOT / "artifacts" / "active" / "gplinks-final-probe"
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "latest_before_unlock.json").write_text(json.dumps(before, ensure_ascii=False, indent=2), encoding="utf-8")
        (outdir / "latest_before_unlock.html").write_text(driver.page_source, encoding="utf-8")
        driver.save_screenshot(str(outdir / "latest_before_unlock.png"))
    except Exception:
        pass
    app_vars = before.get("app_vars") or {}
    sitekey = before.get("sitekey")
    token = None
    if sitekey and str(app_vars.get("cloudflare_turnstile_on", "")).lower() != "no":
        token = solve_turnstile(solver_url, "https://gplinks.co/", sitekey, max(60, timeout_left))
        actions.append({"stage": "turnstile-token", "sitekey": sitekey, "token_len": len(token)})
    if before.get("captchaInput") and not token:
        actions.append({"stage": "captcha-required", "reason": "captchaShortlink_captcha input present and no solver value available"})
        return {"actions": actions, "sitekey": sitekey, "token_used": False, "captcha_required": True}

    submit = js(
        driver,
        r"""
        const token=arguments[0];
        const f=document.querySelector('form#go-link') || document.querySelector('form');
        if(!f) return {submitted:false, reason:'go-link form not found'};
        if(token){
          for(const name of ['cf-turnstile-response','g-recaptcha-response']){
            let el=document.querySelector(`[name="${name}"]`);
            if(!el){el=document.createElement('textarea'); el.name=name; el.style.display='none'; f.appendChild(el);}
            el.value=token;
          }
        }
        const cap=document.querySelector('#captchaShortlink_captcha');
        if(cap && !cap.value){ cap.value='0000'; cap.dispatchEvent(new Event('input',{bubbles:true})); cap.dispatchEvent(new Event('change',{bubbles:true})); }
        const btn=document.querySelector('#captchaButton');
        if(btn){ btn.classList.remove('disabled'); btn.removeAttribute('disabled'); btn.style.pointerEvents='auto'; }
        f.classList.add('go-link');
        try{
          if(typeof window.onTurnstileCompleted === 'function') { window.onTurnstileCompleted(token); }
          else if(window.jQuery){ window.jQuery(f).addClass('go-link'); window.jQuery(f).trigger('submit'); }
          else { f.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true})); }
        }catch(e){ return {submitted:false, reason:String(e)}; }
        return {submitted:true, action:f.action, data:new URLSearchParams(new FormData(f)).toString(), href:location.href, button:btn ? {text:btn.innerText, cls:btn.className, href:btn.href} : null};
        """,
        token,
    )
    actions.append({"stage": "submit-attempt", **(submit or {})})
    final_href = None
    for _ in range(24):
        time.sleep(1)
        st = state(driver, "wait-final-href")
        btn = st.get("captchaButton") or {}
        href = btn.get("href")
        if is_final_url(href):
            final_href = href
            actions.append(st)
            break
    if final_href and GPLINKS_NAVIGATE_FINAL:
        try:
            driver.get(final_href)
            time.sleep(5)
        except Exception as exc:
            actions.append({"stage": "final-navigation-warning", "href": final_href, "reason": str(exc)[:300]})
    elif final_href:
        actions.append({"stage": "final-navigation-skipped", "href": final_href, "reason": "valid downstream href is already the final oracle"})
    close_extra_windows(driver)
    actions.append(state(driver, "after-unlock"))
    return {"actions": actions, "sitekey": sitekey, "token_used": bool(token), "final_href": final_href}


def run(url: str, timeout: int, solver_url: str) -> dict:
    started = time.time()
    timeline: list[dict] = []
    session = curl_requests.Session(impersonate="chrome136")
    entry = session.get(url, timeout=40, allow_redirects=False)
    power_url = entry.headers.get("location") or ""
    decoded = decoded_power_query(power_url) if power_url else {}

    driver = build_driver()
    try:
        timeline.append({"stage": "pre-navigation-recorders", **install_pre_navigation_recorders(driver)})
        if GPLINKS_DIRECT_POWERGAM and power_url:
            timeline.append({"stage": "direct-powergam-requested", "imported_cookies": import_session_cookies(driver, session, "https://gplinks.co/")})
            try:
                driver.execute_cdp_cmd("Network.enable", {})
                driver.execute_cdp_cmd("Network.setExtraHTTPHeaders", {"headers": {"Referer": url}})
            except Exception:
                pass
            driver.get(power_url)
            install_gpt_lifecycle_probe(driver)
            install_network_ledger_recorder(driver)
            wait_document_ready(driver, 25)
            timeline.append(state(driver, "entry-direct-powergam"))
        else:
            driver.get(url)
            install_gpt_lifecycle_probe(driver)
            install_network_ledger_recorder(driver)
            wait_document_ready(driver, 25)
            timeline.append(state(driver, "entry"))

        if urlparse(driver.current_url).netloc.lower() not in POWERGAM_HOSTS:
            if not power_url:
                return {"status": 0, "stage": "entry", "message": "POWERGAM_REDIRECT_NOT_FOUND", "entry_status": entry.status_code, "timeline": timeline}
            try:
                driver.execute_cdp_cmd("Network.enable", {})
                driver.execute_cdp_cmd("Network.setExtraHTTPHeaders", {"headers": {"Referer": url}})
            except Exception:
                pass
            driver.get(power_url)
            install_gpt_lifecycle_probe(driver)
            install_network_ledger_recorder(driver)
            wait_document_ready(driver, 25)
        install_gpt_lifecycle_probe(driver)
        install_network_ledger_recorder(driver)
        timeline.append(state(driver, "power-entry"))

        deadline = time.time() + max(90, timeout - 45)
        last_click: dict = {}
        while time.time() < deadline:
            cur = state(driver, "loop")
            timeline.append(cur)
            href = cur.get("href") or driver.current_url
            host = urlparse(href).netloc.lower()
            if host in GPLINKS_HOSTS and "pid=" in href and "vid=" in href:
                break
            if host in GPLINKS_HOSTS and urlparse(href).path.startswith("/link-error"):
                return {"status": 0, "stage": "powergam", "message": "GPLINKS_LINK_ERROR", "final_url": href, "decoded_query": decoded, "timeline": timeline}
            last_click = click_next_powergam(driver)
            timeline.append({"stage": "power-click", **last_click})
            wait_left = last_click.get("waitLeft")
            if isinstance(wait_left, (int, float)) and wait_left > 0:
                timeline.append(wait_powergam_continue_ready(driver, min(float(wait_left) + 0.5, 16.0), interval=0.25, early_continue_seconds=GPLINKS_EARLY_CONTINUE_SECONDS))
            else:
                wait_document_ready(driver, 4, interval=0.3)
        else:
            return {"status": 0, "stage": "powergam", "message": "POWERGAM_FINAL_CANDIDATE_TIMEOUT", "decoded_query": decoded, "last_click": last_click, "timeline": timeline}

        candidate = wait_not_cloudflare(driver, 35)
        candidate["stage"] = "candidate"
        timeline.append(candidate)
        timeline.append(collect_gpt_lifecycle_events(driver, "powergam-gpt-lifecycle"))
        timeline.append(collect_network_ledger_events(driver, "powergam-network-ledger"))
        candidate_url = candidate.get("href") or driver.current_url
        if is_final_url(candidate_url):
            return {"status": 1, "stage": "live-browser-powergam", "bypass_url": candidate_url, "final_url": candidate_url, "decoded_query": decoded, "timeline": timeline, "waited_seconds": round(time.time() - started, 1)}

        if GPLINKS_HTTP_FINAL_HANDOFF:
            http_final = try_http_final_gate_from_browser(driver, solver_url, max(60, timeout - int(time.time() - started)), timeline)
            if http_final.get("status") == 1 and http_final.get("bypass_url"):
                return {"status": 1, "stage": "live-browser-http-final", "bypass_url": http_final.get("bypass_url"), "final_url": http_final.get("final_url") or http_final.get("bypass_url"), "decoded_query": decoded, "sitekey": http_final.get("sitekey"), "token_used": http_final.get("token_used"), "token_source": http_final.get("token_source"), "timeline": timeline, "waited_seconds": round(time.time() - started, 1)}
        else:
            timeline.append({"stage": "http-final-gate-skipped", "reason": "disabled by SHORTLINK_BYPASS_GPLINKS_HTTP_FINAL_HANDOFF"})

        unlock = unlock_final_gate(driver, solver_url, max(60, timeout - int(time.time() - started)))
        timeline.extend(unlock.get("actions") or [])
        timeline.append(collect_gpt_lifecycle_events(driver, "final-gpt-lifecycle"))
        timeline.append(collect_network_ledger_events(driver, "final-network-ledger"))
        final_state = state(driver, "final")
        timeline.append(final_state)
        final_url = final_state.get("href") or driver.current_url
        button_url = unlock.get("final_href") or ((final_state.get("captchaButton") or {}).get("href"))
        if is_final_url(button_url) or is_final_url(final_url):
            target = button_url if is_final_url(button_url) else final_url
            return {"status": 1, "stage": "live-browser-final-gate", "bypass_url": target, "final_url": target, "decoded_query": decoded, "sitekey": unlock.get("sitekey"), "token_used": unlock.get("token_used"), "timeline": timeline, "waited_seconds": round(time.time() - started, 1)}
        return {"status": 0, "stage": "final-gate", "message": "FINAL_TARGET_NOT_REACHED", "final_url": final_url, "decoded_query": decoded, "sitekey": unlock.get("sitekey"), "token_used": unlock.get("token_used"), "timeline": timeline}
    finally:
        try:
            driver.quit()
        except Exception:
            pass


def main() -> int:
    if not os.environ.get("DISPLAY") and not os.environ.get("GPLINKS_XVFB_REEXEC") and shutil.which("xvfb-run"):
        env = os.environ.copy()
        env["GPLINKS_XVFB_REEXEC"] = "1"
        os.execvpe("xvfb-run", ["xvfb-run", "-a", sys.executable, __file__, *sys.argv[1:]], env)

    parser = argparse.ArgumentParser(description="Live browser helper for gplinks.co / PowerGam")
    parser.add_argument("url")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--solver-url", default="http://127.0.0.1:5000")
    args = parser.parse_args()
    try:
        payload = run(args.url, args.timeout, args.solver_url)
    except Exception as exc:
        payload = {"status": 0, "stage": "exception", "message": str(exc)}
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload.get("status") == 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
