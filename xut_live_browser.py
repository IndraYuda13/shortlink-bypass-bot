#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

import undetected_chromedriver as uc
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
FLARESOLVERR_SRC = WORKSPACE_ROOT / "state" / "flaresolverr-exp" / "src" / "src"
FLARESOLVERR_SITE_PACKAGES = [
    WORKSPACE_ROOT / "state" / "flaresolverr-exp" / "src" / ".venv" / "lib" / "python3.12" / "site-packages",
    WORKSPACE_ROOT / "state" / "flaresolverr-exp" / "src" / ".venv" / "lib64" / "python3.12" / "site-packages",
]
for site_path in FLARESOLVERR_SITE_PACKAGES:
    if site_path.exists() and str(site_path) not in sys.path:
        sys.path.insert(0, str(site_path))
if str(FLARESOLVERR_SRC) not in sys.path:
    sys.path.insert(0, str(FLARESOLVERR_SRC))
ICONCAPTCHA_SOLVER_SRC = WORKSPACE_ROOT / "projects" / "claimcoin-autoclaim" / "src"
if ICONCAPTCHA_SOLVER_SRC.exists() and str(ICONCAPTCHA_SOLVER_SRC) not in sys.path:
    sys.path.insert(0, str(ICONCAPTCHA_SOLVER_SRC))

from claimcoin_autoclaim.iconcaptcha_solver import solve_iconcaptcha_data_url
from dtos import V1RequestBase  # type: ignore
from flaresolverr_service import _controller_v1_handler  # type: ignore

FINAL_PREFIX = "https://onlyfaucet.com/links/back/"
DEFAULT_TIMEOUT = 300
CHROME_PATH = "/usr/bin/google-chrome" if Path("/usr/bin/google-chrome").exists() else "/usr/bin/google-chrome-stable"


def detect_chrome_major() -> int | None:
    try:
        output = subprocess.check_output([CHROME_PATH, "--version"], text=True, timeout=10)
    except Exception:
        return None
    match = re.search(r"(\d+)\.", output)
    return int(match.group(1)) if match else None


ENV_TEXT = Path("/etc/indra-api-hub.env").read_text()
ENV_MATCH = re.search(r"^INDRA_API_KEYS=(.*)$", ENV_TEXT, re.M)
RAW_KEYS = ENV_MATCH.group(1).strip().strip('"').strip("'") if ENV_MATCH else ""
FIRST_KEY = [p.strip() for p in re.split(r"[\n,]+", RAW_KEYS) if p.strip()][0]
API_KEY = FIRST_KEY.split(":", 1)[1] if ":" in FIRST_KEY else FIRST_KEY


def solve_canvas_via_local_api(canvas_data_url: str) -> dict:
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:5001/api/v1/iconcaptcha/solve",
            data=json.dumps({"canvas_data_url": canvas_data_url}).encode(),
            headers={"Content-Type": "application/json", "X-API-Key": API_KEY, "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())["result"]
            data.setdefault("provider", "api")
            return data
    except Exception as api_exc:
        result = solve_iconcaptcha_data_url(canvas_data_url, similarity_threshold=20.0).to_dict()
        result["provider"] = "local-python"
        result["api_error"] = str(api_exc)
        return result


def body_text(driver) -> str:
    try:
        return driver.find_element(By.TAG_NAME, "body").text[:5000]
    except Exception:
        return ""


def wait_for(predicate, timeout: float = 60.0, interval: float = 0.5):
    end = time.time() + timeout
    last = None
    while time.time() < end:
        last = predicate()
        if last:
            return last
        time.sleep(interval)
    return last


def click_button_contains(driver, text: str) -> str | None:
    lower = text.lower()
    for el in driver.find_elements(By.CSS_SELECTOR, "a,button"):
        txt = (el.text or "").strip().lower()
        if lower in txt:
            driver.execute_script('arguments[0].scrollIntoView({block:"center"});', el)
            time.sleep(0.2)
            el.click()
            return txt
    return None


def snap(driver, label: str) -> dict:
    success = driver.execute_script("const el=document.querySelector('#challenge-success-text'); return el ? el.innerText : null;")
    hidden = driver.execute_script("const el=document.querySelector('input[name=\"cf-turnstile-response\"]'); return el ? el.value : null;")
    return {
        "label": label,
        "url": driver.current_url,
        "host": urlparse(driver.current_url).netloc,
        "title": driver.title,
        "body": body_text(driver),
        "successText": success,
        "hiddenValue": hidden,
        "cookies": sorted(c["name"] for c in driver.get_cookies()),
    }


def save_iconcaptcha_capture(capture_dir: Path | None, canvas_data_url: str, solver: dict, attempt: int, passed: bool, title: str, body: str) -> str | None:
    if not capture_dir:
        return None
    capture_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time() * 1000)
    stem = f"xut_autodime_{ts}_attempt{attempt}_{'pass' if passed else 'fail'}"
    image_path = capture_dir / f"{stem}.png"
    label_path = capture_dir / "labels.jsonl"
    payload = canvas_data_url.split(",", 1)[1]
    image_path.write_bytes(base64.b64decode(payload))
    row = {
        "image": image_path.name,
        "attempt": attempt,
        "passed": passed,
        "selected_cell_number": solver.get("selected_cell_number"),
        "selected_cell_index": solver.get("selected_cell_index"),
        "click_x": solver.get("click_x"),
        "click_y": solver.get("click_y"),
        "confidence": solver.get("confidence"),
        "groups": solver.get("groups"),
        "pairwise_mad": solver.get("pairwise_mad"),
        "title": title,
        "body_excerpt": body[:500],
    }
    with label_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return str(image_path)


