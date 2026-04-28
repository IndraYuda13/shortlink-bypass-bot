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
FINAL_HOST_MARKERS = ("onlyfaucet.com", "tesskibidixxx.com")
DEFAULT_TIMEOUT = 300
XUT_FINAL_HOST_BLOCKLIST = {"xut.io", "gamescrate.app", "stiftais.top", "webtrafic.ru", "earnviv.com"}
CHROME_PATH = "/usr/bin/google-chrome" if Path("/usr/bin/google-chrome").exists() else "/usr/bin/google-chrome-stable"
XUT_GAMESCRATE_DWELL_SECONDS = float(os.getenv("SHORTLINK_BYPASS_XUT_GAMESCRATE_DWELL", "4"))
XUT_CLICK_FINAL_LINK = os.getenv("SHORTLINK_BYPASS_XUT_CLICK_FINAL", "0").strip().lower() in {"1", "true", "yes", "on"}


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


def is_final_url(url: str | None) -> bool:
    if not url:
        return False
    lowered = url.lower()
    return lowered.startswith(FINAL_PREFIX) or any(marker in lowered for marker in FINAL_HOST_MARKERS)


def click_ready_get_link(driver) -> dict:
    return driver.execute_script(
        """
        const els=[...document.querySelectorAll('a,button,input[type=submit]')];
        for (const el of els) {
          const txt=(el.innerText||el.value||el.textContent||'').trim().toLowerCase();
          const disabled=el.disabled||el.classList.contains('disabled')||txt.includes('please wait');
          if (txt==='get link' && !disabled) {
            el.scrollIntoView({block:'center'});
            el.click();
            return {clicked:true, text:txt, href:el.href||null, tag:el.tagName, id:el.id||null, className:el.className||null};
          }
        }
        return {clicked:false, buttons:els.map(el=>({text:(el.innerText||el.value||el.textContent||'').trim(), href:el.href||null, tag:el.tagName, id:el.id||null, className:el.className||null, disabled:el.disabled||el.classList.contains('disabled')})).slice(0,20)};
        """
    )


def wait_ready_get_link(driver, timeout: float = 150.0) -> dict:
    end = time.time() + timeout
    last = None
    while time.time() < end:
        last = driver.execute_script(
            """
            return [...document.querySelectorAll('a,button,input[type=submit]')]
              .map(el=>({text:(el.innerText||el.value||el.textContent||'').trim(), href:el.href||null, className:el.className||'', disabled:el.disabled||el.classList.contains('disabled')}))
              .filter(x=>x.text.toLowerCase().includes('get link')||x.text.toLowerCase().includes('please wait'));
            """
        )
        for item in last or []:
            if str(item.get('text', '')).strip().lower() == 'get link' and not item.get('disabled'):
                return {"ready": True, "buttons": last}
        time.sleep(1)
    return {"ready": False, "buttons": last or []}


def finish_gamescrate_and_xut(driver, result: dict) -> str | None:
    wait_for(lambda: "Open Final Page" in body_text(driver), timeout=120, interval=1)
    result["facts"]["gamescrate_open_final"] = snap(driver, "gamescrate-open-final")
    time.sleep(15)
    click_info = driver.execute_script(
        """
        const el=[...document.querySelectorAll('a,button')].find(e=>(e.innerText||'').trim().toLowerCase().includes('open final page'));
        if (!el) return {clicked:false};
        el.scrollIntoView({block:'center'});
        el.click();
        return {clicked:true, text:(el.innerText||'').trim(), id:el.id||null, className:el.className||null};
        """
    )
    result["facts"]["gamescrate_open_final_click"] = click_info
    time.sleep(3)
    result["facts"]["xut_step6_after_open_final"] = snap(driver, "xut-step6-after-open-final")
    ready = wait_ready_get_link(driver, timeout=160)
    result["facts"]["xut_get_link_ready"] = ready
    click_result = click_ready_get_link(driver)
    result["facts"]["xut_get_link_click"] = click_result
    final_url = click_result.get("href") if isinstance(click_result, dict) else None
    if is_final_url(final_url):
        return final_url
    for _ in range(90):
        if is_final_url(driver.current_url):
            return driver.current_url
        time.sleep(1)
    if is_final_url(driver.current_url):
        return driver.current_url
    return final_url if is_final_url(final_url) else None


def get_visible_exact_clickables(driver) -> list[dict]:
    return driver.execute_script(
        """
        return Array.from(document.querySelectorAll('a,button,input[type=submit],input[type=button]')).map((el)=>{
          const r=el.getBoundingClientRect(); const cs=getComputedStyle(el);
          return {
            tag: el.tagName,
            id: el.id || '',
            text: (el.innerText || el.value || '').trim(),
            href: el.href || '',
            visible: r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none',
            rect: [r.x, r.y, r.width, r.height],
          };
        });
        """
    )


