#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

import undetected_chromedriver as uc
from curl_cffi import requests as curl_requests

from gplinks_live_browser import (
    CHROME_PATH,
    GPLINKS_EARLY_CONTINUE_SECONDS,
    GPLINKS_HOSTS,
    POWERGAM_HOSTS,
    click_next_powergam,
    collect_network_ledger_events,
    decoded_power_query,
    install_gpt_lifecycle_probe,
    install_network_ledger_recorder,
    install_pre_navigation_recorders,
    state,
    unlock_final_gate,
    wait_document_ready,
    wait_not_cloudflare,
    wait_powergam_continue_ready,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT = PROJECT_ROOT / "artifacts" / "active" / "gplinks-links-go-cdp-latest.json"


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
    opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})
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


def drain_perf(driver, bucket: list[dict], label: str):
    try:
        logs = driver.get_log("performance")
    except Exception as exc:
        bucket.append({"label": label, "error": str(exc)})
        return
    for item in logs:
        try:
            msg = json.loads(item.get("message") or "{}")
            inner = msg.get("message") or {}
            method = inner.get("method") or ""
            params = inner.get("params") or {}
            url = ((params.get("request") or {}).get("url") or (params.get("response") or {}).get("url") or params.get("documentURL") or "")
            if method.endswith("ExtraInfo") or any(host in url for host in ["gplinks", "powergam", "tracki", "googlesyndication", "doubleclick", "google.com"]):
                bucket.append({"label": label, "method": method, "params": params})
        except Exception:
            pass


def summarize(events: list[dict]) -> list[dict]:
    request_urls: dict[str, str] = {}
    for ev in events:
        params = ev.get("params") or {}
        req = params.get("request") or {}
        res = params.get("response") or {}
        url = req.get("url") or res.get("url") or params.get("documentURL") or ""
        if url and params.get("requestId"):
            request_urls[params["requestId"]] = url
    rows = []
    for ev in events:
        params = ev.get("params") or {}
        req = params.get("request") or {}
        res = params.get("response") or {}
        url = req.get("url") or res.get("url") or params.get("documentURL") or request_urls.get(params.get("requestId") or "") or ""
        if not url:
            continue
        rows.append({
            "label": ev.get("label"),
            "event": ev.get("method"),
            "request_id": params.get("requestId"),
            "loader_id": params.get("loaderId"),
            "type": params.get("type"),
            "url": url,
            "request_method": req.get("method"),
            "status": res.get("status"),
            "request_headers": req.get("headers"),
            "response_headers": res.get("headers"),
            "extra_headers": params.get("headers"),
            "blocked_cookies": params.get("blockedCookies"),
            "associated_cookies": params.get("associatedCookies"),
            "post_data": req.get("postData"),
            "initiator": params.get("initiator"),
        })
    return rows


def run(url: str, solver_url: str, timeout: int):
    started = time.time()
    events: list[dict] = []
    timeline: list[dict] = []
    session = curl_requests.Session(impersonate="chrome136")
    entry = session.get(url, timeout=40, allow_redirects=False)
    power_url = entry.headers.get("location") or ""
    decoded = decoded_power_query(power_url) if power_url else {}
    driver = build_driver()
    try:
        driver.execute_cdp_cmd("Network.enable", {})
        timeline.append({"stage": "pre-navigation-recorders", **install_pre_navigation_recorders(driver)})
        drain_perf(driver, events, "start")
        driver.get(url)
        install_gpt_lifecycle_probe(driver)
        install_network_ledger_recorder(driver)
        wait_document_ready(driver, 25)
        drain_perf(driver, events, "after-entry")
        timeline.append(state(driver, "entry"))
        if urlparse(driver.current_url).netloc.lower() not in POWERGAM_HOSTS:
            driver.execute_cdp_cmd("Network.setExtraHTTPHeaders", {"headers": {"Referer": url}})
            driver.get(power_url)
            install_gpt_lifecycle_probe(driver)
            install_network_ledger_recorder(driver)
            wait_document_ready(driver, 25)
            drain_perf(driver, events, "after-power-nav")
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
                break
            last_click = click_next_powergam(driver)
            timeline.append({"stage": "power-click", **last_click})
            drain_perf(driver, events, f"after-power-click-{len([x for x in timeline if x.get('stage') == 'power-click'])}")
            wait_left = last_click.get("waitLeft")
            if isinstance(wait_left, (int, float)) and wait_left > 0:
                timeline.append(wait_powergam_continue_ready(driver, min(float(wait_left) + 0.5, 16.0), interval=0.25, early_continue_seconds=GPLINKS_EARLY_CONTINUE_SECONDS))
            else:
                wait_document_ready(driver, 4, interval=0.3)
            drain_perf(driver, events, "after-power-wait")
        candidate = wait_not_cloudflare(driver, 35)
        candidate["stage"] = "candidate"
        timeline.append(candidate)
        drain_perf(driver, events, "candidate")
        unlock = unlock_final_gate(driver, solver_url, max(60, timeout - int(time.time() - started)))
        timeline.extend(unlock.get("actions") or [])
        drain_perf(driver, events, "after-unlock")
        timeline.append(collect_network_ledger_events(driver, "final-network-ledger"))
        final_state = state(driver, "final")
        timeline.append(final_state)
        rows = summarize(events)
        payload = {
            "url": url,
            "decoded_query": decoded,
            "candidate_href": candidate.get("href"),
            "unlock_final_href": unlock.get("final_href"),
            "status": 1 if unlock.get("final_href") else 0,
            "waited_seconds": round(time.time() - started, 1),
            "timeline_tail": timeline[-18:],
            "events": rows,
        }
        OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"out": str(OUT), "status": payload["status"], "candidate_href": payload["candidate_href"], "final_href": payload["unlock_final_href"], "events": len(rows), "waited_seconds": payload["waited_seconds"]}, ensure_ascii=False))
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    run("https://gplinks.co/YVTC", "http://127.0.0.1:5000", 320)
