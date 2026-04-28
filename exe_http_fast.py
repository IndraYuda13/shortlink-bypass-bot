#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import time
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests

from cuty_live_browser import solve_turnstile

EXE_INTERNAL_HOSTS = {"exe.io", "www.exe.io", "exeygo.com", "www.exeygo.com"}
BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Upgrade-Insecure-Requests": "1",
}


def extract_app_vars(html: str) -> dict[str, str]:
    block = re.search(r"(?:var\s+)?app_vars\s*=\s*(\{.*?\})\s*;", html or "", re.S)
    if not block:
        return {}
    raw = block.group(1)
    try:
        parsed = json.loads(raw)
        return {str(k): str(v) for k, v in parsed.items()}
    except Exception:
        out: dict[str, str] = {}
        for key, value in re.findall(r'["\']?([A-Za-z0-9_]+)["\']?\s*:\s*["\']([^"\']*)["\']', raw):
            out[key] = value
        return out


def extract_form_payload(html: str, form_selector: str = "form") -> dict:
    soup = BeautifulSoup(html or "", "html.parser")
    form = soup.select_one(form_selector) or soup.find("form")
    if not form:
        return {"found": False, "action": None, "method": None, "data": {}}
    data: dict[str, str] = {}
    for item in form.select("input, textarea, select"):
        name = item.get("name")
        if name:
            data[name] = item.get("value") or ""
    return {
        "found": True,
        "id": form.get("id") or "",
        "action": form.get("action") or "",
        "method": (form.get("method") or "GET").upper(),
        "data": data,
    }


def is_downstream_url(url: str | None) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = parsed.netloc.lower()
    return bool(host and host not in EXE_INTERNAL_HOSTS)


def _sitekey_from(html: str) -> str | None:
    soup = BeautifulSoup(html or "", "html.parser")
    turnstile = soup.select_one(".cf-turnstile[data-sitekey]")
    if turnstile and turnstile.get("data-sitekey"):
        return turnstile.get("data-sitekey")
    vars_obj = extract_app_vars(html)
    return vars_obj.get("turnstile_site_key")


def _cookies_list(session) -> list[dict]:
    try:
        return [{"name": c.name, "domain": c.domain, "path": c.path, "value_len": len(c.value or "")} for c in session.cookies.jar]
    except Exception:
        return []