def solve_step1_until_step2(driver, max_attempts: int = 6, capture_dir: Path | None = None) -> tuple[bool, int | None, list[dict]]:
    history: list[dict] = []
    wait_for(lambda: "Step 1/6" in driver.title or "Step 1/6" in driver.page_source, timeout=120)
    time.sleep(12)
    for attempt in range(1, max_attempts + 1):
        if "Step 2/6" in driver.title or "Step 2" in body_text(driver):
            return True, attempt - 1 if attempt > 1 else 1, history
        widget = driver.find_element(By.CSS_SELECTOR, ".iconcaptcha-widget")
        driver.execute_script('arguments[0].scrollIntoView({block:"center"});', widget)
        time.sleep(0.5)
        try:
            widget.click()
        except Exception:
            ActionChains(driver).move_to_element(widget).click().perform()
        time.sleep(4)
        canvas_data = driver.execute_script("const c=document.querySelector('canvas'); return c ? c.toDataURL('image/png') : null;")
        if not canvas_data:
            history.append({"attempt": attempt, "message": "canvas missing"})
            time.sleep(2)
            continue
        solver = solve_canvas_via_local_api(canvas_data)
        canvas = driver.find_element(By.CSS_SELECTOR, "canvas")
        rect = canvas.rect
        ox = solver["click_x"] - rect["width"] / 2
        oy = solver["click_y"] - rect["height"] / 2
        ActionChains(driver).move_to_element_with_offset(canvas, ox, oy).click().perform()
        time.sleep(6)
        current_body = body_text(driver)
        passed = "Step 2/6" in driver.title or "Step 2" in current_body
        capture_path = save_iconcaptcha_capture(capture_dir, canvas_data, solver, attempt, passed, driver.title, current_body)
        history.append({"attempt": attempt, "solver": solver, "title": driver.title, "body": current_body, "capture_path": capture_path, "passed": passed})
        if passed:
            return True, attempt, history
    return False, None, history


def continue_through_steps(driver):
    for button_text, expected_marker, timeout in [
        ("continue to step 3", "Step 3/6", 20),
        ("continue to step 4", "Step 4/6", 25),
        ("continue to step 5", "gamescrate.app", 20),
    ]:
        wait_for(lambda: button_text.lower() in body_text(driver).lower(), timeout=timeout, interval=1)
        click_button_contains(driver, button_text)
        wait_for(
            lambda: expected_marker in driver.title or expected_marker in driver.current_url or expected_marker.lower() in body_text(driver).lower(),
            timeout=45,
            interval=1,
        )


def fs_eval(session_id: str) -> dict:
    ev = _controller_v1_handler(
        V1RequestBase(
            {
                "cmd": "request.evaluate",
                "session": session_id,
                "javaScript": "return {url: location.href, title: document.title, body: document.body.innerText.slice(0, 2500), successText: (document.querySelector('#challenge-success-text')||{}).innerText || null, hiddenValue: (document.querySelector('input[name=\\'cf-turnstile-response\\']')||{}).value || null, cookies: document.cookie};",
            }
        )
    )
    return json.loads(ev.solution.response)


