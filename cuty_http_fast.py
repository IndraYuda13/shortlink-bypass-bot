#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests

from cuty_live_browser import detect_chrome_path, solve_turnstile

CUTY_INTERNAL_HOSTS = {"cuty.io", "www.cuty.io", "cuttlinks.com", "www.cuttlinks.com"}


def _chrome_major() -> int:
    try:
        import re, subprocess
        out = subprocess.check_output([detect_chrome_path(), "--version"], text=True, timeout=10)
        m = re.search(r"(\d+)\.", out)
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return 147


BASE_HEADERS = {
    "User-Agent": f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/{_chrome_major()}.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Upgrade-Insecure-Requests": "1",
}


def extract_form_payload(html: str, selector: str = "form") -> dict:
    soup = BeautifulSoup(html or "", "html.parser")
    form = soup.select_one(selector) or soup.find("form")
    if not form:
        return {"found": False, "action": None, "method": None, "data": {}}
    data: dict[str, str] = {}
    for item in form.select("input, textarea, select"):
        name = item.get("name")
        if name:
            data[name] = item.get("value") or ""
    return {"found": True, "id": form.get("id") or "", "action": form.get("action") or "", "method": (form.get("method") or "GET").upper(), "data": data}


def turnstile_sitekey(html: str) -> str | None:
    soup = BeautifulSoup(html or "", "html.parser")
    turnstile = soup.select_one(".cf-turnstile[data-sitekey]")
    return turnstile.get("data-sitekey") if turnstile else None


def is_downstream_url(url: str | None) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = parsed.netloc.lower()
    return bool(host and host not in CUTY_INTERNAL_HOSTS)


def _post_form(session, action: str, data: dict[str, str], referer: str, timeout: int = 40):
    return session.post(
        action,
        data=data,
        headers={**BASE_HEADERS, "Origin": "null", "Referer": referer, "Content-Type": "application/x-www-form-urlencoded"},
        allow_redirects=True,
        timeout=timeout,
    )


def _summary_form(html: str, page_url: str, selector: str) -> dict:
    form = extract_form_payload(html, selector)
    if form.get("action"):
        form["action"] = urljoin(page_url, str(form["action"]))
    if "data" in form:
        form["fields"] = sorted(form.get("data", {}).keys())
        form.pop("data", None)
    return form


def _cookies_list(session) -> list[dict]:
    try:
        return [{"name": c.name, "domain": c.domain, "path": c.path, "value_len": len(c.value or "")} for c in session.cookies.jar]
    except Exception:
        return []


def _best_effort_vhit(session, referer: str, timeline: list[dict]) -> None:
    """Mirror the server-visible VHit fetches seen in the browser lane.

    A later live probe showed the final may already pass without these calls, but
    keeping them is cheap and closer to the real browser lifecycle. Failures are
    diagnostic-only because the success oracle is the downstream final URL.
    """
    try:
        fp = session.post(
            "https://fp.vhit.io/",
            headers={"User-Agent": BASE_HEADERS["User-Agent"], "Accept": "*/*", "Origin": "https://cuttlinks.com", "Referer": referer},
            timeout=15,
        )
        timeline.append({"stage": "vhit-fp", "status": fp.status_code, "url": fp.url, "text": (fp.text or "")[:160]})
        req = session.get(
            "https://vhit.io/api/request?f=c05f1bfbacf97684fd9fc9e742760250",
            headers={"User-Agent": BASE_HEADERS["User-Agent"], "Accept": "application/json", "Content-Type": "application/json", "Origin": "https://cuttlinks.com", "Referer": referer},
            timeout=15,
        )
        timeline.append({"stage": "vhit-request", "status": req.status_code, "url": req.url, "text": (req.text or "")[:160]})
    except Exception as exc:
        timeline.append({"stage": "vhit-best-effort", "message": str(exc)})