def _post_form(session, action: str, data: dict[str, str], referer: str, timeout: int, allow_redirects: bool = True):
    parsed = urlparse(action)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    headers = {
        **BASE_HEADERS,
        "Origin": origin,
        "Referer": referer,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    return session.post(action, data=data, headers=headers, timeout=timeout, allow_redirects=allow_redirects)


def _summary_form(html: str, page_url: str, selector: str) -> dict:
    form = extract_form_payload(html, selector)
    if form.get("action"):
        form["action"] = urljoin(page_url, str(form["action"]))
    if "data" in form:
        form["fields"] = sorted(form["data"].keys())
        form.pop("data", None)
    return form


def run(url: str, timeout: int = 160, solver_url: str = "http://127.0.0.1:5000") -> dict:
    started = time.time()
    timeline: list[dict] = []
    session = curl_requests.Session(impersonate="chrome136")
    try:
        entry = session.get(url, headers=BASE_HEADERS, timeout=30, allow_redirects=False)
        gate_url = entry.headers.get("location") or url
        timeline.append({"stage": "entry", "status": entry.status_code, "url": entry.url, "location": gate_url, "cookies": _cookies_list(session)})

        first = session.get(gate_url, headers={**BASE_HEADERS, "Referer": url}, timeout=30, allow_redirects=True)
        first_vars = extract_app_vars(first.text)
        timeline.append({"stage": "first", "status": first.status_code, "url": first.url, "app_vars": first_vars, "before_form": _summary_form(first.text, first.url, "form#before-captcha"), "cookies": _cookies_list(session)})
        before = extract_form_payload(first.text, "form#before-captcha")
        if not before.get("found"):
            return {"status": 0, "stage": "first", "message": "BEFORE_CAPTCHA_FORM_NOT_FOUND", "timeline": timeline, "waited_seconds": round(time.time() - started, 1)}
        before_action = urljoin(first.url, str(before.get("action") or ""))
        second = _post_form(session, before_action, dict(before.get("data") or {}), first.url, timeout=30)

        second_vars = extract_app_vars(second.text)
        sitekey = _sitekey_from(second.text)
        timeline.append({"stage": "second", "status": second.status_code, "url": second.url, "app_vars": second_vars, "sitekey": sitekey, "link_form": _summary_form(second.text, second.url, "form#link-view"), "cookies": _cookies_list(session)})
        link = extract_form_payload(second.text, "form#link-view")
        if not link.get("found"):
            return {"status": 0, "stage": "second", "message": "LINK_VIEW_FORM_NOT_FOUND", "timeline": timeline, "waited_seconds": round(time.time() - started, 1)}
        if not sitekey:
            return {"status": 0, "stage": "captcha", "message": "TURNSTILE_SITEKEY_NOT_FOUND", "timeline": timeline, "waited_seconds": round(time.time() - started, 1)}

        token = solve_turnstile(solver_url, second.url, sitekey, timeout)
        link_data = dict(link.get("data") or {})
        link_data["cf-turnstile-response"] = token
        link_data.setdefault("g-recaptcha-response", "")
        timeline.append({"stage": "turnstile-token", "sitekey": sitekey, "token_len": len(token)})

        counter_raw = second_vars.get("counter_value") or first_vars.get("counter_value") or "6"
        try:
            counter = int(float(counter_raw))
        except Exception:
            counter = 6
        time.sleep(max(0, counter) + 1)

        link_action = urljoin(second.url, str(link.get("action") or ""))
        go_page = _post_form(session, link_action, link_data, second.url, timeout=40)
        timeline.append({"stage": "link-view-post", "status": go_page.status_code, "url": go_page.url, "go_form": _summary_form(go_page.text, go_page.url, "form#go-link"), "cookies": _cookies_list(session)})
        go_form = extract_form_payload(go_page.text, "form#go-link")
        if not go_form.get("found"):
            return {"status": 0, "stage": "link-view-post", "message": "GO_LINK_FORM_NOT_FOUND", "timeline": timeline, "sitekey": sitekey, "waited_seconds": round(time.time() - started, 1)}

        time.sleep(max(0, counter) + 1)
        go_action = urljoin(go_page.url, str(go_form.get("action") or ""))
        final = _post_form(session, go_action, dict(go_form.get("data") or {}), go_page.url, timeout=40)
        timeline.append({"stage": "final-post", "status": final.status_code, "url": final.url, "location": final.headers.get("location"), "text": (final.text or "")[:200]})
        if is_downstream_url(final.url):
            return {"status": 1, "stage": "http-final", "bypass_url": final.url, "final_url": final.url, "sitekey": sitekey, "timeline": timeline, "waited_seconds": round(time.time() - started, 1)}
        return {"status": 0, "stage": "http-final", "message": "FINAL_DID_NOT_LEAVE_EXEYGO", "final_url": final.url, "sitekey": sitekey, "timeline": timeline, "waited_seconds": round(time.time() - started, 1)}
    except Exception as exc:
        return {"status": 0, "stage": "exception", "message": str(exc), "timeline": timeline, "waited_seconds": round(time.time() - started, 1)}


def main() -> int:
    parser = argparse.ArgumentParser(description="HTTP-only exe.io/exeygo.com helper")
    parser.add_argument("url")
    parser.add_argument("--timeout", type=int, default=160)
    parser.add_argument("--solver-url", default="http://127.0.0.1:5000")
    args = parser.parse_args()
    payload = run(args.url, args.timeout, args.solver_url)
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload.get("status") == 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
