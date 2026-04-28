from __future__ import annotations

import argparse
import json
import time
from urllib.parse import urlparse

from cuty_live_browser import CdpPage, detect_chrome_path, solve_turnstile

GOOGLE_HOSTS = {"google.com", "www.google.com"}


def state(page: CdpPage) -> dict:
    raw = page.eval(
        """({
          href: location.href,
          title: document.title,
          text: document.body ? document.body.innerText.slice(0, 900) : '',
          site: document.querySelector('.cf-turnstile')?.dataset.sitekey || (typeof app_vars !== 'undefined' ? app_vars.turnstile_site_key : null) || null,
          recaptcha: document.querySelector('.g-recaptcha')?.dataset.sitekey || (typeof app_vars !== 'undefined' ? app_vars.reCAPTCHA_site_key : null) || null,
          forms: [...document.forms].map(f => ({id:f.id, action:f.action, method:f.method, data:new URLSearchParams(new FormData(f)).toString()})),
          buttons: [...document.querySelectorAll('button,input[type=submit],a')].slice(0, 24).map(x => ({tag:x.tagName,id:x.id,text:x.innerText||x.value||'',href:x.href||'',disabled:!!x.disabled}))
        })"""
    )
    return raw.get("value") or {}


def run(url: str, timeout: int, solver_url: str) -> dict:
    started = time.time()
    timeline: list[dict] = []
    with CdpPage(detect_chrome_path(), timeout) as page:
        page.navigate(url)
        page.drain(12)
        timeline.append({"stage": "entry", **state(page)})

        page.eval("""(()=>{const f=document.querySelector('form#before-captcha')||document.querySelector('form'); if(f){f.submit(); return true} return false;})()""")
        page.drain(10)
        captcha_state = state(page)
        timeline.append({"stage": "captcha", **captcha_state})
        sitekey = captcha_state.get("site")
        if not sitekey:
            return {"status": 0, "stage": "captcha", "message": "Turnstile sitekey not found", "timeline": timeline}

        # Trigger explicit/invisible widget rendering if the site script has not
        # materialized the .cf-turnstile container yet. The token solver still
        # uses the real page URL and real sitekey from app_vars.
        page.eval("document.querySelector('#invisibleCaptchaShortlink')?.click()")
        page.drain(3)

        try:
            token = solve_turnstile(solver_url, captcha_state.get("href") or url, sitekey, max(60, timeout - int(time.time() - started)))
        except Exception as exc:
            return {
                "status": 0,
                "stage": "captcha-solver",
                "message": "TURNSTILE_SOLVER_FAILED",
                "solver_error": str(exc),
                "sitekey": sitekey,
                "timeline": timeline,
            }

        page.eval(
            """(()=>{const token=%s; const f=document.querySelector('form#link-view')||document.querySelector('form'); if(!f) return false; for (const name of ['cf-turnstile-response','g-recaptcha-response']) { let el=document.querySelector(`[name="${name}"]`); if(!el){el=document.createElement('textarea'); el.name=name; el.style.display='none'; f.appendChild(el)} el.value=token; } for (const btn of document.querySelectorAll('button,input[type=submit]')) btn.disabled=false; return true;})()"""
            % json.dumps(token)
        )
        page.drain(8)
        after_token = state(page)
        timeline.append({"stage": "after-token", **after_token})

        # Exeygo has a short visible countdown. Wait a bit so server/client-side checks
        # can mark the link-view form as ready before submit.
        page.drain(8)
        page.eval("""(()=>{const f=document.querySelector('form#link-view')||document.querySelector('form'); if(f){f.submit(); return true} return false;})()""")
        page.drain(14)
        go_state = state(page)
        timeline.append({"stage": "go-link", **go_state})

        if any(form.get("id") == "go-link" for form in go_state.get("forms", [])):
            page.eval("""(()=>{const f=document.querySelector('form#go-link'); if(f){f.submit(); return true} return false;})()""")
            page.drain(18)

        final_state = state(page)
        timeline.append({"stage": "final", **final_state})
        final_url = final_state.get("href") or ""
        host = urlparse(final_url).netloc.lower()
        if host in GOOGLE_HOSTS or (host and host not in {"exe.io", "exeygo.com", "www.exe.io", "www.exeygo.com"}):
            return {
                "status": 1,
                "stage": "live-browser-turnstile-go",
                "bypass_url": final_url,
                "final_url": final_url,
                "final_title": final_state.get("title"),
                "sitekey": sitekey,
                "timeline": timeline,
                "waited_seconds": round(time.time() - started, 1),
            }
        return {"status": 0, "stage": "final", "message": "final page did not leave exeygo", "final_url": final_url, "sitekey": sitekey, "timeline": timeline}


def main() -> int:
    parser = argparse.ArgumentParser(description="Live browser helper for exe.io/exeygo.com")
    parser.add_argument("url")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--solver-url", default="http://127.0.0.1:5000")
    args = parser.parse_args()
    print(json.dumps(run(args.url, args.timeout, args.solver_url), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
