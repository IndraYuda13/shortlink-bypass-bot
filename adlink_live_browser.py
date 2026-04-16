from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import undetected_chromedriver as uc
from selenium.common.exceptions import TimeoutException, WebDriverException

CHALLENGE_TITLES = {"just a moment...", "attention required! | cloudflare"}
GOOGLE_HOSTS = {"www.google.com", "google.com"}
ADLINK_HOSTS = {"link.adlink.click", "adlink.click", "www.adlink.click", "blog.adlink.click"}


def detect_chrome_path() -> str:
    for candidate in [
        "/usr/bin/google-chrome-stable",
        "/usr/bin/google-chrome",
        "/bin/google-chrome",
    ]:
        if Path(candidate).exists():
            return candidate
    raise FileNotFoundError("chrome executable tidak ketemu")


def detect_chrome_major(path: str) -> int | None:
    try:
        out = subprocess.check_output([path, "--product-version"], text=True, timeout=10).strip()
    except Exception:
        return None
    match = re.match(r"(\d+)", out)
    return int(match.group(1)) if match else None


def decode_google_redirect(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc.lower() not in GOOGLE_HOSTS or parsed.path != "/url":
        return url
    qs = parse_qs(parsed.query)
    return qs.get("url", [url])[0]


def prepare_driver_copy(workdir: Path) -> str | None:
    candidates = [
        Path.home() / ".local/share/undetected_chromedriver/undetected_chromedriver",
        Path.home() / ".local/share/undetected_chromedriver/undetected/chromedriver-linux64/chromedriver",
    ]
    for candidate in candidates:
        if candidate.exists():
            target = workdir / "undetected_chromedriver"
            shutil.copy2(candidate, target)
            target.chmod(0o755)
            return str(target)
    return None


def cookie_names(driver) -> list[str]:
    return sorted(cookie["name"] for cookie in driver.get_cookies())


def append_timeline(driver, timeline: list[dict], started_at: float) -> dict:
    current_url = decode_google_redirect(driver.current_url)
    title = driver.title or ""
    ready_state = driver.execute_script("return document.readyState")
    row = {
        "t": round(time.time() - started_at, 1),
        "url": current_url,
        "title": title,
        "ready_state": ready_state,
        "cookie_names": cookie_names(driver),
    }
    timeline.append(row)
    return row


def wait_for_external_host(driver, input_host: str, end_at: float, timeline: list[dict], started_at: float) -> str:
    candidate_url = None
    candidate_since = None
    while time.time() < end_at:
        row = append_timeline(driver, timeline, started_at)
        current_url = row["url"]
        host = urlparse(current_url).netloc.lower()
        title = row["title"].strip().lower()
        challenge = title in CHALLENGE_TITLES or host in {"", input_host} | GOOGLE_HOSTS
        if not challenge and host:
            if candidate_url != current_url:
                candidate_url = current_url
                candidate_since = time.time()
            elif candidate_since and time.time() - candidate_since >= 2:
                return current_url
        else:
            candidate_url = None
            candidate_since = None
        time.sleep(1)
    return decode_google_redirect(driver.current_url)


def settle_page(driver, end_at: float, timeline: list[dict], started_at: float, seconds: int = 3) -> None:
    until = min(end_at, time.time() + seconds)
    while time.time() < until:
        append_timeline(driver, timeline, started_at)
        time.sleep(1)


def get_skip_button(driver) -> dict | None:
    return driver.execute_script(
        """
        const b = document.getElementById('skip-btn');
        if (!b) return null;
        return {
          href: b.href || null,
          text: (b.textContent || '').trim(),
          display: getComputedStyle(b).display
        };
        """
    )


def navigate_in_page(driver, url: str) -> None:
    driver.execute_script("window.location.href = arguments[0];", url)


def fetch_verify_json(driver) -> dict:
    return driver.execute_async_script(
        """
        const done = arguments[0];
        fetch('verify.php', {credentials: 'same-origin'})
          .then(async response => {
            const text = await response.text();
            let data = null;
            try { data = JSON.parse(text); } catch (error) {}
            done({status: response.status, text, data});
          })
          .catch(error => done({error: String(error)}));
        """
    )


def wait_for_blog_target(driver, end_at: float, timeline: list[dict], started_at: float) -> dict:
    last_target = None
    while time.time() < end_at:
        append_timeline(driver, timeline, started_at)
        target = driver.execute_script(
            """
            const link = document.querySelector('a.get-link');
            const form = document.querySelector('form.go-link');
            return {
              current_url: window.location.href,
              title: document.title || '',
              target_url: link ? link.href : null,
              target_text: link ? (link.textContent || '').trim() : null,
              form_action: form ? form.getAttribute('action') : null,
              ad_form_data_present: !!(form && form.querySelector('input[name="ad_form_data"]'))
            };
            """
        )
        last_target = target
        target_url = (target.get("target_url") or "").strip()
        if target_url.startswith("http://") or target_url.startswith("https://"):
            return target
        time.sleep(0.5)
    if last_target:
        return last_target
    return {
        "current_url": decode_google_redirect(driver.current_url),
        "title": driver.title or "",
        "target_url": None,
        "target_text": None,
        "form_action": None,
        "ad_form_data_present": False,
    }


def submit_blog_form(driver) -> dict:
    return driver.execute_async_script(
        """
        const done = arguments[0];
        const form = document.querySelector('form#go-link');
        if (!form) {
          return done({status: 0, message: 'blog form missing'});
        }
        const fd = new FormData(form);
        fetch(form.action, {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
          },
          body: new URLSearchParams(fd),
        }).then(async response => {
          const text = await response.text();
          let data = null;
          try { data = JSON.parse(text); } catch (error) {}
          done({status: response.status, text, data});
        }).catch(error => done({status: 0, message: String(error)}));
        """
    )


def attempt_blog_form_submit(
    driver,
    end_at: float,
    timeline: list[dict],
    started_at: float,
    blog_wait_seconds: float = 4.0,
) -> dict | None:
    lane_end = min(end_at, time.time() + 8)
    lane_started = time.time()
    last_meta = None

    while time.time() < lane_end:
        append_timeline(driver, timeline, started_at)
        meta = driver.execute_script(
            """
            const form = document.querySelector('form#go-link');
            const link = document.querySelector('a.get-link');
            return {
              current_url: window.location.href,
              title: document.title || '',
              form_action: form ? form.getAttribute('action') : null,
              ad_form_data_present: !!(form && form.querySelector('input[name="ad_form_data"]')),
              target_url: link ? link.href : null,
              target_text: link ? (link.textContent || '').trim() : null,
            };
            """
        )
        last_meta = meta
        target_url = (meta.get("target_url") or "").strip()
        if target_url.startswith("http://") or target_url.startswith("https://"):
            return {
                "status": 1,
                "stage": "blog-fast-final",
                "final_url": meta.get("current_url") or decode_google_redirect(driver.current_url),
                "final_title": meta.get("title") or driver.title or "",
                "bypass_url": target_url,
                "target_text": meta.get("target_text"),
                "blog_form_action": meta.get("form_action"),
                "blog_ad_form_data_present": meta.get("ad_form_data_present"),
                "fast_lane": "direct-blog-anchor",
            }

        if meta.get("ad_form_data_present") and time.time() - lane_started >= blog_wait_seconds:
            submit = submit_blog_form(driver)
            data = submit.get("data") if isinstance(submit.get("data"), dict) else {}
            bypass_url = (data.get("url") or "").strip() if isinstance(data, dict) else ""
            if bypass_url.startswith("http://") or bypass_url.startswith("https://"):
                return {
                    "status": 1,
                    "stage": "blog-form-submit",
                    "final_url": meta.get("current_url") or decode_google_redirect(driver.current_url),
                    "final_title": meta.get("title") or driver.title or "",
                    "bypass_url": bypass_url,
                    "target_text": meta.get("target_text") or data.get("message") or "Get Link",
                    "blog_form_action": meta.get("form_action"),
                    "blog_ad_form_data_present": meta.get("ad_form_data_present"),
                    "fast_lane": "direct-blog-submit",
                    "blog_submit_payload": data,
                }
        time.sleep(0.5)

    if last_meta:
        return {
            "status": 0,
            "stage": "blog-form-submit-timeout",
            "final_url": last_meta.get("current_url") or decode_google_redirect(driver.current_url),
            "final_title": last_meta.get("title") or driver.title or "",
            "target_text": last_meta.get("target_text"),
            "blog_form_action": last_meta.get("form_action"),
            "blog_ad_form_data_present": last_meta.get("ad_form_data_present"),
        }
    return None


def attempt_fast_blog_lane(
    driver,
    end_at: float,
    timeline: list[dict],
    started_at: float,
    blog_url: str | None,
) -> dict | None:
    if not blog_url:
        return None
    navigate_in_page(driver, blog_url)
    fast_submit = attempt_blog_form_submit(driver, end_at, timeline, started_at)
    if fast_submit and fast_submit.get("status") == 1 and fast_submit.get("bypass_url"):
        return fast_submit

    target = wait_for_blog_target(driver, min(end_at, time.time() + 6), timeline, started_at)
    target_url = (target.get("target_url") or "").strip()
    valid_target = target_url.startswith("http://") or target_url.startswith("https://")
    if not valid_target:
        return fast_submit
    return {
        "status": 1,
        "stage": "blog-fast-final",
        "final_url": target.get("current_url") or decode_google_redirect(driver.current_url),
        "final_title": target.get("title") or driver.title or "",
        "bypass_url": target_url,
        "target_text": target.get("target_text"),
        "blog_form_action": target.get("form_action"),
        "blog_ad_form_data_present": target.get("ad_form_data_present"),
        "fast_lane": "direct-blog-after-cloudflare",
    }


def run_maqal360_chain(
    driver,
    end_at: float,
    timeline: list[dict],
    started_at: float,
    fallback_blog_url: str | None = None,
) -> dict:
    steps: list[dict] = []

    for step_no in range(1, 10):
        wait_left = min(end_at - time.time(), 12)
        if wait_left <= 0:
            break
        settle_page(driver, end_at, timeline, started_at, seconds=max(1, int(wait_left)))
        current_url = decode_google_redirect(driver.current_url)
        current_host = urlparse(current_url).netloc.lower()

        if current_host == "blog.adlink.click":
            target = wait_for_blog_target(driver, end_at, timeline, started_at)
            target_url = (target.get("target_url") or "").strip()
            valid_target = target_url.startswith("http://") or target_url.startswith("https://")
            return {
                "status": 1 if valid_target else 0,
                "stage": "blog-final" if valid_target else "blog-waiting-target",
                "final_url": target.get("current_url") or current_url,
                "final_title": target.get("title") or driver.title or "",
                "bypass_url": target_url if valid_target else None,
                "target_text": target.get("target_text"),
                "blog_form_action": target.get("form_action"),
                "blog_ad_form_data_present": target.get("ad_form_data_present"),
                "maqal360_steps": steps,
            }

        if not current_host.endswith("maqal360.com"):
            return {
                "status": 1,
                "stage": "external-hop",
                "final_url": current_url,
                "final_title": driver.title or "",
                "maqal360_steps": steps,
            }

        button = get_skip_button(driver)
        verify = fetch_verify_json(driver)
        verify_data = verify.get("data") if isinstance(verify.get("data"), dict) else {}
        verify_url = verify_data.get("url") if isinstance(verify_data, dict) else None
        step_row = {
            "step": step_no,
            "url": current_url,
            "button": button,
            "verify": {
                "status": verify.get("status"),
                "text": verify.get("text"),
                "url": verify_url,
            },
        }
        steps.append(step_row)

        if verify_url:
            navigate_in_page(driver, verify_url)
            settle_page(driver, end_at, timeline, started_at, seconds=4)
            continue

        if fallback_blog_url:
            step_row["fallback_blog_url"] = fallback_blog_url
            navigate_in_page(driver, fallback_blog_url)
            settle_page(driver, end_at, timeline, started_at, seconds=4)
            target = wait_for_blog_target(driver, end_at, timeline, started_at)
            target_url = (target.get("target_url") or "").strip()
            valid_target = target_url.startswith("http://") or target_url.startswith("https://")
            return {
                "status": 1 if valid_target else 0,
                "stage": "blog-final" if valid_target else "blog-waiting-target",
                "final_url": target.get("current_url") or decode_google_redirect(driver.current_url),
                "final_title": target.get("title") or driver.title or "",
                "bypass_url": target_url if valid_target else None,
                "target_text": target.get("target_text"),
                "blog_form_action": target.get("form_action"),
                "blog_ad_form_data_present": target.get("ad_form_data_present"),
                "maqal360_steps": steps,
            }

        return {
            "status": 0,
            "stage": "maqal360-verify-stalled",
            "message": f"verify.php tidak mengembalikan next URL di step {step_no}",
            "final_url": current_url,
            "final_title": driver.title or "",
            "maqal360_steps": steps,
        }

    return {
        "status": 0,
        "stage": "maqal360-chain-incomplete",
        "message": "chain maqal360 belum selesai sampai final target",
        "final_url": decode_google_redirect(driver.current_url),
        "final_title": driver.title or "",
        "maqal360_steps": steps,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--timeout", type=int, default=240)
    args = parser.parse_args()

    chrome_path = detect_chrome_path()
    chrome_major = detect_chrome_major(chrome_path)
    input_host = urlparse(args.url).netloc.lower()

    workdir = Path(tempfile.mkdtemp(prefix="adlink-live-"))
    profile_dir = workdir / "profile"
    profile_dir.mkdir(parents=True, exist_ok=True)

    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-setuid-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1366,900")
    options.add_argument("--lang=en-US")
    options.add_argument("--disable-search-engine-choice-screen")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
    )
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.page_load_strategy = "none"

    driver = None
    try:
        kwargs = {
            "options": options,
            "browser_executable_path": chrome_path,
            "headless": False,
            "use_subprocess": True,
        }
        driver_copy = prepare_driver_copy(workdir)
        if driver_copy:
            kwargs["driver_executable_path"] = driver_copy
        if chrome_major:
            kwargs["version_main"] = chrome_major

        driver = uc.Chrome(**kwargs)
        driver.set_page_load_timeout(20)
        try:
            driver.get(args.url)
        except TimeoutException:
            pass

        started_at = time.time()
        end_at = started_at + args.timeout
        timeline: list[dict] = []

        external_url = wait_for_external_host(driver, input_host, end_at, timeline, started_at)
        current_url = external_url or decode_google_redirect(driver.current_url)
        current_host = urlparse(current_url).netloc.lower()
        cookies = driver.get_cookies()
        cf_clearance_seen = any(cookie["name"] == "cf_clearance" for cookie in cookies)

        secure_url = None
        perf_matches: list[dict] = []

        payload = {
            "status": 1,
            "input_url": args.url,
            "external_url": external_url,
            "final_url": current_url,
            "final_title": driver.title or "",
            "cookie_names": cookie_names(driver),
            "cf_clearance_seen": cf_clearance_seen,
            "secure_url": secure_url,
            "timeline": timeline,
            "workdir": str(workdir),
            "performance_matches": perf_matches,
        }

        alias = urlparse(args.url).path.strip("/")
        fallback_blog_url = f"https://blog.adlink.click/{alias}" if alias else None

        fast_lane = attempt_fast_blog_lane(driver, end_at, timeline, started_at, fallback_blog_url)
        if fast_lane:
            payload.update(fast_lane)
        elif current_host.endswith("maqal360.com") or current_host == "blog.adlink.click":
            navigate_in_page(driver, current_url)
            settle_page(driver, end_at, timeline, started_at, seconds=2)
            payload.update(run_maqal360_chain(driver, end_at, timeline, started_at, fallback_blog_url))

        if not payload.get("bypass_url") and current_host == "blog.adlink.click":
            target = wait_for_blog_target(driver, end_at, timeline, started_at)
            target_url = (target.get("target_url") or "").strip()
            valid_target = target_url.startswith("http://") or target_url.startswith("https://")
            payload.update(
                {
                    "final_url": target.get("current_url") or payload.get("final_url"),
                    "final_title": target.get("title") or payload.get("final_title"),
                    "bypass_url": target_url if valid_target else payload.get("bypass_url"),
                    "target_text": target.get("target_text") or payload.get("target_text"),
                    "blog_form_action": target.get("form_action") or payload.get("blog_form_action"),
                    "blog_ad_form_data_present": target.get("ad_form_data_present") or payload.get("blog_ad_form_data_present"),
                }
            )
            if valid_target:
                payload["status"] = 1
                payload["stage"] = "blog-final"

        if not payload.get("bypass_url") and urlparse(payload.get("final_url") or "").netloc.lower() in {"", input_host}:
            payload["status"] = 0
            payload.setdefault("message", "browser tidak berhasil keluar dari host adlink")

        print(json.dumps(payload, ensure_ascii=False))
        return 0 if payload.get("status") == 1 else 1
    except (WebDriverException, FileNotFoundError) as exc:
        payload = {
            "status": 0,
            "input_url": args.url,
            "message": str(exc),
            "workdir": str(workdir),
        }
        print(json.dumps(payload, ensure_ascii=False))
        return 1
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