def run(url: str, timeout: int = 160, solver_url: str = "http://127.0.0.1:5000") -> dict:
    started = time.time()
    timeline: list[dict] = []
    session = curl_requests.Session(impersonate="chrome136")
    try:
        entry = session.get(url, headers=BASE_HEADERS, allow_redirects=False, timeout=30)
        auth_url = entry.headers.get("location")
        timeline.append({"stage": "entry", "status": entry.status_code, "url": entry.url, "location": auth_url, "cookies": _cookies_list(session)})
        if not auth_url:
            return {"status": 0, "stage": "entry", "message": "AUTH_REDIRECT_NOT_FOUND", "timeline": timeline, "waited_seconds": round(time.time() - started, 1)}

        auth = session.get(auth_url, headers={**BASE_HEADERS, "Referer": url}, allow_redirects=False, timeout=30)
        first_url = auth.headers.get("location") or auth.url
        timeline.append({"stage": "auth", "status": auth.status_code, "url": auth.url, "location": first_url, "cookies": _cookies_list(session)})
        first = session.get(first_url, headers={**BASE_HEADERS, "Referer": auth_url}, allow_redirects=True, timeout=30)
        first_form = extract_form_payload(first.text, "form#free-submit-form")
        timeline.append({"stage": "first", "status": first.status_code, "url": first.url, "free_form": _summary_form(first.text, first.url, "form#free-submit-form"), "cookies": _cookies_list(session)})
        if not first_form.get("found"):
            return {"status": 0, "stage": "first", "message": "FREE_FORM_NOT_FOUND", "timeline": timeline, "waited_seconds": round(time.time() - started, 1)}

        captcha = _post_form(session, urljoin(first.url, str(first_form.get("action") or "")), dict(first_form.get("data") or {}), first.url, 40)
        sitekey = turnstile_sitekey(captcha.text)
        captcha_form = extract_form_payload(captcha.text, "form#free-submit-form")
        timeline.append({"stage": "captcha", "status": captcha.status_code, "url": captcha.url, "sitekey": sitekey, "free_form": _summary_form(captcha.text, captcha.url, "form#free-submit-form"), "cookies": _cookies_list(session)})
        if not sitekey:
            return {"status": 0, "stage": "captcha", "message": "TURNSTILE_SITEKEY_NOT_FOUND", "timeline": timeline, "waited_seconds": round(time.time() - started, 1)}
        if not captcha_form.get("found"):
            return {"status": 0, "stage": "captcha", "message": "CAPTCHA_FORM_NOT_FOUND", "timeline": timeline, "sitekey": sitekey, "waited_seconds": round(time.time() - started, 1)}

        token = solve_turnstile(solver_url, captcha.url, sitekey, timeout)
        captcha_data = dict(captcha_form.get("data") or {})
        captcha_data["cf-turnstile-response"] = token
        timeline.append({"stage": "turnstile-token", "sitekey": sitekey, "token_len": len(token)})
        last = _post_form(session, urljoin(captcha.url, str(captcha_form.get("action") or "")), captcha_data, captcha.url, 60)
        submit_form = extract_form_payload(last.text, "form#submit-form")
        timeline.append({"stage": "last", "status": last.status_code, "url": last.url, "submit_form": _summary_form(last.text, last.url, "form#submit-form"), "cookies": _cookies_list(session)})
        if not submit_form.get("found"):
            return {"status": 0, "stage": "last", "message": "SUBMIT_FORM_NOT_FOUND", "timeline": timeline, "sitekey": sitekey, "waited_seconds": round(time.time() - started, 1)}

        _best_effort_vhit(session, last.url, timeline)
        time.sleep(9)
        final = _post_form(session, urljoin(last.url, str(submit_form.get("action") or "")), dict(submit_form.get("data") or {}), last.url, 60)
        timeline.append({"stage": "final", "status": final.status_code, "url": final.url, "location": final.headers.get("location"), "text": (final.text or "")[:160]})
        if is_downstream_url(final.url):
            return {"status": 1, "stage": "http-final", "bypass_url": final.url, "final_url": final.url, "sitekey": sitekey, "timeline": timeline, "waited_seconds": round(time.time() - started, 1)}
        return {"status": 0, "stage": "http-final", "message": "FINAL_DID_NOT_LEAVE_CUTTLINKS", "final_url": final.url, "sitekey": sitekey, "timeline": timeline, "waited_seconds": round(time.time() - started, 1)}
    except Exception as exc:
        return {"status": 0, "stage": "exception", "message": str(exc), "timeline": timeline, "waited_seconds": round(time.time() - started, 1)}


def main() -> int:
    parser = argparse.ArgumentParser(description="HTTP-only cuty.io/cuttlinks.com helper")
    parser.add_argument("url")
    parser.add_argument("--timeout", type=int, default=160)
    parser.add_argument("--solver-url", default="http://127.0.0.1:5000")
    args = parser.parse_args()
    payload = run(args.url, args.timeout, args.solver_url)
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload.get("status") == 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