def exact_visible_clickable_exists(driver, text: str) -> bool:
    wanted = text.strip().lower()
    return any(
        item.get("visible") and str(item.get("text") or "").strip().lower() == wanted
        for item in get_visible_exact_clickables(driver)
    )


def click_exact_visible(driver, text: str) -> str | None:
    return driver.execute_script(
        """
        const wanted = arguments[0].trim().toLowerCase();
        for (const el of Array.from(document.querySelectorAll('a,button,input[type=submit],input[type=button]'))) {
          const txt = (el.innerText || el.value || '').trim().toLowerCase();
          const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
          if (txt === wanted && r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none') {
            el.scrollIntoView({block:'center'});
            el.click();
            return txt;
          }
        }
        return null;
        """,
        text,
    )


def final_url_from_current_state(driver) -> str | None:
    current = driver.current_url
    host = urlparse(current).netloc.lower()
    if current.startswith("http") and host and not any(host == bad or host.endswith("." + bad) for bad in XUT_FINAL_HOST_BLOCKLIST):
        return current
    for item in get_visible_exact_clickables(driver):
        text = str(item.get("text") or "").strip().lower()
        href = str(item.get("href") or "").strip()
        host = urlparse(href).netloc.lower()
        if item.get("visible") and text == "get link" and href.startswith("http"):
            if not any(host == bad or host.endswith("." + bad) for bad in XUT_FINAL_HOST_BLOCKLIST):
                return href
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
    headless = os.getenv("SHORTLINK_BYPASS_XUT_HEADLESS", "0").strip().lower() in {"1", "true", "yes"}
    if headless:
        opts.add_argument("--headless=new")
    opts.page_load_strategy = "eager"

    chrome_major = detect_chrome_major()
    driver = uc.Chrome(options=opts, use_subprocess=True, headless=headless, version_main=chrome_major)
    driver.set_page_load_timeout(60)
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
        wait_for(lambda: "gamescrate.app" in driver.current_url or "Step 5/6" in driver.title or "Open Final Page" in body_text(driver), timeout=90, interval=1)
        result["facts"]["gamescrate_entry"] = snap(driver, "gamescrate-entry")

        wait_for(lambda: "Open Final Page" in body_text(driver), timeout=120, interval=1)
        result["facts"]["open_final_visible"] = snap(driver, "open-final-visible")
        time.sleep(max(0.0, XUT_GAMESCRATE_DWELL_SECONDS))
        result["facts"]["open_final_after_dwell"] = snap(driver, "open-final-after-dwell")
        result["facts"]["open_final_clicked"] = click_button_contains(driver, "open final page")
        time.sleep(3)
        result["facts"]["post_open_final"] = [snap(driver, "post-open-final")]

        for _ in range(80):
            final_url = final_url_from_current_state(driver)
            if final_url:
                result["facts"]["step6_clickables"] = get_visible_exact_clickables(driver)
                if XUT_CLICK_FINAL_LINK:
                    clicked = click_exact_visible(driver, "Get Link")
                    result["facts"]["get_link_clicked"] = clicked
                    if clicked:
                        time.sleep(5)
                        final_url = final_url_from_current_state(driver) or driver.current_url
                else:
                    result["facts"]["get_link_clicked"] = {"skipped": True, "reason": "visible Get Link href is already the downstream final oracle"}
                result["status"] = 1
                result["message"] = "XUT_FINAL_OK"
                result["stage"] = "final-bypass"
                result["bypass_url"] = final_url
                result["facts"]["final_state"] = snap(driver, "final-state")
                result["notes"].append("final oracle tercapai lewat direct browser: gamescrate Step 5 -> xut Step 6 -> exact Get Link")
                print(json.dumps(result, ensure_ascii=False))
                return 0
            time.sleep(1)

        result["facts"]["step6_or_final_state"] = snap(driver, "step6-or-final-state")
        result["facts"]["step6_clickables"] = get_visible_exact_clickables(driver)
        result["message"] = "XUT_STEP6_GETLINK_NOT_READY"
        result["stage"] = "xut-step6"
        result["blockers"] = [
            "gamescrate handoff sudah sampai xut Step 6 tetapi tombol final Get Link belum valid/terlihat pada run ini",
        ]
        result["notes"] = [
            "Step 1 IconCaptcha dan gamescrate Step 5 sudah ditembus pada lane direct browser",
        ]
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        result["status"] = 0
        result["message"] = f"XUT_HELPER_EXCEPTION: {exc}"
        result["stage"] = result.get("stage") or "live-browser-exception"
        try:
            result["facts"]["exception_state"] = snap(driver, "exception-state")
        except Exception as snap_exc:
            result["facts"]["exception_snap_error"] = str(snap_exc)
        result["blockers"].append("helper browser runtime exception before final oracle")
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
