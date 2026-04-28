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

PROJECT_ROOT = Path(__file__).resolve().parent
CHROME_PATH = "/usr/bin/google-chrome" if Path("/usr/bin/google-chrome").exists() else "/usr/bin/google-chrome-stable"
GPLINKS_HOSTS = {"gplinks.co", "www.gplinks.co"}
POWERGAM_HOSTS = {"powergam.online", "www.powergam.online"}


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
    return data or {"stage": stage}


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


def click_next_powergam(driver) -> dict:
    result = js(
        driver,
        r"""
        const els=[...document.querySelectorAll('a,button,input[type=submit]')].map((el,i)=>({i,el,t:(el.innerText||el.value||el.textContent||'').trim(),disabled:!!el.disabled||el.classList.contains('disabled'),tag:el.tagName,id:el.id,cls:el.className||''}));
        const body=(document.body?.innerText||'');
        const waitMatch=body.match(/Please wait\s+(\d+)\s+Seconds/i);
        const waitLeft=waitMatch ? parseInt(waitMatch[1],10) : 0;
        const verify=els.find(x=>/^verify$/i.test(x.t)&&!x.disabled);
        const cont=els.find(x=>/^continue$/i.test(x.t)&&!x.disabled);
        let target=verify || (waitLeft <= 0 ? cont : null) || els.find(x=>/verify/i.test(x.t)&&!x.disabled) || (waitLeft <= 0 ? els.find(x=>/continue/i.test(x.t)&&!x.disabled) : null);
        if(!target) return {clicked:false, waitLeft, candidates:els.slice(0,24).map(x=>({i:x.i,t:x.t,disabled:x.disabled,tag:x.tag,id:x.id,cls:x.cls}))};
        if(/continue/i.test(target.t)) {
          window.scrollTo(0, document.body.scrollHeight);
          document.dispatchEvent(new Event('scroll', {bubbles:true}));
        }
        target.el.scrollIntoView({block:'center'});
        target.el.click();
        return {clicked:true,text:target.t,idx:target.i,disabled:target.disabled,tag:target.tag,id:target.id,cls:target.cls};
        """,
    )
    close_extra_windows(driver)
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
    if final_href:
        try:
            driver.get(final_href)
            time.sleep(5)
        except Exception as exc:
            actions.append({"stage": "final-navigation-warning", "href": final_href, "reason": str(exc)[:300]})
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
        driver.get(url)
        time.sleep(12)
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
            time.sleep(12)
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
            time.sleep(9)
        else:
            return {"status": 0, "stage": "powergam", "message": "POWERGAM_FINAL_CANDIDATE_TIMEOUT", "decoded_query": decoded, "last_click": last_click, "timeline": timeline}

        time.sleep(8)
        candidate = wait_not_cloudflare(driver, 35)
        candidate["stage"] = "candidate"
        timeline.append(candidate)
        candidate_url = candidate.get("href") or driver.current_url
        if is_final_url(candidate_url):
            return {"status": 1, "stage": "live-browser-powergam", "bypass_url": candidate_url, "final_url": candidate_url, "decoded_query": decoded, "timeline": timeline, "waited_seconds": round(time.time() - started, 1)}

        unlock = unlock_final_gate(driver, solver_url, max(60, timeout - int(time.time() - started)))
        timeline.extend(unlock.get("actions") or [])
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