def fs_get(session_id: str, url: str, timeout_ms: int) -> dict:
    res = _controller_v1_handler(
        V1RequestBase(
            {
                "cmd": "request.get",
                "session": session_id,
                "url": url,
                "reuseCurrentPage": True,
                "maxTimeout": timeout_ms,
                "waitInSeconds": 5,
            }
        )
    )
    return {
        "status": res.status,
        "message": res.message,
        "url": res.solution.url if res.solution else None,
        "userAgent": res.solution.userAgent if res.solution else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--iconcaptcha-capture-dir", type=Path, default=None)
    args = parser.parse_args()

    opts = uc.ChromeOptions()
    opts.binary_location = CHROME_PATH
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1400,1000")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--lang=en-US")
    opts.add_argument("--headless=new")

    chrome_major = detect_chrome_major()
    driver = uc.Chrome(options=opts, use_subprocess=True, headless=True, version_main=chrome_major)
    session_id = f"xut-live-{int(time.time())}"
    result: dict = {
        "status": 0,
        "message": "LIVE_BROWSER_START",
        "stage": "init",
        "facts": {},
        "blockers": [],
        "notes": [],
    }

    try:
        driver.get(args.url)
        ok, step1_attempt, step1_history = solve_step1_until_step2(driver, capture_dir=args.iconcaptcha_capture_dir)
        result["facts"]["step1_success_attempt"] = step1_attempt
        result["facts"]["step1_history"] = step1_history[-3:]
        if not ok:
            result["message"] = "ICONCAPTCHA_STEP1_FAILED"
            result["stage"] = "step1-iconcaptcha"
            result["blockers"].append("helper live browser gagal melewati Step 1 pada run ini")
            print(json.dumps(result, ensure_ascii=False))
            return 0

        continue_through_steps(driver)
        wait_for(lambda: "gamescrate.app" in driver.current_url or "Just a moment" in driver.title, timeout=60, interval=1)
        time.sleep(8)
        result["facts"]["pre_handoff"] = snap(driver, "pre-handoff")
        debugger_address = getattr(getattr(driver, "options", None), "debugger_address", None)
        result["facts"]["debugger_address"] = debugger_address

        _controller_v1_handler(
            V1RequestBase(
                {
                    "cmd": "sessions.create",
                    "session": session_id,
                    "debuggerAddress": debugger_address,
                    "keepAttachedBrowserAlive": True,
                }
            )
        )

        attempts: list[dict] = []
        for idx, timeout_ms in enumerate([45000, 45000], start=1):
            row = {"idx": idx, "timeout_ms": timeout_ms}
            try:
                row["request"] = fs_get(session_id, driver.current_url, timeout_ms)
            except Exception as exc:
                row["request_error"] = str(exc)
            row["eval"] = fs_eval(session_id)
            row["driver"] = snap(driver, f"after-fs-attempt-{idx}")
            attempts.append(row)

            final_url = row["eval"].get("url") or row.get("request", {}).get("url")
            if final_url and final_url.startswith(FINAL_PREFIX):
                result["status"] = 1
                result["message"] = "XUT_FINAL_OK"
                result["stage"] = "final-bypass"
                result["bypass_url"] = final_url
                result["facts"]["attempts"] = attempts
                result["notes"].append("final oracle tercapai lewat warm browser handoff + FlareSolverr attach")
                print(json.dumps(result, ensure_ascii=False))
                return 0

        try:
            _controller_v1_handler(
                V1RequestBase(
                    {
                        "cmd": "request.evaluate",
                        "session": session_id,
                        "javaScript": "location.reload(); return true;",
                    }
                )
            )
        except Exception as exc:
            result["facts"]["reload_error"] = str(exc)
        time.sleep(10)
        after_reload = fs_eval(session_id)
        result["facts"]["attempts"] = attempts
        result["facts"]["after_reload"] = after_reload
        result["facts"]["after_reload_driver"] = snap(driver, "after-reload")

        final_url = after_reload.get("url")
        if final_url and final_url.startswith(FINAL_PREFIX):
            result["status"] = 1
            result["message"] = "XUT_FINAL_OK"
            result["stage"] = "final-bypass"
            result["bypass_url"] = final_url
            result["notes"].append("final oracle tercapai sesudah refresh di session yang sama")
            print(json.dumps(result, ensure_ascii=False))
            return 0

        result["message"] = "GAMESCRATE_HANDOFF_PROGRESS_ONLY"
        result["stage"] = "gamescrate-cloudflare"
        result["blockers"] = [
            "warm browser handoff sudah bekerja tetapi gamescrate belum redirect ke final oracle",
            "Cloudflare/backend gamescrate masih berhenti setelah state verifying/waiting-for-response",
        ]
        result["notes"] = [
            "helper sudah melewati Step 1 autodime dan berhasil handoff ke FlareSolverr attach mode",
            "state verify berhasil bergerak, tetapi downstream final onlyfaucet belum keluar",
        ]
        print(json.dumps(result, ensure_ascii=False))
        return 0
    finally:
        try:
            _controller_v1_handler(V1RequestBase({"cmd": "sessions.destroy", "session": session_id}))
        except Exception:
            pass
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
