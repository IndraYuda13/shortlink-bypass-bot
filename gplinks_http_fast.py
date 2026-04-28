#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import time
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests

from cuty_live_browser import solve_turnstile

GPLINKS_HOSTS = {"gplinks.co", "www.gplinks.co"}
POWERGAM_HOSTS = {"powergam.online", "www.powergam.online"}
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _b64_decode(value: str) -> str:
    try:
        return base64.b64decode(value + "=" * ((4 - len(value) % 4) % 4)).decode()
    except Exception:
        return value


def raw_power_query(power_url: str) -> dict[str, str | None]:
    query = parse_qs(urlparse(power_url).query)
    return {key: (query.get(key) or [""])[0] or None for key in ["lid", "pid", "vid", "pages"]}


def decoded_power_query(power_url: str) -> dict[str, str | None]:
    return {key: _b64_decode(value or "") or None for key, value in raw_power_query(power_url).items()}


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


def extract_final_gate(html: str, page_url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    form = soup.select_one("form#go-link") or soup.find("form")
    if not form:
        return {"action": None, "payload": {}, "sitekey": None, "has_form": False}
    payload: dict[str, str] = {}
    for item in form.select("input, textarea, select"):
        name = item.get("name")
        if not name:
            continue
        payload[name] = item.get("value") or ""
    sitekey = None
    turnstile = soup.select_one(".cf-turnstile[data-sitekey]")
    if turnstile:
        sitekey = turnstile.get("data-sitekey")
    return {
        "action": urljoin(page_url, form.get("action") or ""),
        "payload": payload,
        "sitekey": sitekey,
        "has_form": True,
    }


def _extract_forms(html: str, page_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    forms = []
    for form in soup.find_all("form"):
        payload = {}
        for item in form.select("input, textarea, select"):
            name = item.get("name")
            if name:
                payload[name] = item.get("value") or ""
        forms.append({
            "id": form.get("id") or "",
            "action": urljoin(page_url, form.get("action") or ""),
            "method": (form.get("method") or "GET").upper(),
            "payload": payload,
        })
    return forms


def build_powergam_step_payloads(pages: int, visitor_id: str, target_final: str, fallback_target: str, imps: int = 5) -> list[dict[str, str]]:
    payloads: list[dict[str, str]] = []
    for step in range(1, max(1, pages) + 1):
        payloads.append({
            "form_name": "ads-track-data",
            "step_id": str(step),
            "ad_impressions": str(imps),
            "visitor_id": visitor_id,
            "next_target": target_final if step >= pages else fallback_target,
        })
    return payloads


def _set_powergam_cookies(session, decoded: dict[str, str | None], host_url: str, step_count: int = 0, imps: int = 5) -> None:
    host = urlparse(host_url).hostname or "powergam.online"
    cookie_values = {
        "lid": decoded.get("lid") or "",
        "pid": decoded.get("pid") or "",
        "pages": decoded.get("pages") or "",
        "vid": decoded.get("vid") or "",
        "step_count": str(step_count),
        "imps": str(imps),
        "adexp": "1",
    }
    for name, value in cookie_values.items():
        try:
            session.cookies.set(name, value, domain=host, path="/")
        except Exception:
            try:
                session.cookies.set(name, value)
            except Exception:
                pass


def _submit_power_forms(session, forms: list[dict], referer: str, timeout: int, timeline: list[dict]) -> None:
    for form in forms[:3]:
        if not form.get("action"):
            continue
        try:
            headers = {**DEFAULT_HEADERS, "Referer": referer, "Origin": "https://powergam.online"}
            if form.get("method") == "POST":
                response = session.post(form["action"], data=form.get("payload") or {}, headers=headers, timeout=timeout, allow_redirects=True)
            else:
                response = session.get(form["action"], params=form.get("payload") or {}, headers=headers, timeout=timeout, allow_redirects=True)
            timeline.append({"stage": "power-form-submit", "form_id": form.get("id"), "status": response.status_code, "url": response.url, "payload": form.get("payload") or {}})
        except Exception as exc:
            timeline.append({"stage": "power-form-submit", "form_id": form.get("id"), "error": str(exc)})


def _post_final_gate(session, page_url: str, html: str, solver_url: str, timeout: int, timeline: list[dict]) -> dict:
    gate = extract_final_gate(html, page_url)
    timeline.append({"stage": "final-gate", "action": gate.get("action"), "sitekey": gate.get("sitekey"), "has_form": gate.get("has_form")})
    if not gate.get("has_form") or not gate.get("action"):
        return {"status": 0, "stage": "final-gate", "message": "GO_LINK_FORM_NOT_FOUND"}
    payload = dict(gate.get("payload") or {})
    sitekey = gate.get("sitekey")
    token = None
    if sitekey:
        token = solve_turnstile(solver_url, "https://gplinks.co/", sitekey, max(60, timeout))
        payload["cf-turnstile-response"] = token
        payload["g-recaptcha-response"] = token
        timeline.append({"stage": "turnstile-token", "sitekey": sitekey, "token_len": len(token)})
    headers = {
        **DEFAULT_HEADERS,
        "Referer": page_url,
        "Origin": "https://gplinks.co",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/javascript, */*; q=0.01",
    }
    response = session.post(gate["action"], data=payload, headers=headers, timeout=timeout, allow_redirects=False)
    text = response.text or ""
    try:
        data = response.json()
    except Exception:
        data = None
    timeline.append({"stage": "links-go", "status": response.status_code, "url": response.url, "json": data, "text": text[:300]})
    final = data.get("url") if isinstance(data, dict) else None
    if is_final_url(final):
        return {"status": 1, "stage": "http-fast", "bypass_url": final, "final_url": final, "sitekey": sitekey, "token_used": bool(token)}
    return {"status": 0, "stage": "links-go", "message": (data or {}).get("message") if isinstance(data, dict) else "LINKS_GO_NO_FINAL_URL", "sitekey": sitekey, "token_used": bool(token)}


def run(url: str, timeout: int = 90, solver_url: str = "http://127.0.0.1:5000") -> dict:
    started = time.time()
    timeline: list[dict] = []
    session = curl_requests.Session(impersonate="chrome136")
    headers = dict(DEFAULT_HEADERS)
    try:
        entry = session.get(url, headers=headers, timeout=timeout, allow_redirects=False)
        power_url = entry.headers.get("location") or ""
        timeline.append({"stage": "entry", "status": entry.status_code, "url": entry.url, "location": power_url})
        if not power_url:
            return {"status": 0, "stage": "entry", "message": "POWERGAM_REDIRECT_NOT_FOUND", "timeline": timeline, "waited_seconds": round(time.time() - started, 2)}

        raw = raw_power_query(power_url)
        decoded = decoded_power_query(power_url)
        lid = decoded.get("lid") or ""
        pid = decoded.get("pid") or ""
        vid = raw.get("vid") or ""
        target_final_candidate = f"https://gplinks.co/{lid}?pid={pid}&vid={vid}" if lid and pid and vid else None

        power = session.get(power_url, headers={**headers, "Referer": url}, timeout=timeout, allow_redirects=True)
        timeline.append({"stage": "power", "status": power.status_code, "url": power.url, "text": (power.text or "")[:180]})
        forms = _extract_forms(power.text or "", power.url)
        timeline.append({"stage": "power-forms", "count": len(forms), "forms": [{"id": f["id"], "action": f["action"], "method": f["method"], "fields": sorted(f["payload"].keys())} for f in forms]})

        if not target_final_candidate:
            return {"status": 0, "stage": "entry", "message": "POWER_QUERY_INCOMPLETE", "decoded_query": decoded, "timeline": timeline, "waited_seconds": round(time.time() - started, 2)}

        try:
            pages = int(decoded.get("pages") or "3")
        except Exception:
            pages = 3
        visitor_id = decoded.get("vid") or ""
        if forms:
            base_form = dict(forms[0])
            for index, payload in enumerate(build_powergam_step_payloads(pages, visitor_id, target_final_candidate, "https://powergam.online", imps=5), start=1):
                _set_powergam_cookies(session, decoded, power.url, step_count=index - 1, imps=5)
                step_form = dict(base_form)
                step_form["payload"] = payload
                _submit_power_forms(session, [step_form], power.url, timeout, timeline)
        else:
            _set_powergam_cookies(session, decoded, power.url, step_count=pages, imps=5)

        final_page = session.get(target_final_candidate, headers={**headers, "Referer": power.url}, timeout=timeout, allow_redirects=False)
        final_location = final_page.headers.get("location") or ""
        timeline.append({"stage": "candidate", "status": final_page.status_code, "url": final_page.url, "location": final_location, "text": (final_page.text or "")[:180]})
        if "link-error" in final_location or "error_code=not_enough_steps" in final_location:
            return {
                "status": 0,
                "stage": "powergam-ledger",
                "message": "HTTP_FAST_POWERGAM_LEDGER_REJECTED",
                "decoded_query": decoded,
                "target_final_candidate": target_final_candidate,
                "timeline": timeline,
                "waited_seconds": round(time.time() - started, 2),
            }
        if is_final_url(final_location):
            return {"status": 1, "stage": "http-fast-redirect", "bypass_url": final_location, "final_url": final_location, "decoded_query": decoded, "timeline": timeline, "waited_seconds": round(time.time() - started, 2)}
        if final_page.status_code in {301, 302, 303, 307, 308} and final_location:
            final_page = session.get(final_location, headers={**headers, "Referer": power.url}, timeout=timeout, allow_redirects=True)
            timeline.append({"stage": "candidate-follow", "status": final_page.status_code, "url": final_page.url, "text": (final_page.text or "")[:180]})

        gate_result = _post_final_gate(session, final_page.url or target_final_candidate, final_page.text or "", solver_url, timeout, timeline)
        gate_result.update({
            "decoded_query": decoded,
            "target_final_candidate": target_final_candidate,
            "timeline": timeline,
            "waited_seconds": round(time.time() - started, 2),
        })
        return gate_result
    except Exception as exc:
        return {"status": 0, "stage": "exception", "message": str(exc), "timeline": timeline, "waited_seconds": round(time.time() - started, 2)}


def main() -> int:
    parser = argparse.ArgumentParser(description="HTTP-first GPLinks / PowerGam probe")
    parser.add_argument("url")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--solver-url", default="http://127.0.0.1:5000")
    args = parser.parse_args()
    payload = run(args.url, args.timeout, args.solver_url)
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload.get("status") == 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
