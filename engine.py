from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

try:
    from curl_cffi import requests as curl_requests
except Exception:
    curl_requests = None

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_TIMEOUT = 30
ADLINK_BROWSER_TIMEOUT = int(os.getenv("SHORTLINK_BYPASS_ADLINK_BROWSER_TIMEOUT", "240"))
ADLINK_HTTP_IMPERSONATE = os.getenv("SHORTLINK_BYPASS_ADLINK_IMPERSONATE", "chrome136")
ADLINK_LIVE_HELPER = os.getenv("SHORTLINK_BYPASS_ADLINK_HELPER", str(PROJECT_ROOT / "adlink_live_browser.py"))
HELPER_PYTHON = os.getenv("SHORTLINK_BYPASS_HELPER_PYTHON", sys.executable)
HELPER_PYTHONPATH = os.getenv("SHORTLINK_BYPASS_HELPER_PYTHONPATH", "")
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/135.0.0.0 Safari/537.36"
    )
}
URL_RE = re.compile(r"https?://[^\s'\"<>]+")


@dataclass
class BypassResult:
    status: int
    input_url: str
    family: str
    message: str
    bypass_url: str | None = None
    stage: str | None = None
    facts: dict[str, Any] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ShortlinkBypassEngine:
    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def analyze(self, url: str) -> BypassResult:
        host = urlparse(url).netloc.lower()
        parsed = urlparse(url)
        if host == "xut.io" or host.endswith(".xut.io"):
            return self._handle_autodime_cwsafelink(url)
        if host == "autodime.com" and parsed.path.startswith("/cwsafelinkphp/go.php"):
            return self._handle_autodime_cwsafelink(url)
        if host == "oii.la" or host.endswith(".oii.la"):
            return self._handle_oii(url)
        if host == "shrinkme.click" or host.endswith(".shrinkme.click"):
            return self._handle_shrinkme(url)
        if host == "link.adlink.click" or host.endswith(".adlink.click"):
            return self._handle_adlink_click(url)
        return BypassResult(
            status=0,
            input_url=url,
            family="unknown",
            message="UNSUPPORTED_FAMILY",
            blockers=[f"host {host} belum ada handler khusus"],
        )

    def _get(self, url: str) -> requests.Response:
        return self.session.get(url, timeout=self.timeout, allow_redirects=True)

    def _cookie_names(self) -> list[str]:
        return sorted({cookie.name for cookie in self.session.cookies})

    def _common_facts(self, response: requests.Response, soup: BeautifulSoup) -> dict[str, Any]:
        return {
            "final_url": response.url,
            "status_code": response.status_code,
            "title": (soup.title.string.strip() if soup.title and soup.title.string else None),
            "cookie_names": self._cookie_names(),
        }

    def _handle_autodime_cwsafelink(self, url: str) -> BypassResult:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        family = "autodime.cwsafelinkphp"
        facts: dict[str, Any] = {
            "entry_mode": "xut-wrapper" if host == "xut.io" or host.endswith(".xut.io") else "direct-go-url",
            "entry_host": host,
            "entry_path": parsed.path,
            "entry_query": parsed.query,
        }

        try:
            if facts["entry_mode"] == "xut-wrapper":
                entry = self.session.get(url, timeout=self.timeout, allow_redirects=False)
                facts["entry_status"] = entry.status_code
                facts["entry_redirect"] = self._clean_url(entry.headers.get("location", "")) or None
                facts["cookie_names_after_entry"] = self._cookie_names()
                go_url = facts["entry_redirect"] or ""
                referer = url
            else:
                go_url = url
                referer = url

            if not go_url:
                return BypassResult(
                    status=0,
                    input_url=url,
                    family=family,
                    message="ENTRY_REDIRECT_MISSING",
                    stage="entry-wrapper",
                    facts=facts,
                    blockers=["entry wrapper tidak memberi redirect ke lane go.php yang diharapkan"],
                )

            go = self.session.get(
                go_url,
                headers={"Referer": referer},
                timeout=self.timeout,
                allow_redirects=False,
            )
        except Exception as exc:
            return BypassResult(
                status=0,
                input_url=url,
                family=family,
                message="REQUEST_FAILED",
                stage="entry-wrapper",
                facts=facts,
                blockers=[str(exc)],
            )

        facts["go_url"] = go_url
        facts["go_status"] = go.status_code
        facts["go_redirect"] = self._clean_url(go.headers.get("location", "")) or None
        facts["cookie_names_after_go"] = self._cookie_names()

        fexkomin = self.session.cookies.get("fexkomin") or ""
        if fexkomin:
            facts["fexkomin_claims"] = self._decode_signed_json_cookie(fexkomin)

        google_target = self._decode_google_wrapper(facts.get("go_redirect") or "")
        facts["google_target"] = google_target
        home_url = google_target or "https://autodime.com/"

        try:
            home = self.session.get(
                home_url,
                headers={"Referer": "https://www.google.com/"},
                timeout=self.timeout,
                allow_redirects=True,
            )
        except Exception as exc:
            return BypassResult(
                status=0,
                input_url=url,
                family=family,
                message="HOME_FETCH_FAILED",
                stage="google-warmup",
                facts=facts,
                blockers=[str(exc)],
            )

        soup = BeautifulSoup(home.text, "html.parser")
        facts.update(self._common_facts(home, soup))
        runtime = self._extract_runtime_config(home.text)
        facts.update(runtime)

        form = soup.select_one("form#sl-form") or soup
        hidden = self._extract_hidden_inputs(form)
        facts["hidden_inputs"] = hidden
        facts["embedded_urls"] = self._collect_embedded_urls(home.text, hidden)
        facts["iconcaptcha_token_present"] = bool(hidden.get("_iconcaptcha-token"))

        blockers = [
            "step 1 masih berhenti di gate IconCaptcha",
            "hasil final downstream belum bisa diklaim sebelum stepwise captcha flow selesai",
        ]
        notes = [
            "xut.io diperlakukan sebagai wrapper menuju family autodime cwsafelinkphp",
            "warmup chain saat ini sudah bisa dipetakan sampai page Step 1/6 di autodime.com",
        ]

        if runtime.get("captchaProvider") == "iconcaptcha":
            notes.append("runtime gate yang aktif sekarang adalah IconCaptcha dengan countdown 10 detik")
        if facts.get("fexkomin_claims"):
            notes.append("cookie fexkomin membawa step dan sid pendek yang membantu mengikat alias wrapper ke state server")

        return BypassResult(
            status=0,
            input_url=url,
            family=family,
            message="ICONCAPTCHA_STEP1_MAPPED",
            stage="step1-iconcaptcha",
            facts=facts,
            blockers=blockers,
            notes=notes,
        )

    def _handle_oii(self, url: str) -> BypassResult:
        try:
            response = self._get(url)
        except Exception as exc:
            return BypassResult(
                status=0,
                input_url=url,
                family="oii.la",
                message="REQUEST_FAILED",
                blockers=[str(exc)],
            )

        soup = BeautifulSoup(response.text, "html.parser")
        facts = self._common_facts(response, soup)
        config = self._extract_runtime_config(response.text)
        facts.update(config)

        form = None
        for candidate in soup.find_all("form"):
            action = (candidate.get("action") or "").strip()
            if action:
                form = candidate
                break
        hidden = self._extract_hidden_inputs(form or soup)
        facts["form_action"] = (form.get("action") if form else None)
        facts["hidden_inputs"] = hidden

        embedded_urls = self._collect_embedded_urls(response.text, hidden)
        token_target = self._extract_oii_token_target(hidden.get("token", ""))
        preferred = token_target or self._pick_preferred_bypass_url(embedded_urls, input_url=url)
        facts["embedded_urls"] = embedded_urls
        facts["token_target"] = token_target

        if preferred:
            return BypassResult(
                status=1,
                input_url=url,
                family="oii.la",
                message="EMBEDDED_TARGET_EXTRACTED",
                bypass_url=preferred,
                stage="embedded-target",
                facts=facts,
                notes=[
                    "hasil ini berasal dari payload entry page, belum dari eksekusi captcha/timer live",
                    "untuk sample oii.la, target terkuat diambil dari hidden token yang didecode",
                ],
            )

        return BypassResult(
            status=0,
            input_url=url,
            family="oii.la",
            message="CAPTCHA_OR_TOKEN_FLOW_STILL_REQUIRED",
            stage="entry-mapped",
            facts=facts,
            blockers=[
                "belum ada embedded downstream URL yang bisa diangkat dengan yakin",
                "flow live tetap butuh timer + turnstile + verify/back execution",
            ],
        )

    def _handle_shrinkme(self, url: str) -> BypassResult:
        try:
            response = self._get(url)
        except Exception as exc:
            return BypassResult(
                status=0,
                input_url=url,
                family="shrinkme.click",
                message="REQUEST_FAILED",
                blockers=[str(exc)],
            )

        soup = BeautifulSoup(response.text, "html.parser")
        facts = self._common_facts(response, soup)
        config = self._extract_runtime_config(response.text)
        facts.update(config)
        hidden = self._extract_hidden_inputs(soup)
        facts["hidden_inputs"] = hidden

        embedded_urls = self._collect_embedded_urls(response.text, hidden)
        continue_hint = self._extract_shrinkme_continue_hint(response.text, url)
        if continue_hint and continue_hint not in embedded_urls:
            embedded_urls.append(continue_hint)
        facts["embedded_urls"] = embedded_urls
        facts["continue_hint"] = continue_hint

        direct_mrproblogger = self._resolve_shrinkme_direct_mrproblogger(url)
        if direct_mrproblogger:
            facts["mrproblogger_direct"] = direct_mrproblogger
            if direct_mrproblogger.get("bypass_url"):
                return BypassResult(
                    status=1,
                    input_url=url,
                    family="shrinkme.click",
                    message="MRPROBLOGGER_DIRECT_CHAIN_OK",
                    bypass_url=direct_mrproblogger.get("bypass_url"),
                    stage="mrproblogger-direct",
                    facts=facts,
                    notes=[
                        "shortcut cepat: alias shrinkme langsung dibuka ke MrProBlogger dengan referer ThemeZon, tanpa replay penuh ThemeZon article chain",
                        f"timer mrproblogger ditunggu {direct_mrproblogger.get('waited_seconds', 0)} detik sebelum submit final form",
                    ],
                )

        themezon = self._resolve_shrinkme_themezon(url, continue_hint)
        if themezon:
            facts["themezon"] = themezon
            article_url = themezon.get("article_url")
            if article_url and article_url not in embedded_urls:
                embedded_urls.append(article_url)
                facts["embedded_urls"] = embedded_urls
            mrproblogger = self._resolve_shrinkme_mrproblogger(
                input_url=url,
                continue_hint=continue_hint,
                article_url=article_url,
            )
            if mrproblogger:
                facts["mrproblogger"] = mrproblogger
                if mrproblogger.get("bypass_url"):
                    return BypassResult(
                        status=1,
                        input_url=url,
                        family="shrinkme.click",
                        message="THEMEZON_MRPROBLOGGER_CHAIN_OK",
                        bypass_url=mrproblogger.get("bypass_url"),
                        stage="themezon-mrproblogger",
                        facts=facts,
                        notes=[
                            "shrinkme direplay lewat continue hint ThemeZon lalu final form /links/go di MrProBlogger",
                            f"timer mrproblogger ditunggu {mrproblogger.get('waited_seconds', 0)} detik sebelum submit final form",
                        ],
                    )
            if article_url:
                blockers = [
                    "hasil yang ditemukan baru article/interstitial ThemeZon, belum downstream reward URL final",
                ]
                if mrproblogger and mrproblogger.get("message"):
                    blockers.append(f"mrproblogger lane belum selesai: {mrproblogger['message']}")
                return BypassResult(
                    status=0,
                    input_url=url,
                    family="shrinkme.click",
                    message="THEMEZON_ARTICLE_EXTRACTED",
                    bypass_url=article_url,
                    stage="themezon-hop",
                    facts=facts,
                    blockers=blockers,
                    notes=[
                        "themezon hop berhasil direplay via HTTP dengan referer shrinkme yang benar",
                        "bypass_url disimpan sebagai petunjuk intermediate, jangan diperlakukan sebagai hasil bypass final",
                    ],
                )

        if continue_hint:
            return BypassResult(
                status=0,
                input_url=url,
                family="shrinkme.click",
                message="ENTRY_MAPPED_CONTINUE_HINT_FOUND",
                stage="captcha-gated",
                facts=facts,
                blockers=[
                    "themezon hop belum berhasil direplay penuh",
                    "hasil final downstream reward URL masih belum terbukti",
                ],
                notes=["continue hint sudah kelihatan, tapi itu belum final downstream reward URL"],
            )

        return BypassResult(
            status=0,
            input_url=url,
            family="shrinkme.click",
            message="CAPTCHA_FLOW_NOT_YET_REPLAYED",
            stage="entry-mapped",
            facts=facts,
            blockers=[
                "reCAPTCHA flow belum diselesaikan",
                "continue URL belum bisa dipastikan dari HTML statis saja",
            ],
        )

    def _handle_adlink_click(self, url: str) -> BypassResult:
        try:
            response = self._get(url)
        except Exception as exc:
            return BypassResult(
                status=0,
                input_url=url,
                family="link.adlink.click",
                message="REQUEST_FAILED",
                blockers=[str(exc)],
            )

        soup = BeautifulSoup(response.text, "html.parser")
        facts = self._common_facts(response, soup)
        config = self._extract_runtime_config(response.text)
        facts.update(config)
        hidden = self._extract_hidden_inputs(soup)
        facts["hidden_inputs"] = hidden
        embedded_urls = self._collect_embedded_urls(response.text, hidden)
        preferred = self._pick_preferred_bypass_url(embedded_urls, input_url=url)
        facts["embedded_urls"] = embedded_urls

        if self._is_cloudflare_challenge(response):
            facts["cloudflare"] = True
            facts["challenge_type"] = "managed"
            facts["cf_ray"] = response.headers.get("cf-ray")
            facts["cf_mitigated"] = response.headers.get("cf-mitigated")

            http_fast = self._resolve_adlink_http(url)
            facts["http_impersonation"] = http_fast
            if http_fast.get("status") == 1 and http_fast.get("bypass_url"):
                notes = [
                    "hasil ini diambil tanpa Selenium, lewat HTTP TLS impersonation langsung ke blog.adlink.click",
                    "plain requests tetap kena Cloudflare, jadi lane cepat ini bergantung pada fingerprint client yang lebih mirip browser asli",
                ]
                return BypassResult(
                    status=1,
                    input_url=url,
                    family="link.adlink.click",
                    message="HTTP_IMPERSONATION_BYPASS_OK",
                    bypass_url=http_fast.get("bypass_url"),
                    stage=http_fast.get("stage") or "blog-http-fast",
                    facts=facts,
                    notes=notes,
                )

            live = self._resolve_adlink_live(url)
            facts["live_runner"] = "undetected-chromedriver-xvfb"
            facts["live_title"] = live.get("final_title")
            facts["live_cookie_names"] = live.get("cookie_names") or []
            facts["secure_url"] = live.get("secure_url")
            facts["cf_clearance_seen"] = bool(live.get("cf_clearance_seen"))
            facts["timeline"] = live.get("timeline") or []
            facts["live_stage"] = live.get("stage")
            facts["live_external_url"] = live.get("external_url")
            facts["blog_form_action"] = live.get("blog_form_action")
            facts["blog_ad_form_data_present"] = live.get("blog_ad_form_data_present")
            facts["target_text"] = live.get("target_text")
            facts["maqal360_steps"] = live.get("maqal360_steps") or []

            if live.get("status") == 1 and live.get("bypass_url"):
                notes = [
                    "hasil ini diambil dari browser live non-headless untuk menembus Cloudflare managed challenge",
                ]
                if (live.get("stage") or "") == "blog-fast-final":
                    notes.append("setelah Cloudflare clear, helper langsung lompat ke page blog.adlink.click dan ekstrak target final di sana")
                else:
                    notes.append("flow lanjut melewati rantai maqal360 lalu mengekstrak target akhir dari page blog.adlink.click")
                return BypassResult(
                    status=1,
                    input_url=url,
                    family="link.adlink.click",
                    message="LIVE_BROWSER_CHAIN_BYPASS_OK",
                    bypass_url=live.get("bypass_url"),
                    stage=live.get("stage") or "live-browser",
                    facts=facts,
                    notes=notes,
                )

            if live.get("status") == 1 and live.get("final_url"):
                return BypassResult(
                    status=0,
                    input_url=url,
                    family="link.adlink.click",
                    message="LIVE_BROWSER_INTERMEDIATE_ONLY",
                    bypass_url=None,
                    stage=live.get("stage") or "live-browser",
                    facts=facts,
                    blockers=[
                        "browser live sudah keluar dari host adlink.click, tapi target akhir belum berhasil diekstrak",
                    ],
                    notes=[
                        "hasil live browser ini masih intermediate, jadi belum dinaikkan sebagai bypass final",
                    ],
                )

            blockers = [
                "origin shortlink flow masih ketutup Cloudflare managed challenge atau chain live belum selesai",
                "butuh browser session yang bisa dapet cf_clearance lalu menyelesaikan rantai maqal360 sampai target akhir",
            ]
            if live.get("message"):
                blockers.append(f"live browser lane gagal: {live['message']}")
            return BypassResult(
                status=0,
                input_url=url,
                family="link.adlink.click",
                message="CLOUDFLARE_CHALLENGE",
                stage="cf-gate",
                facts=facts,
                blockers=blockers,
                notes=["belum ada redirect site-specific yang terverifikasi sebelum Cloudflare clear"],
            )

        if preferred:
            return BypassResult(
                status=1,
                input_url=url,
                family="link.adlink.click",
                message="EMBEDDED_TARGET_EXTRACTED",
                bypass_url=preferred,
                stage="embedded-target",
                facts=facts,
                notes=["hasil ini masih perlu dicross-check dengan flow timer/captcha live"],
            )

        return BypassResult(
            status=0,
            input_url=url,
            family="link.adlink.click",
            message="MAPPING_PENDING",
            stage="entry-mapped",
            facts=facts,
            blockers=[
                "family ini masih butuh pemetaan live yang lebih dalam",
                "belum ada verify/back URL yang bisa diangkat dengan yakin dari entry HTML saja",
            ],
        )

    def _resolve_adlink_live(self, url: str) -> dict[str, Any]:
        if not (os.path.exists(ADLINK_LIVE_HELPER) and os.path.exists(HELPER_PYTHON)):
            return {"status": 0, "message": "helper live browser tidak tersedia"}

        env = os.environ.copy()
        if HELPER_PYTHONPATH:
            existing = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = f"{HELPER_PYTHONPATH}:{existing}" if existing else HELPER_PYTHONPATH
        try:
            proc = subprocess.run(
                [
                    "xvfb-run",
                    "-a",
                    HELPER_PYTHON,
                    ADLINK_LIVE_HELPER,
                    url,
                    "--timeout",
                    str(ADLINK_BROWSER_TIMEOUT),
                ],
                capture_output=True,
                text=True,
                timeout=ADLINK_BROWSER_TIMEOUT + 30,
                env=env,
            )
        except subprocess.TimeoutExpired:
            return {"status": 0, "message": "live browser timeout"}
        except Exception as exc:
            return {"status": 0, "message": str(exc)}

        stdout = (proc.stdout or "").strip()
        if not stdout:
            stderr = (proc.stderr or "").strip()
            return {"status": 0, "message": stderr or f"helper exit {proc.returncode}"}

        last_line = stdout.splitlines()[-1]
        try:
            payload = json.loads(last_line)
        except Exception:
            stderr = (proc.stderr or "").strip()
            return {
                "status": 0,
                "message": stderr or f"helper output tidak valid: {last_line[:240]}",
            }

        if proc.returncode != 0 and not payload.get("message"):
            payload["message"] = f"helper exit {proc.returncode}"
        return payload

    def _resolve_adlink_http(self, url: str) -> dict[str, Any]:
        alias = urlparse(url).path.strip("/")
        if not alias:
            return {"status": 0, "message": "alias adlink kosong"}
        if curl_requests is None:
            return {"status": 0, "message": "curl_cffi tidak tersedia"}

        blog_url = f"https://blog.adlink.click/{alias}"
        result: dict[str, Any] = {
            "status": 0,
            "alias": alias,
            "blog_url": blog_url,
            "session_type": "curl_cffi",
            "impersonate": ADLINK_HTTP_IMPERSONATE,
        }
        session = curl_requests.Session(impersonate=ADLINK_HTTP_IMPERSONATE)
        session.headers.update(DEFAULT_HEADERS)

        def fetch_blog() -> requests.Response:
            return session.get(
                blog_url,
                headers={"Referer": "https://www.maqal360.com/"},
                timeout=self.timeout,
                allow_redirects=True,
            )

        try:
            response = fetch_blog()
        except Exception as exc:
            result["message"] = f"direct blog fetch gagal: {exc}"
            return result

        result["blog_status"] = response.status_code
        result["blog_final_url"] = response.url
        result["cookie_names"] = sorted(session.cookies.keys())

        if response.status_code >= 400 and "just a moment" in response.text.lower():
            try:
                entry = session.get(url, timeout=self.timeout, allow_redirects=True)
                result["entry_status"] = entry.status_code
                result["entry_final_url"] = entry.url
            except Exception as exc:
                result["entry_message"] = str(exc)
            try:
                response = fetch_blog()
                result["blog_retry_status"] = response.status_code
                result["blog_retry_final_url"] = response.url
                result["cookie_names"] = sorted(session.cookies.keys())
            except Exception as exc:
                result["message"] = f"blog retry gagal: {exc}"
                return result

        soup = BeautifulSoup(response.text, "html.parser")
        runtime = self._extract_runtime_config(response.text)
        result["runtime"] = runtime
        result["title"] = soup.title.get_text(strip=True) if soup.title else ""
        form = soup.select_one("form#go-link")
        target = soup.select_one("a.get-link")
        result["target_text"] = target.get_text(" ", strip=True) if target else None
        if not form:
            result["message"] = "form blog adlink tidak ditemukan"
            return result

        hidden = self._extract_hidden_inputs(form)
        action = urljoin(response.url, form.get("action") or "/links/go")
        result["form_action"] = action
        result["hidden_names"] = sorted(hidden)
        result["ad_form_data_present"] = bool(hidden.get("ad_form_data"))

        try:
            counter_value = float(runtime.get("counter_value") or 5)
        except Exception:
            counter_value = 5.0

        first_wait_seconds = max(1.0, counter_value - 1.0)
        retry_interval_seconds = 0.5
        retry_deadline = time.time() + first_wait_seconds + 2.0
        result["submit_attempts"] = []
        time.sleep(first_wait_seconds)

        submit = None
        payload: dict[str, Any] | None = None
        while time.time() <= retry_deadline:
            waited_seconds = round(first_wait_seconds + max(0.0, time.time() - (retry_deadline - 2.0)), 2)
            try:
                submit = session.post(
                    action,
                    data=hidden,
                    headers={
                        "Referer": blog_url,
                        "Origin": "https://blog.adlink.click",
                        "X-Requested-With": "XMLHttpRequest",
                        "Accept": "application/json, text/javascript, */*; q=0.01",
                    },
                    timeout=self.timeout,
                    allow_redirects=True,
                )
            except Exception as exc:
                result["message"] = f"submit blog adlink gagal: {exc}"
                return result

            try:
                payload = submit.json()
            except Exception:
                payload = {"raw": submit.text[:400]}

            final_url = self._clean_url(str(payload.get("url") or "")) if isinstance(payload, dict) else None
            attempt_row = {
                "waited_seconds": waited_seconds,
                "status_code": submit.status_code,
                "payload_status": payload.get("status") if isinstance(payload, dict) else None,
                "payload_message": payload.get("message") if isinstance(payload, dict) else None,
                "payload_url": final_url,
            }
            result["submit_attempts"].append(attempt_row)
            if final_url:
                result["status"] = 1
                result["stage"] = "blog-http-fast"
                result["waited_seconds"] = waited_seconds
                result["submit_status"] = submit.status_code
                result["submit_payload"] = payload
                result["bypass_url"] = final_url
                result["message"] = str(payload.get("message") or "OK")
                return result
            if time.time() + retry_interval_seconds > retry_deadline:
                break
            time.sleep(retry_interval_seconds)

        result["waited_seconds"] = result["submit_attempts"][-1]["waited_seconds"] if result["submit_attempts"] else first_wait_seconds
        result["submit_status"] = submit.status_code if submit is not None else None
        result["submit_payload"] = payload or {}
        result["message"] = str(payload.get("message") or "blog adlink submit tidak mengembalikan url final") if isinstance(payload, dict) else "blog adlink submit tidak valid"
        return result

    def _extract_runtime_config(self, html: str) -> dict[str, Any]:
        facts: dict[str, Any] = {}
        patterns = {
            "captcha_type": r"[\"']?captcha_type[\"']?\s*[:=]\s*[\"']([^\"']+)",
            "counter_value": r"[\"']?counter_value[\"']?\s*[:=]\s*[\"']?(\d+)",
            "counter_start": r"[\"']?counter_start[\"']?\s*[:=]\s*[\"']([^\"']+)",
            "step": r"[\"']?step[\"']?\s*[:=]\s*[\"']?(\d+)",
            "countdown": r"[\"']?countdown[\"']?\s*[:=]\s*[\"']?(\d+)",
            "captchaProvider": r"[\"']?captchaProvider[\"']?\s*[:=]\s*[\"']([^\"']+)",
            "iconcaptchaEndpoint": r"[\"']?iconcaptchaEndpoint[\"']?\s*[:=]\s*[\"']([^\"']+)",
            "verifyUrl": r"[\"']?verifyUrl[\"']?\s*[:=]\s*[\"']([^\"']+)",
            "captcha_shortlink": r"[\"']?captcha_shortlink[\"']?\s*[:=]\s*[\"']([^\"']+)",
            "targetClickCount": r"[\"']?targetClickCount[\"']?\s*[:=]\s*(\d+)",
            "turnstile_site_key": r"[\"']?turnstile_site_key[\"']?\s*[:=]\s*[\"']([^\"']+)",
            "reCAPTCHA_site_key": r"[\"']?reCAPTCHA_site_key[\"']?\s*[:=]\s*[\"']([^\"']+)",
            "hcaptcha_checkbox_site_key": r"[\"']?hcaptcha_checkbox_site_key[\"']?\s*[:=]\s*[\"']([^\"']+)",
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                facts[key] = match.group(1)

        dom_sitekeys = re.findall(r"data-sitekey=[\"']([^\"']+)", html, re.IGNORECASE)
        sitekeys = []
        sitekeys.extend(dom_sitekeys)
        sitekeys.extend(re.findall(r"sitekey[\"']?\s*[:=]\s*[\"']([^\"']+)", html, re.IGNORECASE))
        for key in ("turnstile_site_key", "reCAPTCHA_site_key", "hcaptcha_checkbox_site_key"):
            value = facts.get(key)
            if value:
                sitekeys.append(str(value))
        sitekeys = [
            value
            for value in dict.fromkeys(sitekeys)
            if value and not str(value).startswith("YOUR_")
        ]
        if sitekeys:
            facts["sitekeys"] = sitekeys
            if facts.get("captcha_type") == "turnstile" and facts.get("turnstile_site_key"):
                facts["sitekey"] = facts["turnstile_site_key"]
            elif facts.get("captcha_type") == "recaptcha" and dom_sitekeys:
                facts["sitekey"] = dom_sitekeys[0]
            elif facts.get("captcha_type") == "recaptcha" and facts.get("reCAPTCHA_site_key"):
                facts["sitekey"] = facts["reCAPTCHA_site_key"]
            else:
                facts["sitekey"] = sitekeys[0]
        if dom_sitekeys:
            facts["dom_sitekeys"] = list(dict.fromkeys(dom_sitekeys))
        return facts

    def _extract_hidden_inputs(self, root: Any) -> dict[str, str]:
        data: dict[str, str] = {}
        try:
            inputs = root.find_all("input")
        except Exception:
            inputs = []
        for element in inputs:
            name = (element.get("name") or "").strip()
            if not name:
                continue
            value = element.get("value") or ""
            data[name] = value
        return data

    def _collect_embedded_urls(self, html: str, hidden: dict[str, str]) -> list[str]:
        found: list[str] = []
        for candidate in URL_RE.findall(html):
            found.append(self._clean_url(candidate))
        for value in hidden.values():
            found.extend(self._decode_urls_from_blob(value))
        deduped = []
        seen = set()
        for item in found:
            cleaned = self._clean_url(item)
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            deduped.append(cleaned)
        return deduped

    def _decode_urls_from_blob(self, raw: str) -> list[str]:
        values = [raw, unquote(raw), unescape(raw)]
        found: list[str] = []
        for value in list(values):
            found.extend(URL_RE.findall(value))
            compact = re.sub(r"[^A-Za-z0-9_\-=/+]", "", value)
            if len(compact) >= 16:
                for candidate in {compact, compact + "=", compact + "=="}:
                    for decoder in (base64.b64decode, base64.urlsafe_b64decode):
                        try:
                            decoded = decoder(candidate)
                        except Exception:
                            continue
                        text = decoded.decode("utf-8", errors="ignore")
                        if text and text not in values:
                            values.append(text)
                            found.extend(URL_RE.findall(text))
        return [self._clean_url(item) for item in found if item]

    def _extract_oii_token_target(self, token: str) -> str | None:
        candidates = self._decode_urls_from_blob(token)
        tail_match = re.search(r"(aHR0cHM6Ly[A-Za-z0-9+/=]+)$", token)
        if tail_match:
            tail = tail_match.group(1)
            for padded in {tail, tail + "=", tail + "=="}:
                try:
                    text = base64.b64decode(padded).decode("utf-8", errors="ignore")
                except Exception:
                    continue
                candidates.extend(URL_RE.findall(text))
        for candidate in candidates:
            if any(marker in candidate for marker in ["/links/back/", "/member/shortlinks/verify/"]):
                return self._clean_url(candidate)
        return None

    def _extract_shrinkme_continue_hint(self, html: str, input_url: str) -> str | None:
        patterns = [
            r"https://themezon\.net/link\.php\?link=[A-Za-z0-9_-]+",
            r"link\.php\?link=([A-Za-z0-9_-]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if not match:
                continue
            if pattern.startswith("https://"):
                return self._clean_url(match.group(0))
            return f"https://themezon.net/link.php?link={match.group(1)}"
        if "themezon.net/link.php" in html:
            alias = urlparse(input_url).path.strip("/")
            if alias:
                return f"https://themezon.net/link.php?link={alias}"
        return None

    def _resolve_shrinkme_themezon(self, input_url: str, continue_hint: str | None) -> dict[str, Any] | None:
        if not continue_hint:
            return None
        try:
            response = self.session.get(
                continue_hint,
                headers={"Referer": input_url},
                timeout=self.timeout,
                allow_redirects=True,
            )
        except Exception as exc:
            return {"status": 0, "message": str(exc)}

        result: dict[str, Any] = {
            "status": response.status_code,
            "url": response.url,
            "cookie_names": self._cookie_names(),
        }

        if "Invalid Access" in response.text or "Direct Access not Allowed" in response.text:
            result["message"] = "referer gate rejected"
            return result

        redirect_match = re.search(r'window\.location\.href\s*=\s*"([^"]+)"', response.text, re.IGNORECASE)
        if not redirect_match:
            return result

        wrapped_url = self._clean_url(redirect_match.group(1))
        result["wrapped_url"] = wrapped_url
        parsed = urlparse(wrapped_url)
        wrapped_target = unquote(parsed.query.split("url=", 1)[1].split("&", 1)[0]) if "url=" in parsed.query else None
        if wrapped_target:
            result["article_url"] = self._clean_url(wrapped_target)
            return result

        if parsed.netloc.lower().endswith("themezon.net") and parsed.path == "/":
            try:
                follow = self.session.get(
                    wrapped_url,
                    headers={"Referer": continue_hint},
                    timeout=self.timeout,
                    allow_redirects=False,
                )
                result["follow_status"] = follow.status_code
                result["follow_location"] = follow.headers.get("location")
                if follow.headers.get("location"):
                    result["article_url"] = self._clean_url(follow.headers["location"])
            except Exception as exc:
                result["follow_message"] = str(exc)
        return result

    def _resolve_shrinkme_direct_mrproblogger(self, input_url: str) -> dict[str, Any] | None:
        alias = urlparse(input_url).path.strip("/")
        if not alias:
            return None

        result: dict[str, Any] = {
            "alias": alias,
            "mode": "direct-mrproblogger",
        }
        mrproblogger_url = f"https://en.mrproblogger.com/{alias}"
        result["mrproblogger_url"] = mrproblogger_url

        try:
            response = self.session.get(
                mrproblogger_url,
                headers={"Referer": "https://themezon.net/"},
                timeout=self.timeout,
                allow_redirects=True,
            )
        except Exception as exc:
            result["message"] = f"mrproblogger direct page gagal: {exc}"
            return result

        soup = BeautifulSoup(response.text, "html.parser")
        runtime = self._extract_runtime_config(response.text)
        result["mrproblogger_status"] = response.status_code
        result["mrproblogger_final_url"] = response.url
        result["cookie_names_after_mrproblogger"] = self._cookie_names()
        result["mrproblogger_runtime"] = runtime

        form = soup.select_one("form#go-link")
        if not form:
            result["message"] = "mrproblogger direct form tidak ditemukan"
            return result

        hidden = self._extract_hidden_inputs(form)
        action = urljoin(response.url, form.get("action") or "/links/go")
        result["form_action"] = action
        result["hidden_names"] = sorted(hidden)

        try:
            counter_value = float(runtime.get("counter_value") or 12)
        except Exception:
            counter_value = 12.0

        first_wait_seconds = max(1.0, counter_value - 0.8)
        retry_interval_seconds = 0.5
        retry_deadline = time.time() + first_wait_seconds + 2.0
        result["submit_attempts"] = []
        time.sleep(first_wait_seconds)

        submit = None
        payload: dict[str, Any] | None = None
        while time.time() <= retry_deadline:
            waited_seconds = round(first_wait_seconds + max(0.0, time.time() - (retry_deadline - 2.0)), 2)
            try:
                submit = self.session.post(
                    action,
                    data=hidden,
                    headers={
                        "Referer": response.url,
                        "Origin": f"{urlparse(response.url).scheme}://{urlparse(response.url).netloc}",
                        "X-Requested-With": "XMLHttpRequest",
                        "Accept": "application/json, text/javascript, */*; q=0.01",
                    },
                    timeout=self.timeout,
                    allow_redirects=True,
                )
            except Exception as exc:
                result["message"] = f"mrproblogger direct submit gagal: {exc}"
                return result

            try:
                payload = submit.json()
            except Exception:
                payload = {"raw": submit.text[:400]}

            final_url = self._clean_url(str(payload.get("url") or "")) if isinstance(payload, dict) else None
            attempt_row = {
                "waited_seconds": waited_seconds,
                "status_code": submit.status_code,
                "payload_status": payload.get("status") if isinstance(payload, dict) else None,
                "payload_message": payload.get("message") if isinstance(payload, dict) else None,
                "payload_url": final_url,
            }
            result["submit_attempts"].append(attempt_row)
            if final_url:
                result["status"] = 1
                result["waited_seconds"] = waited_seconds
                result["submit_status"] = submit.status_code
                result["submit_payload"] = payload
                result["bypass_url"] = final_url
                result["message"] = str(payload.get("message") or "OK")
                return result
            if time.time() + retry_interval_seconds > retry_deadline:
                break
            time.sleep(retry_interval_seconds)

        result["waited_seconds"] = result["submit_attempts"][-1]["waited_seconds"] if result["submit_attempts"] else first_wait_seconds
        result["submit_status"] = submit.status_code if submit is not None else None
        result["submit_payload"] = payload or {}
        result["message"] = str(payload.get("message") or "mrproblogger direct submit tidak mengembalikan url final") if isinstance(payload, dict) else "mrproblogger direct submit tidak valid"
        return result

    def _resolve_shrinkme_mrproblogger(
        self,
        input_url: str,
        continue_hint: str | None,
        article_url: str | None,
    ) -> dict[str, Any] | None:
        alias = urlparse(input_url).path.strip("/")
        if not alias or not article_url:
            return None

        result: dict[str, Any] = {
            "alias": alias,
            "article_url": article_url,
        }

        result["article_status"] = "skipped"
        result["article_final_url"] = article_url
        result["cookie_names_after_article"] = self._cookie_names()
        themezon_referer = continue_hint or article_url or input_url

        try:
            themezon_next = self.session.post(
                "https://themezon.net/?redirect_to=random",
                data={"newwpsafelink": alias},
                headers={
                    "Referer": themezon_referer,
                    "Origin": "https://themezon.net",
                },
                timeout=self.timeout,
                allow_redirects=False,
            )
            result["themezon_next_status"] = themezon_next.status_code
            next_location = self._clean_url(themezon_next.headers.get("Location", "")) or None
            result["themezon_next_url"] = next_location
        except Exception as exc:
            result["message"] = f"themezon next hop gagal: {exc}"
            return result

        mrproblogger_url = f"https://en.mrproblogger.com/{alias}"
        mrproblogger_referer = result.get("themezon_next_url") or themezon_referer
        result["mrproblogger_url"] = mrproblogger_url
        result["mrproblogger_referer"] = mrproblogger_referer

        try:
            mrproblogger_response = self.session.get(
                mrproblogger_url,
                headers={"Referer": mrproblogger_referer},
                timeout=self.timeout,
                allow_redirects=True,
            )
        except Exception as exc:
            result["message"] = f"mrproblogger page gagal: {exc}"
            return result

        mrproblogger_soup = BeautifulSoup(mrproblogger_response.text, "html.parser")
        result["mrproblogger_status"] = mrproblogger_response.status_code
        result["mrproblogger_final_url"] = mrproblogger_response.url
        result["cookie_names_after_mrproblogger"] = self._cookie_names()
        runtime = self._extract_runtime_config(mrproblogger_response.text)
        result["mrproblogger_runtime"] = runtime

        form = mrproblogger_soup.select_one("form#go-link")
        if not form:
            result["message"] = "mrproblogger go-link form tidak ditemukan"
            return result

        hidden = self._extract_hidden_inputs(form)
        action = urljoin(mrproblogger_response.url, form.get("action") or "/links/go")
        result["form_action"] = action
        result["hidden_names"] = sorted(hidden)

        try:
            counter_value = int(runtime.get("counter_value") or 12)
        except Exception:
            counter_value = 12

        first_wait_seconds = max(1.0, float(counter_value) - 1.0)
        retry_interval_seconds = 0.5
        retry_deadline = time.time() + first_wait_seconds + 4.0
        result["submit_attempts"] = []
        time.sleep(first_wait_seconds)

        submit = None
        payload: dict[str, Any] | None = None
        while time.time() <= retry_deadline:
            waited_seconds = round(first_wait_seconds + max(0.0, time.time() - (retry_deadline - 4.0)), 2)
            try:
                submit = self.session.post(
                    action,
                    data=hidden,
                    headers={
                        "Referer": mrproblogger_response.url,
                        "Origin": f"{urlparse(mrproblogger_response.url).scheme}://{urlparse(mrproblogger_response.url).netloc}",
                        "X-Requested-With": "XMLHttpRequest",
                        "Accept": "application/json, text/javascript, */*; q=0.01",
                    },
                    timeout=self.timeout,
                    allow_redirects=True,
                )
            except Exception as exc:
                result["message"] = f"mrproblogger submit gagal: {exc}"
                return result

            try:
                payload = submit.json()
            except Exception:
                payload = {"raw": submit.text[:400]}

            final_url = self._clean_url(str(payload.get("url") or "")) if isinstance(payload, dict) else None
            attempt_row = {
                "waited_seconds": waited_seconds,
                "status_code": submit.status_code,
                "payload_status": payload.get("status") if isinstance(payload, dict) else None,
                "payload_message": payload.get("message") if isinstance(payload, dict) else None,
                "payload_url": final_url,
            }
            result["submit_attempts"].append(attempt_row)
            if final_url:
                result["waited_seconds"] = waited_seconds
                result["submit_status"] = submit.status_code
                result["submit_payload"] = payload
                result["status"] = 1
                result["bypass_url"] = final_url
                result["message"] = str(payload.get("message") or "OK")
                return result
            if time.time() + retry_interval_seconds > retry_deadline:
                break
            time.sleep(retry_interval_seconds)

        result["waited_seconds"] = result["submit_attempts"][-1]["waited_seconds"] if result.get("submit_attempts") else first_wait_seconds
        result["submit_status"] = submit.status_code if submit is not None else None
        result["submit_payload"] = payload or {}
        result["message"] = str(payload.get("message") or "mrproblogger submit tidak mengembalikan url final") if isinstance(payload, dict) else "mrproblogger submit tidak valid"
        return result

    def _is_cloudflare_challenge(self, response: requests.Response) -> bool:
        text = response.text.lower()
        return (
            response.status_code == 403
            and "cloudflare" in (response.headers.get("server", "").lower() + text)
            and "just a moment" in text
        )

    def _decode_google_wrapper(self, value: str) -> str | None:
        if not value:
            return None
        parsed = urlparse(value)
        if parsed.netloc.lower() not in {"google.com", "www.google.com"} or parsed.path != "/url":
            return self._clean_url(value)
        return self._clean_url(parse_qs(parsed.query).get("url", [""])[0]) or None

    def _decode_signed_json_cookie(self, value: str) -> dict[str, Any] | None:
        if not value or "." not in value:
            return None
        head = value.split(".", 1)[0]
        for candidate in (head, head + "=", head + "=="):
            try:
                text = base64.urlsafe_b64decode(candidate).decode("utf-8", errors="ignore")
                data = json.loads(text)
            except Exception:
                continue
            if isinstance(data, dict):
                return data
        return None

    def _pick_preferred_bypass_url(self, urls: list[str], input_url: str) -> str | None:
        source_host = urlparse(input_url).netloc.lower()
        ranked: list[str] = []
        for candidate in urls:
            parsed = urlparse(candidate)
            host = parsed.netloc.lower()
            if not host:
                continue
            if host == source_host:
                continue
            if any(host.endswith(blocked) for blocked in [
                "taboola.com",
                "advertisingcamps.com",
                "googlesyndication.com",
                "g.doubleclick.net",
                "dd133.com",
                "crn77.com",
                "googletagmanager.com",
                "themezon.net",
            ]):
                continue
            if re.search(r"\.(?:js|css|png|jpg|jpeg|webp|svg|gif)(?:$|[?#])", parsed.path, re.IGNORECASE):
                continue
            ranked.append(candidate)
        if not ranked:
            return None
        strong = [item for item in ranked if any(marker in item for marker in ["/links/back/", "/member/shortlinks/verify/"])]
        return strong[0] if strong else ranked[0]

    def _clean_url(self, value: str) -> str:
        return value.strip().strip('"\'').rstrip('.,);]')


def cli() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Shortlink bypass engine")
    parser.add_argument("url", help="shortlink URL")
    parser.add_argument("--pretty", action="store_true", help="pretty JSON")
    args = parser.parse_args()

    engine = ShortlinkBypassEngine()
    result = engine.analyze(args.url)
    if args.pretty:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(json.dumps(result.to_dict(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
