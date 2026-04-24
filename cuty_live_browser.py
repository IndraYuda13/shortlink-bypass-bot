from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

import requests
from websocket import create_connection

GOOGLE_HOSTS = {"google.com", "www.google.com"}


def detect_chrome_path() -> str:
    for candidate in [
        "/usr/bin/google-chrome-stable",
        "/usr/bin/google-chrome",
        "/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ]:
        if Path(candidate).exists():
            return candidate
    found = shutil.which("google-chrome") or shutil.which("chromium")
    if found:
        return found
    raise FileNotFoundError("chrome executable tidak ketemu")


class CdpPage:
    def __init__(self, chrome_path: str, timeout: int):
        self.timeout = timeout
        self.port = 9240
        self.proc = subprocess.Popen(
            [
                chrome_path,
                "--headless=new",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--remote-allow-origins=*",
                f"--remote-debugging-port={self.port}",
                f"--user-data-dir={tempfile.mkdtemp(prefix='cuty-cdp-')}",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.ws = None
        self.msg_id = 0
        self.events: list[dict] = []

    def __enter__(self):
        deadline = time.time() + min(20, self.timeout)
        last_error = None
        while time.time() < deadline:
            try:
                tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json", timeout=1))
                pages = [item for item in tabs if item.get("type") == "page" and item.get("url") == "about:blank"]
                if pages:
                    self.ws = create_connection(pages[0]["webSocketDebuggerUrl"], timeout=5)
                    self.send("Network.enable")
                    self.send("Page.enable")
                    self.send("Runtime.enable")
                    return self
            except Exception as exc:
                last_error = exc
                time.sleep(0.2)
        raise RuntimeError(f"CDP page not ready: {last_error}")

    def __exit__(self, exc_type, exc, tb):
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            pass
        self.proc.terminate()
        try:
            self.proc.wait(timeout=3)
        except Exception:
            self.proc.kill()

    def send(self, method: str, params: dict | None = None) -> int:
        self.msg_id += 1
        assert self.ws is not None
        self.ws.send(json.dumps({"id": self.msg_id, "method": method, "params": params or {}}))
        return self.msg_id

    def _capture_event(self, msg: dict) -> None:
        method = msg.get("method", "")
        if method in {"Page.frameNavigated", "Runtime.consoleAPICalled"} or method.startswith("Network."):
            self.events.append(msg)

    def drain(self, seconds: float) -> None:
        assert self.ws is not None
        deadline = time.time() + seconds
        while time.time() < deadline:
            self.ws.settimeout(max(0.05, deadline - time.time()))
            try:
                msg = json.loads(self.ws.recv())
            except Exception:
                continue
            self._capture_event(msg)

    def eval(self, expression: str) -> dict:
        target = self.send("Runtime.evaluate", {"expression": expression, "returnByValue": True, "awaitPromise": False})
        assert self.ws is not None
        while True:
            msg = json.loads(self.ws.recv())
            self._capture_event(msg)
            if msg.get("id") == target:
                return msg.get("result", {}).get("result", {})

    def navigate(self, url: str) -> None:
        self.send("Page.navigate", {"url": url})


def solve_turnstile(solver_url: str, page_url: str, sitekey: str, timeout: int) -> str:
    task = requests.get(
        f"{solver_url.rstrip('/')}/turnstile",
        params={"url": page_url, "sitekey": sitekey},
        timeout=20,
    ).json()
    task_id = task.get("taskId")
    if not task_id:
        raise RuntimeError(f"solver did not return taskId: {task}")

    deadline = time.time() + timeout
    while time.time() < deadline:
        result = requests.get(f"{solver_url.rstrip('/')}/result", params={"id": task_id}, timeout=20).json()
        if result.get("status") == "ready":
            token = (result.get("solution") or {}).get("token")
            if token:
                return token
            raise RuntimeError(f"solver ready without token: {result}")
        if result.get("errorId"):
            raise RuntimeError(f"solver error: {result}")
        time.sleep(5)
    raise TimeoutError("solver timeout")


def state(page: CdpPage) -> dict:
    raw = page.eval(
        """({
          href: location.href,
          title: document.title,
          text: document.body ? document.body.innerText.slice(0, 600) : '',
          site: document.querySelector('.cf-turnstile')?.dataset.sitekey || null,
          forms: [...document.forms].map(f => ({id:f.id, action:f.action, data:new URLSearchParams(new FormData(f)).toString()})),
          buttons: [...document.querySelectorAll('button,input[type=submit],a')].slice(0, 16).map(x => ({tag:x.tagName,id:x.id,text:x.innerText||x.value||'',href:x.href||'',disabled:!!x.disabled}))
        })"""
    )
    return raw.get("value") or {}


def run(url: str, timeout: int, solver_url: str) -> dict:
    started = time.time()
    timeline: list[dict] = []
    with CdpPage(detect_chrome_path(), timeout) as page:
        page.navigate(url)
        page.drain(22)
        timeline.append({"stage": "entry", **state(page)})

        page.eval("document.querySelector('#submit-button')?.click()")
        page.drain(8)
        captcha_state = state(page)
        timeline.append({"stage": "captcha", **captcha_state})
        sitekey = captcha_state.get("site")
        if not sitekey:
            return {"status": 0, "stage": "captcha", "message": "Turnstile sitekey not found", "timeline": timeline}

        token = solve_turnstile(solver_url, captcha_state.get("href") or url, sitekey, max(60, timeout - int(time.time() - started)))
        page.eval(
            """(()=>{const token=%s; const f=document.querySelector('form'); if(!f) return false; let ta=document.querySelector('[name="cf-turnstile-response"]'); if(!ta){ta=document.createElement('textarea'); ta.name='cf-turnstile-response'; ta.style.display='none'; f.appendChild(ta)} ta.value=token; let b=document.querySelector('#submit-button'); if(b)b.disabled=false; return true;})()"""
            % json.dumps(token)
        )
        page.eval("document.querySelector('#submit-button')?.click()")
        page.drain(12)
        last_state = state(page)
        timeline.append({"stage": "last", **last_state})

        if not any((form.get("id") == "submit-form" and "/go/" in form.get("action", "")) for form in last_state.get("forms", [])):
            return {"status": 0, "stage": "last-page", "message": "final go form not found", "timeline": timeline}

        page.drain(4)
        page.eval("document.querySelector('#submit-form')?.submit()")
        page.drain(18)
        final_state = state(page)
        timeline.append({"stage": "final", **final_state})
        final_url = final_state.get("href") or ""
        host = urlparse(final_url).netloc.lower()
        if host in GOOGLE_HOSTS or (host and host not in {"cuty.io", "cuttlinks.com", "www.cuty.io", "www.cuttlinks.com"}):
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
        return {"status": 0, "stage": "final", "message": "final page did not leave cuty/cuttlinks", "final_url": final_url, "timeline": timeline}


def main() -> int:
    parser = argparse.ArgumentParser(description="Live browser helper for cuty.io/cuttlinks.com")
    parser.add_argument("url")
    parser.add_argument("--timeout", type=int, default=240)
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
