from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

try:
    from curl_cffi import requests as curl_requests
except Exception:
    curl_requests = None

PROJECT_ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = PROJECT_ROOT.parent.parent
DEFAULT_TIMEOUT = 30
ADLINK_BROWSER_TIMEOUT = int(os.getenv("SHORTLINK_BYPASS_ADLINK_BROWSER_TIMEOUT", "240"))
ADLINK_HTTP_IMPERSONATE = os.getenv("SHORTLINK_BYPASS_ADLINK_IMPERSONATE", "chrome136")
ADLINK_LIVE_HELPER = os.getenv("SHORTLINK_BYPASS_ADLINK_HELPER", str(PROJECT_ROOT / "adlink_live_browser.py"))
HELPER_PYTHON = os.getenv("SHORTLINK_BYPASS_HELPER_PYTHON", sys.executable)
HELPER_PYTHONPATH = os.getenv("SHORTLINK_BYPASS_HELPER_PYTHONPATH", "")
XUT_BROWSER_TIMEOUT = int(os.getenv("SHORTLINK_BYPASS_XUT_BROWSER_TIMEOUT", "300"))
XUT_LIVE_ATTEMPTS = int(os.getenv("SHORTLINK_BYPASS_XUT_ATTEMPTS", "3"))
XUT_LIVE_HELPER = os.getenv("SHORTLINK_BYPASS_XUT_HELPER", str(PROJECT_ROOT / "xut_live_browser.py"))
XUT_HELPER_PYTHON = os.getenv("SHORTLINK_BYPASS_XUT_HELPER_PYTHON", HELPER_PYTHON)
XUT_HELPER_PYTHONPATH = os.getenv("SHORTLINK_BYPASS_XUT_HELPER_PYTHONPATH", "")
CUTY_BROWSER_TIMEOUT = int(os.getenv("SHORTLINK_BYPASS_CUTY_BROWSER_TIMEOUT", "240"))
CUTY_LIVE_HELPER = os.getenv("SHORTLINK_BYPASS_CUTY_HELPER", str(PROJECT_ROOT / "cuty_live_browser.py"))
CUTY_HELPER_PYTHON = os.getenv("SHORTLINK_BYPASS_CUTY_HELPER_PYTHON", HELPER_PYTHON)
CUTY_HELPER_PYTHONPATH = os.getenv("SHORTLINK_BYPASS_CUTY_HELPER_PYTHONPATH", "")
CUTY_TURNSTILE_SOLVER_URL = os.getenv("SHORTLINK_BYPASS_CUTY_TURNSTILE_SOLVER_URL", "http://127.0.0.1:5000")
EXE_BROWSER_TIMEOUT = int(os.getenv("SHORTLINK_BYPASS_EXE_BROWSER_TIMEOUT", "240"))
EXE_LIVE_HELPER = os.getenv("SHORTLINK_BYPASS_EXE_HELPER", str(PROJECT_ROOT / "exe_live_browser.py"))
EXE_HELPER_PYTHON = os.getenv("SHORTLINK_BYPASS_EXE_HELPER_PYTHON", HELPER_PYTHON)
EXE_HELPER_PYTHONPATH = os.getenv("SHORTLINK_BYPASS_EXE_HELPER_PYTHONPATH", "")
EXE_TURNSTILE_SOLVER_URL = os.getenv("SHORTLINK_BYPASS_EXE_TURNSTILE_SOLVER_URL", CUTY_TURNSTILE_SOLVER_URL)
GPLINKS_BROWSER_TIMEOUT = int(os.getenv("SHORTLINK_BYPASS_GPLINKS_BROWSER_TIMEOUT", "340"))
GPLINKS_LIVE_HELPER = os.getenv("SHORTLINK_BYPASS_GPLINKS_HELPER", str(PROJECT_ROOT / "gplinks_live_browser.py"))
GPLINKS_HELPER_PYTHON = os.getenv("SHORTLINK_BYPASS_GPLINKS_HELPER_PYTHON", HELPER_PYTHON)
GPLINKS_HELPER_PYTHONPATH = os.getenv("SHORTLINK_BYPASS_GPLINKS_HELPER_PYTHONPATH", "")
GPLINKS_TURNSTILE_SOLVER_URL = os.getenv("SHORTLINK_BYPASS_GPLINKS_TURNSTILE_SOLVER_URL", CUTY_TURNSTILE_SOLVER_URL)
GPLINKS_HTTP_FAST_TIMEOUT = int(os.getenv("SHORTLINK_BYPASS_GPLINKS_HTTP_FAST_TIMEOUT", "90"))
GPLINKS_HTTP_FAST_HELPER = os.getenv("SHORTLINK_BYPASS_GPLINKS_HTTP_FAST_HELPER", str(PROJECT_ROOT / "gplinks_http_fast.py"))
GPLINKS_HTTP_FAST_PYTHON = os.getenv("SHORTLINK_BYPASS_GPLINKS_HTTP_FAST_PYTHON", HELPER_PYTHON)
GPLINKS_HTTP_FAST_PYTHONPATH = os.getenv("SHORTLINK_BYPASS_GPLINKS_HTTP_FAST_PYTHONPATH", "")
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
        token_landing_hosts = {"oii.la", "tpi.li", "aii.sh"}
        if host in token_landing_hosts or any(host.endswith(f".{item}") for item in token_landing_hosts):
            family = next(item for item in token_landing_hosts if host == item or host.endswith(f".{item}"))
            return self._handle_token_landing(url, family)
        if host == "shrinkme.click" or host.endswith(".shrinkme.click"):
            return self._handle_shrinkme(url)
        if host == "link.adlink.click" or host.endswith(".adlink.click"):
            return self._handle_adlink_click(url)
        if host == "sfl.gl" or host.endswith(".sfl.gl"):
            return self._handle_sfl(url)
        if host == "gplinks.co" or host.endswith(".gplinks.co"):
            return self._handle_gplinks(url)
        if host == "ez4short.com" or host.endswith(".ez4short.com"):
            return self._handle_ez4short(url)
        if host == "cuty.io" or host.endswith(".cuty.io") or host == "cuttlinks.com" or host.endswith(".cuttlinks.com"):
            return self._handle_cuty(url)
        if host == "lnbz.la" or host.endswith(".lnbz.la"):
            return self._handle_lnbz(url)
        if host == "exe.io" or host.endswith(".exe.io") or host == "exeygo.com" or host.endswith(".exeygo.com"):
            return self._handle_exe(url)
        return BypassResult(
            status=0,
            input_url=url,
            family="unknown",
            message="UNSUPPORTED_FAMILY",
            blockers=[f"host {host} belum ada handler khusus"],
        )

    def _get(self, url: str) -> requests.Response:
        return self.session.get(url, timeout=self.timeout, allow_redirects=True)

    def _new_impersonated_session(self):
        if curl_requests is None:
            raise RuntimeError("curl_cffi is not installed")
        session = curl_requests.Session(impersonate=ADLINK_HTTP_IMPERSONATE)
        session.headers.update(DEFAULT_HEADERS)
        return session

    def _cookie_names(self) -> list[str]:
        return sorted({cookie.name for cookie in self.session.cookies})

    def _common_facts(self, response: requests.Response, soup: BeautifulSoup) -> dict[str, Any]:
        return {
            "final_url": response.url,
            "status_code": response.status_code,
            "title": (soup.title.string.strip() if soup.title and soup.title.string else None),
            "cookie_names": self._cookie_names(),
        }

    def _common_facts_for_session(self, response: Any, soup: BeautifulSoup, session: Any) -> dict[str, Any]:
        cookie_names: list[str] = []
        jar = getattr(getattr(session, "cookies", None), "jar", [])
        try:
            cookie_names = sorted({cookie.name for cookie in jar})
        except Exception:
            cookie_names = []
        return {
            "final_url": response.url,
            "status_code": response.status_code,
            "title": (soup.title.string.strip() if soup.title and soup.title.string else None),
            "cookie_names": cookie_names,
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

        live = self._resolve_xut_live(url)
        if live:
            facts["live_helper"] = {k: v for k, v in live.items() if k not in {"facts", "notes", "blockers", "bypass_url"}}
            if isinstance(live.get("facts"), dict):
                facts["live_helper_facts"] = live["facts"]
            if live.get("notes"):
                notes.extend(str(item) for item in live.get("notes", []) if str(item).strip())

            if live.get("status") == 1 and live.get("bypass_url"):
                return BypassResult(
                    status=1,
                    input_url=url,
                    family=family,
                    message=str(live.get("message") or "LIVE_BROWSER_FINAL_OK"),
                    bypass_url=str(live.get("bypass_url")),
                    stage=str(live.get("stage") or "final-bypass"),
                    facts=facts,
                    blockers=list(live.get("blockers") or []),
                    notes=notes,
                )

            live_stage = str(live.get("stage") or "")
            live_message = str(live.get("message") or "")
            if live_stage or live_message:
                merged_blockers = blockers + [str(item) for item in live.get("blockers", []) if str(item).strip()]
                deduped_blockers = list(dict.fromkeys(merged_blockers))
                return BypassResult(
                    status=0,
                    input_url=url,
                    family=family,
                    message=live_message or "LIVE_BROWSER_PROGRESS_ONLY",
                    stage=live_stage or "live-browser-partial",
                    facts=facts,
                    blockers=deduped_blockers,
                    notes=notes,
                )

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
        return self._handle_token_landing(url, "oii.la")


    def _handle_exe(self, url: str) -> BypassResult:
        family = "exe.io"
        facts: dict[str, Any] = {}
        try:
            session = self._new_impersonated_session()
            parsed = urlparse(url)
            if parsed.netloc.lower() == "exe.io" or parsed.netloc.lower().endswith(".exe.io"):
                entry = session.get(url, timeout=self.timeout, allow_redirects=False)
                facts["entry_status"] = entry.status_code
                facts["entry_redirect"] = self._clean_url(entry.headers.get("location", "")) or None
                gate_url = facts["entry_redirect"] or url
            else:
                gate_url = url
                facts["entry_status"] = None
                facts["entry_redirect"] = gate_url

            first = session.get(gate_url, timeout=self.timeout, allow_redirects=True, headers={"Referer": url})
            first_soup = BeautifulSoup(first.text, "html.parser")
            facts.update(self._common_facts_for_session(first, first_soup, session))
            facts.update(self._extract_runtime_config(first.text))

            before_form = first_soup.select_one("form#before-captcha") or first_soup.find("form")
            if not before_form:
                return BypassResult(
                    status=0,
                    input_url=url,
                    family=family,
                    message="EXE_BEFORE_FORM_NOT_FOUND",
                    stage="entry",
                    facts=facts,
                    blockers=["form before-captcha tidak ditemukan di gate exe/exeygo"],
                )

            before_action = urljoin(first.url, before_form.get("action") or "")
            before_hidden = self._extract_hidden_inputs(before_form)
            facts["before_form_action"] = before_action
            facts["before_hidden_names"] = sorted(before_hidden)

            second = session.post(
                before_action,
                data=before_hidden,
                timeout=self.timeout,
                allow_redirects=True,
                headers={
                    "Origin": f"{urlparse(first.url).scheme}://{urlparse(first.url).netloc}",
                    "Referer": first.url,
                },
            )
            second_soup = BeautifulSoup(second.text, "html.parser")
            facts["second_status"] = second.status_code
            facts["second_url"] = second.url
            facts.update({k: v for k, v in self._extract_runtime_config(second.text).items() if k not in facts or not facts.get(k)})

            link_form = second_soup.select_one("form#link-view")
            if not link_form:
                return BypassResult(
                    status=0,
                    input_url=url,
                    family=family,
                    message="EXE_LINK_FORM_NOT_FOUND",
                    stage="second-gate",
                    facts=facts,
                    blockers=["form link-view tidak ditemukan setelah submit before-captcha"],
                )

            link_hidden = self._extract_hidden_inputs(link_form)
            facts["link_form_action"] = urljoin(second.url, link_form.get("action") or "")
            facts["link_hidden_names"] = sorted(link_hidden)

            live = self._resolve_exe_live(url)
            if live:
                facts["live_helper"] = {k: v for k, v in live.items() if k not in {"timeline", "bypass_url", "blockers", "notes"}}
                if live.get("status") == 1 and live.get("bypass_url"):
                    return BypassResult(
                        status=1,
                        input_url=url,
                        family=family,
                        message=str(live.get("message") or "EXE_LIVE_TURNSTILE_CHAIN_OK"),
                        bypass_url=str(live.get("bypass_url")),
                        stage=str(live.get("stage") or "live-browser-turnstile-go"),
                        facts=facts,
                        notes=["dua tahap CakePHP form + Turnstile + go-link submit live-proven"],
                    )

            return BypassResult(
                status=0,
                input_url=url,
                family=family,
                message="EXE_GATE_MAPPED",
                stage="captcha-gate",
                facts=facts,
                blockers=[
                    "valid Turnstile/reCAPTCHA token diperlukan sebelum final target bisa dibuktikan",
                    "jangan klaim google.com dari snippet referrer randomizer; final harus datang dari post-captcha redirect/body",
                ],
                notes=["dua tahap CakePHP form sudah termap sampai form#link-view"],
            )
        except Exception as exc:
            return BypassResult(
                status=0,
                input_url=url,
                family=family,
                message="REQUEST_FAILED",
                facts=facts,
                blockers=[str(exc)],
            )

    def _handle_token_landing(self, url: str, family: str) -> BypassResult:
        try:
            response = self._get(url)
        except Exception as exc:
            return BypassResult(
                status=0,
                input_url=url,
                family=family,
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
                family=family,
                message="TOKEN_TARGET_EXTRACTED" if token_target else "EMBEDDED_TARGET_EXTRACTED",
                bypass_url=preferred,
                stage="token-target" if token_target else "embedded-target",
                facts=facts,
                notes=[
                    "hasil ini berasal dari payload entry page, belum dari eksekusi captcha/timer live",
                    "target terkuat diambil dari hidden token yang didecode" if token_target else "target diambil dari URL embedded di entry page",
                ],
            )

        return BypassResult(
            status=0,
            input_url=url,
            family=family,
            message="CAPTCHA_OR_TOKEN_FLOW_STILL_REQUIRED",
            stage="entry-mapped",
            facts=facts,
            blockers=[
                "belum ada embedded downstream URL yang bisa diangkat dengan yakin",
                "flow live tetap butuh timer + turnstile + verify/back execution",
            ],
        )

    def _handle_sfl(self, url: str) -> BypassResult:
        family = "sfl.gl"
        facts: dict[str, Any] = {}
        try:
            session = self._new_impersonated_session()
            facts["egress_mode"] = "direct"
            entry = session.get(url, timeout=self.timeout, allow_redirects=True)
            soup = BeautifulSoup(entry.text, "html.parser")
            facts.update(self._common_facts_for_session(entry, soup, session))
            if self._is_cloudflare_block(entry, soup):
                for proxy in self._sfl_proxy_candidates():
                    proxy_session = self._new_impersonated_session()
                    try:
                        proxy_session.proxies = proxy
                    except Exception:
                        pass
                    proxy_entry = proxy_session.get(url, timeout=self.timeout, allow_redirects=True, proxies=proxy)
                    proxy_soup = BeautifulSoup(proxy_entry.text, "html.parser")
                    if not self._is_cloudflare_block(proxy_entry, proxy_soup):
                        session = proxy_session
                        entry = proxy_entry
                        soup = proxy_soup
                        facts.clear()
                        facts["egress_mode"] = "proxy-fallback"
                        facts["proxy"] = next(iter(proxy.values())) if proxy else None
                        facts.update(self._common_facts_for_session(entry, soup, session))
                        break
                else:
                    return BypassResult(
                        status=0,
                        input_url=url,
                        family=family,
                        message="CLOUDFLARE_BLOCKED",
                        stage="entry-cloudflare",
                        facts=facts,
                        blockers=["Cloudflare access denied / IP block sebelum form SafelinkU muncul"],
                    )

            form = soup.find("form")
            if not form:
                return BypassResult(
                    status=0,
                    input_url=url,
                    family=family,
                    message="ENTRY_FORM_NOT_FOUND",
                    stage="entry",
                    facts=facts,
                    blockers=["form redirect.php tidak ditemukan di entry page"],
                )

            action = urljoin(entry.url, form.get("action") or "")
            hidden = self._extract_hidden_inputs(form)
            facts["entry_form_action"] = action
            facts["entry_hidden_inputs"] = hidden
            redirect_url = f"{action}?{urlencode(hidden)}"
            redirect_response = session.get(
                redirect_url,
                timeout=self.timeout,
                allow_redirects=False,
                headers={"Referer": entry.url},
            )
            article_url = urljoin(action, redirect_response.headers.get("location", ""))
            facts["article_redirect_status"] = redirect_response.status_code
            facts["article_url"] = article_url
            if not article_url:
                return BypassResult(
                    status=0,
                    input_url=url,
                    family=family,
                    message="ARTICLE_REDIRECT_NOT_FOUND",
                    stage="redirect",
                    facts=facts,
                    blockers=["redirect article app.khaddavi.net tidak ditemukan"],
                )

            article = session.get(article_url, timeout=self.timeout, allow_redirects=True, headers={"Referer": redirect_url})
            facts["article_final_url"] = article.url
            app_base = f"{urlparse(article.url).scheme}://{urlparse(article.url).netloc}"
            api_headers = {
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json",
                "Origin": app_base,
                "Referer": article.url,
            }

            session_response = session.post(f"{app_base}/api/session", json={}, headers=api_headers, timeout=self.timeout)
            session_payload = self._safe_json(session_response)
            facts["api_session"] = session_payload
            wait_seconds = 10 if int(session_payload.get("step") or 1) == 1 else 3
            facts["wait_seconds"] = wait_seconds
            time.sleep(wait_seconds)

            captcha = session_payload.get("captcha")
            if captcha:
                return BypassResult(
                    status=0,
                    input_url=url,
                    family=family,
                    message="CAPTCHA_REQUIRED",
                    stage="api-session",
                    facts=facts,
                    blockers=[f"api/session meminta captcha: {captcha}"],
                )

            verify_response = session.post(
                f"{app_base}/api/verify",
                json={"_a": True, "captcha": None, "passcode": None},
                headers={**api_headers, "Idempotency-Key": str(uuid.uuid4())},
                timeout=self.timeout,
            )
            verify_payload = self._safe_json(verify_response)
            facts["api_verify"] = verify_payload

            go_response = session.post(
                f"{app_base}/api/go",
                json={"key": hidden.get("alias"), "size": 0, "_dvc": "desktop"},
                headers={**api_headers, "Idempotency-Key": str(uuid.uuid4())},
                timeout=self.timeout,
            )
            go_payload = self._safe_json(go_response)
            facts["api_go"] = go_payload
            ready_url = go_payload.get("url")
            if not ready_url:
                return BypassResult(
                    status=0,
                    input_url=url,
                    family=family,
                    message="READY_URL_NOT_FOUND",
                    stage="api-go",
                    facts=facts,
                    blockers=["api/go belum mengembalikan ready URL"],
                )

            ready = session.get(ready_url, timeout=self.timeout, allow_redirects=True, headers={"Referer": article.url})
            facts["ready_url"] = ready.url
            target = self._extract_sfl_ready_target(ready.text)
            facts["ready_target"] = target
            if target:
                return BypassResult(
                    status=1,
                    input_url=url,
                    family=family,
                    message="SFL_API_FLOW_OK",
                    bypass_url=target,
                    stage="ready-page",
                    facts=facts,
                    notes=["target final diekstrak dari ready page setelah API session/verify/go flow"],
                )

            return BypassResult(
                status=0,
                input_url=url,
                family=family,
                message="READY_TARGET_NOT_FOUND",
                stage="ready-page",
                facts=facts,
                blockers=["ready page tidak memuat window.location.href final"],
            )
        except Exception as exc:
            return BypassResult(
                status=0,
                input_url=url,
                family=family,
                message="REQUEST_FAILED",
                facts=facts,
                blockers=[str(exc)],
            )

    def _handle_gplinks(self, url: str) -> BypassResult:
        family = "gplinks.co"
        facts: dict[str, Any] = {}
        try:
            http_fast = self._resolve_gplinks_http_fast(url)
            if http_fast.get("status") == 1 and http_fast.get("bypass_url"):
                facts["live_stage"] = http_fast.get("stage")
                facts["decoded_query"] = http_fast.get("decoded_query")
                facts["sitekey"] = http_fast.get("sitekey")
                facts["token_used"] = http_fast.get("token_used")
                facts["waited_seconds"] = http_fast.get("waited_seconds")
                return BypassResult(
                    status=1,
                    input_url=url,
                    family=family,
                    message="GPLINKS_FINAL_OK",
                    bypass_url=self._clean_url(http_fast["bypass_url"]),
                    stage="http-fast",
                    facts=facts,
                    notes=[
                        "GPLinks returned final target through the HTTP fast helper",
                        "success is claimed only after /links/go returns a non-gplinks downstream target",
                    ],
                )
            if http_fast:
                facts["http_fast_stage"] = http_fast.get("stage")
                facts["http_fast_message"] = http_fast.get("message")
                facts["http_fast_waited_seconds"] = http_fast.get("waited_seconds")

            live = self._resolve_gplinks_live(url)
            if live.get("status") == 1 and live.get("bypass_url"):
                facts["live_stage"] = live.get("stage")
                facts["decoded_query"] = live.get("decoded_query")
                facts["sitekey"] = live.get("sitekey")
                facts["token_used"] = live.get("token_used")
                facts["waited_seconds"] = live.get("waited_seconds")
                return BypassResult(
                    status=1,
                    input_url=url,
                    family=family,
                    message="GPLINKS_FINAL_OK",
                    bypass_url=self._clean_url(live["bypass_url"]),
                    stage="live-browser",
                    facts=facts,
                    notes=[
                        "PowerGam steps completed in a browser, then the final gplinks page was unlocked via its Turnstile callback path",
                        "success is claimed only after the final page exposes a non-gplinks downstream target",
                    ],
                )
            if live:
                facts["live_stage"] = live.get("stage")
                facts["live_message"] = live.get("message")
                facts["live_final_url"] = live.get("final_url")

            session = self._new_impersonated_session()
            entry = session.get(url, timeout=self.timeout, allow_redirects=False)
            facts["entry_status"] = entry.status_code
            facts["entry_redirect"] = self._clean_url(entry.headers.get("location", "")) or None
            power_url = facts["entry_redirect"] or ""
            if not power_url:
                return BypassResult(
                    status=0,
                    input_url=url,
                    family=family,
                    message="POWERGAM_REDIRECT_NOT_FOUND",
                    stage="entry",
                    facts=facts,
                    blockers=["entry tidak memberi redirect ke powergam.online"],
                )

            decoded = self._decode_gplinks_power_query(power_url)
            facts["decoded_query"] = decoded
            lid = decoded.get("lid") or ""
            pid = decoded.get("pid") or ""
            vid = decoded.get("vid") or ""
            facts["target_final_candidate"] = f"https://gplinks.co/{lid}?pid={pid}&vid={vid}" if lid and pid and vid else None

            power = session.get(power_url, timeout=self.timeout, allow_redirects=True, headers={"Referer": url})
            soup = BeautifulSoup(power.text, "html.parser")
            facts.update(self._common_facts_for_session(power, soup, session))
            form = soup.select_one("form#adsForm") or soup.find("form")
            facts["form_action"] = urljoin(power.url, form.get("action") or "") if form else None
            facts["hidden_inputs"] = self._extract_hidden_inputs(form or soup)
            facts["has_ads_form"] = bool(form)

            return BypassResult(
                status=0,
                input_url=url,
                family=family,
                message="POWERGAM_STEPS_MAPPED",
                stage="powergam-mapped",
                facts=facts,
                blockers=[
                    "PowerGam step flow mapped, but naive 3-step replay still returns gplinks not_enough_steps",
                    "missing server-side ad impression/conversion contract before final target can be claimed",
                ],
                notes=["target_final_candidate is a JS-computed candidate, not a verified final bypass result"],
            )
        except Exception as exc:
            return BypassResult(
                status=0,
                input_url=url,
                family=family,
                message="REQUEST_FAILED",
                facts=facts,
                blockers=[str(exc)],
            )

    def _resolve_gplinks_http_fast(self, url: str) -> dict[str, Any]:
        if not (os.path.exists(GPLINKS_HTTP_FAST_HELPER) and os.path.exists(GPLINKS_HTTP_FAST_PYTHON)):
            return {}

        env = os.environ.copy()
        helper_pythonpath_parts = [part for part in [GPLINKS_HTTP_FAST_PYTHONPATH, HELPER_PYTHONPATH] if part]
        if helper_pythonpath_parts:
            existing = env.get("PYTHONPATH", "")
            helper_pythonpath = ":".join(helper_pythonpath_parts)
            env["PYTHONPATH"] = f"{helper_pythonpath}:{existing}" if existing else helper_pythonpath
        try:
            proc = subprocess.run(
                [
                    GPLINKS_HTTP_FAST_PYTHON,
                    GPLINKS_HTTP_FAST_HELPER,
                    url,
                    "--timeout",
                    str(GPLINKS_HTTP_FAST_TIMEOUT),
                    "--solver-url",
                    GPLINKS_TURNSTILE_SOLVER_URL,
                ],
                capture_output=True,
                text=True,
                timeout=GPLINKS_HTTP_FAST_TIMEOUT + 30,
                env=env,
            )
        except subprocess.TimeoutExpired:
            return {"status": 0, "message": "gplinks HTTP fast timeout", "stage": "http-fast-timeout"}
        except Exception as exc:
            return {"status": 0, "message": str(exc), "stage": "http-fast-error"}

        stdout = (proc.stdout or "").strip()
        if not stdout:
            return {"status": 0, "message": (proc.stderr or "").strip() or f"helper exit {proc.returncode}", "stage": "http-fast-no-output"}
        last_line = stdout.splitlines()[-1]
        try:
            payload = json.loads(last_line)
        except Exception:
            return {"status": 0, "message": (proc.stderr or "").strip() or f"helper output tidak valid: {last_line[:240]}", "stage": "http-fast-invalid-output"}
        if proc.returncode != 0 and not payload.get("message"):
            payload["message"] = f"helper exit {proc.returncode}"
        return payload

    def _resolve_gplinks_live(self, url: str) -> dict[str, Any]:
        if not (os.path.exists(GPLINKS_LIVE_HELPER) and os.path.exists(GPLINKS_HELPER_PYTHON)):
            return {}

        env = os.environ.copy()
        helper_pythonpath_parts = [part for part in [GPLINKS_HELPER_PYTHONPATH, HELPER_PYTHONPATH] if part]
        if helper_pythonpath_parts:
            existing = env.get("PYTHONPATH", "")
            helper_pythonpath = ":".join(helper_pythonpath_parts)
            env["PYTHONPATH"] = f"{helper_pythonpath}:{existing}" if existing else helper_pythonpath
        try:
            proc = subprocess.run(
                [
                    GPLINKS_HELPER_PYTHON,
                    GPLINKS_LIVE_HELPER,
                    url,
                    "--timeout",
                    str(GPLINKS_BROWSER_TIMEOUT),
                    "--solver-url",
                    GPLINKS_TURNSTILE_SOLVER_URL,
                ],
                capture_output=True,
                text=True,
                timeout=GPLINKS_BROWSER_TIMEOUT + 45,
                env=env,
            )
        except subprocess.TimeoutExpired:
            return {"status": 0, "message": "gplinks live browser timeout", "stage": "live-browser-timeout"}
        except Exception as exc:
            return {"status": 0, "message": str(exc), "stage": "live-browser-error"}

        stdout = (proc.stdout or "").strip()
        if not stdout:
            return {"status": 0, "message": (proc.stderr or "").strip() or f"helper exit {proc.returncode}", "stage": "live-browser-no-output"}
        last_line = stdout.splitlines()[-1]
        try:
            payload = json.loads(last_line)
        except Exception:
            return {"status": 0, "message": (proc.stderr or "").strip() or f"helper output tidak valid: {last_line[:240]}", "stage": "live-browser-invalid-output"}
        if proc.returncode != 0 and not payload.get("message"):
            payload["message"] = f"helper exit {proc.returncode}"
        return payload

    def _handle_ez4short(self, url: str) -> BypassResult:
        family = "ez4short.com"
        facts: dict[str, Any] = {"fast_referer": "https://game5s.com/"}
        try:
            session = self._new_impersonated_session()
            page = session.get(
                url,
                timeout=self.timeout,
                allow_redirects=True,
                headers={"Referer": "https://game5s.com/"},
            )
            soup = BeautifulSoup(page.text, "html.parser")
            facts.update(self._common_facts_for_session(page, soup, session))
            form = soup.select_one("form#go-link")
            if not form:
                return BypassResult(
                    status=0,
                    input_url=url,
                    family=family,
                    message="GO_LINK_FORM_NOT_FOUND",
                    stage="game5s-referer-entry",
                    facts=facts,
                    blockers=["game5s referer belum membuka form#go-link pada response ini"],
                )

            hidden = self._extract_hidden_inputs(form)
            action = urljoin(page.url, form.get("action") or "/links/go")
            timer = self._extract_numeric_timer(page.text, default=3.0)
            wait_seconds = max(timer + 0.2, 3.2)
            facts["go_link_action"] = action
            facts["hidden_inputs"] = hidden
            facts["timer_seconds"] = timer
            facts["wait_seconds"] = wait_seconds
            time.sleep(wait_seconds)

            submit = session.post(
                action,
                data=hidden,
                timeout=self.timeout,
                headers={
                    "Origin": "https://ez4short.com",
                    "Referer": page.url,
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                },
            )
            payload = self._safe_json(submit)
            facts["submit_payload"] = payload
            target = self._clean_url(str(payload.get("url") or "")) or None
            if payload.get("status") == "success" and target:
                return BypassResult(
                    status=1,
                    input_url=url,
                    family=family,
                    message="EZ4SHORT_FAST_CHAIN_OK",
                    bypass_url=target,
                    stage="game5s-referer-go-link",
                    facts=facts,
                    notes=["fast lane uses game5s referer to unlock fresh go-link form, then waits final timer before /links/go"],
                )

            return BypassResult(
                status=0,
                input_url=url,
                family=family,
                message="EZ4SHORT_SUBMIT_FAILED",
                stage="links-go",
                facts=facts,
                blockers=[str(payload.get("message") or "links/go did not return success URL")],
            )
        except Exception as exc:
            return BypassResult(
                status=0,
                input_url=url,
                family=family,
                message="REQUEST_FAILED",
                facts=facts,
                blockers=[str(exc)],
            )


    def _handle_cuty(self, url: str) -> BypassResult:
        family = "cuty.io"
        facts: dict[str, Any] = {
            "helper": CUTY_LIVE_HELPER,
            "solver_url": CUTY_TURNSTILE_SOLVER_URL,
        }
        live = self._resolve_cuty_live(url)
        facts.update({
            "live_stage": live.get("stage"),
            "final_url": live.get("final_url"),
            "final_title": live.get("final_title"),
            "sitekey": live.get("sitekey"),
            "solver_error": live.get("solver_error"),
            "waited_seconds": live.get("waited_seconds"),
            "timeline": live.get("timeline") or [],
        })
        if live.get("status") == 1 and live.get("bypass_url"):
            return BypassResult(
                status=1,
                input_url=url,
                family=family,
                message="CUTY_LIVE_TURNSTILE_CHAIN_OK",
                bypass_url=live.get("bypass_url"),
                stage=live.get("stage") or "live-browser-turnstile-go",
                facts=facts,
                notes=[
                    "live browser helper uses same browser context for first form, Turnstile token injection, final timer, and /go submit",
                    "success is claimed only after the browser leaves cuttlinks/cuty to the downstream target",
                ],
            )
        return BypassResult(
            status=0,
            input_url=url,
            family=family,
            message="CUTY_LIVE_CHAIN_FAILED",
            stage=live.get("stage") or "live-browser",
            facts=facts,
            blockers=[str(live.get("solver_error") or live.get("message") or "live helper did not return downstream final URL")],
        )

    def _handle_lnbz(self, url: str) -> BypassResult:
        family = "lnbz.la"
        facts: dict[str, Any] = {}
        try:
            session = self._new_impersonated_session()
            page = session.get(url, timeout=self.timeout, allow_redirects=True)
            soup = BeautifulSoup(page.text, "html.parser")
            facts.update(self._common_facts_for_session(page, soup, session))
            facts["entry_url"] = page.url

            current = page
            current_soup = soup
            steps: list[dict[str, Any]] = []
            for index in range(1, 6):
                form = current_soup.select_one("form#go_d2") or current_soup.find("form")
                if current_soup.select_one("form#go-link"):
                    break
                if not form:
                    return BypassResult(
                        status=0,
                        input_url=url,
                        family=family,
                        message="LNBZ_CHAIN_FORM_NOT_FOUND",
                        stage=f"step-{index}",
                        facts=facts,
                        blockers=["expected entry/go_d2 form before final go-link page"],
                    )
                action = urljoin(current.url, form.get("action") or "")
                hidden = self._extract_hidden_inputs(form)
                steps.append({"index": index, "url": current.url, "action": action, "field_names": sorted(hidden.keys())})
                origin = f"{urlparse(current.url).scheme}://{urlparse(current.url).netloc}"
                current = session.post(
                    action,
                    data=hidden,
                    timeout=self.timeout,
                    allow_redirects=True,
                    headers={"Origin": origin, "Referer": current.url},
                )
                current_soup = BeautifulSoup(current.text, "html.parser")

            facts["steps"] = steps
            final_form = current_soup.select_one("form#go-link")
            if not final_form:
                return BypassResult(
                    status=0,
                    input_url=url,
                    family=family,
                    message="LNBZ_GO_LINK_FORM_NOT_FOUND",
                    stage="article-chain",
                    facts=facts,
                    blockers=["article/survey chain did not reach final form#go-link"],
                )

            hidden = self._extract_hidden_inputs(final_form)
            action = urljoin(current.url, final_form.get("action") or "/links/go")
            timer = self._extract_numeric_timer(current.text, default=15.0)
            wait_seconds = max(timer + 1.0, 16.0)
            facts["go_link_action"] = action
            facts["hidden_inputs"] = hidden
            facts["timer_seconds"] = timer
            facts["wait_seconds"] = wait_seconds
            time.sleep(wait_seconds)

            submit = session.post(
                action,
                data=hidden,
                timeout=self.timeout,
                headers={
                    "Origin": "https://lnbz.la",
                    "Referer": current.url,
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                },
            )
            payload = self._safe_json(submit)
            facts["submit_payload"] = payload
            target = self._clean_url(str(payload.get("url") or "")) or None
            if payload.get("status") == "success" and target:
                return BypassResult(
                    status=1,
                    input_url=url,
                    family=family,
                    message="LNBZ_ARTICLE_CHAIN_OK",
                    bypass_url=target,
                    stage="links-go",
                    facts=facts,
                    notes=["same-session article chain reached form#go-link and /links/go returned the downstream URL"],
                )

            return BypassResult(
                status=0,
                input_url=url,
                family=family,
                message="LNBZ_SUBMIT_FAILED",
                stage="links-go",
                facts=facts,
                blockers=[str(payload.get("message") or "links/go did not return success URL")],
            )
        except Exception as exc:
            return BypassResult(
                status=0,
                input_url=url,
                family=family,
                message="REQUEST_FAILED",
                facts=facts,
                blockers=[str(exc)],
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


    def _resolve_exe_live(self, url: str) -> dict[str, Any]:
        if not (os.path.exists(EXE_LIVE_HELPER) and os.path.exists(EXE_HELPER_PYTHON)):
            return {}

        env = os.environ.copy()
        helper_pythonpath_parts = [part for part in [EXE_HELPER_PYTHONPATH, HELPER_PYTHONPATH] if part]
        if helper_pythonpath_parts:
            existing = env.get("PYTHONPATH", "")
            helper_pythonpath = ":".join(helper_pythonpath_parts)
            env["PYTHONPATH"] = f"{helper_pythonpath}:{existing}" if existing else helper_pythonpath
        try:
            proc = subprocess.run(
                [
                    EXE_HELPER_PYTHON,
                    EXE_LIVE_HELPER,
                    url,
                    "--timeout",
                    str(EXE_BROWSER_TIMEOUT),
                    "--solver-url",
                    EXE_TURNSTILE_SOLVER_URL,
                ],
                capture_output=True,
                text=True,
                timeout=EXE_BROWSER_TIMEOUT + 30,
                env=env,
            )
        except subprocess.TimeoutExpired:
            return {"status": 0, "message": "exe live browser timeout", "stage": "live-browser-timeout"}
        except Exception as exc:
            return {"status": 0, "message": str(exc), "stage": "live-browser-error"}

        stdout = (proc.stdout or "").strip()
        if not stdout:
            return {"status": 0, "message": (proc.stderr or "").strip() or f"helper exit {proc.returncode}", "stage": "live-browser-no-output"}
        last_line = stdout.splitlines()[-1]
        try:
            payload = json.loads(last_line)
        except Exception:
            return {"status": 0, "message": (proc.stderr or "").strip() or f"helper output tidak valid: {last_line[:240]}", "stage": "live-browser-invalid-output"}
        if proc.returncode != 0 and not payload.get("message"):
            payload["message"] = f"helper exit {proc.returncode}"
        return payload

    def _resolve_cuty_live(self, url: str) -> dict[str, Any]:
        if not (os.path.exists(CUTY_LIVE_HELPER) and os.path.exists(CUTY_HELPER_PYTHON)):
            return {"status": 0, "message": "cuty live helper tidak tersedia"}

        env = os.environ.copy()
        helper_pythonpath_parts = [part for part in [CUTY_HELPER_PYTHONPATH, HELPER_PYTHONPATH] if part]
        if helper_pythonpath_parts:
            existing = env.get("PYTHONPATH", "")
            helper_pythonpath = ":".join(helper_pythonpath_parts)
            env["PYTHONPATH"] = f"{helper_pythonpath}:{existing}" if existing else helper_pythonpath
        try:
            proc = subprocess.run(
                [
                    CUTY_HELPER_PYTHON,
                    CUTY_LIVE_HELPER,
                    url,
                    "--timeout",
                    str(CUTY_BROWSER_TIMEOUT),
                    "--solver-url",
                    CUTY_TURNSTILE_SOLVER_URL,
                ],
                capture_output=True,
                text=True,
                timeout=CUTY_BROWSER_TIMEOUT + 30,
                env=env,
            )
        except subprocess.TimeoutExpired:
            return {"status": 0, "message": "cuty live browser timeout"}
        except Exception as exc:
            return {"status": 0, "message": str(exc)}

        stdout = (proc.stdout or "").strip()
        if not stdout:
            return {"status": 0, "message": (proc.stderr or "").strip() or f"helper exit {proc.returncode}"}
        last_line = stdout.splitlines()[-1]
        try:
            payload = json.loads(last_line)
        except Exception:
            return {"status": 0, "message": (proc.stderr or "").strip() or f"helper output tidak valid: {last_line[:240]}"}
        if proc.returncode != 0 and not payload.get("message"):
            payload["message"] = f"helper exit {proc.returncode}"
        return payload

    def _resolve_xut_live(self, url: str) -> dict[str, Any]:
        if not (os.path.exists(XUT_LIVE_HELPER) and os.path.exists(XUT_HELPER_PYTHON)):
            return {}

        env = os.environ.copy()
        helper_pythonpath_parts = [part for part in [XUT_HELPER_PYTHONPATH, HELPER_PYTHONPATH] if part]
        if helper_pythonpath_parts:
            existing = env.get("PYTHONPATH", "")
            helper_pythonpath = ":".join(helper_pythonpath_parts)
            env["PYTHONPATH"] = f"{helper_pythonpath}:{existing}" if existing else helper_pythonpath

        helper_cmd = [
            XUT_HELPER_PYTHON,
            XUT_LIVE_HELPER,
            url,
            "--timeout",
            str(XUT_BROWSER_TIMEOUT),
        ]
        xvfb_run = "/usr/bin/xvfb-run"
        if env.get("SHORTLINK_BYPASS_XUT_HEADLESS", "0").strip().lower() not in {"1", "true", "yes"} and os.path.exists(xvfb_run):
            helper_cmd = [xvfb_run, "-a", *helper_cmd]

        attempts: list[dict[str, Any]] = []
        max_attempts = max(1, XUT_LIVE_ATTEMPTS)
        for attempt_idx in range(1, max_attempts + 1):
            try:
                proc = subprocess.run(
                    helper_cmd,
                    capture_output=True,
                    text=True,
                    timeout=XUT_BROWSER_TIMEOUT + 60,
                    env=env,
                )
            except subprocess.TimeoutExpired:
                attempts.append({"idx": attempt_idx, "status": 0, "message": "XUT_LIVE_BROWSER_TIMEOUT", "stage": "live-browser-timeout"})
                continue
            except Exception as exc:
                attempts.append({"idx": attempt_idx, "status": 0, "message": f"XUT_LIVE_BROWSER_ERROR: {exc}", "stage": "live-browser-error"})
                continue

            stdout = (proc.stdout or "").strip()
            if not stdout:
                stderr = (proc.stderr or "").strip()
                attempts.append({
                    "idx": attempt_idx,
                    "status": 0,
                    "message": stderr or f"helper exit {proc.returncode}",
                    "stage": "live-browser-no-output",
                })
                continue

            last_line = stdout.splitlines()[-1]
            try:
                payload = json.loads(last_line)
            except Exception:
                stderr = (proc.stderr or "").strip()
                attempts.append({
                    "idx": attempt_idx,
                    "status": 0,
                    "message": stderr or f"helper output tidak valid: {last_line[:240]}",
                    "stage": "live-browser-invalid-output",
                })
                continue

            if proc.returncode != 0 and not payload.get("message"):
                payload["message"] = f"helper exit {proc.returncode}"
            payload["attempt_idx"] = attempt_idx
            if payload.get("status") == 1:
                if attempts:
                    payload.setdefault("facts", {})["previous_live_attempts"] = attempts
                return payload
            attempts.append({
                "idx": attempt_idx,
                "status": payload.get("status"),
                "message": payload.get("message"),
                "stage": payload.get("stage"),
            })

        last = attempts[-1] if attempts else {"status": 0, "message": "XUT_LIVE_BROWSER_NO_ATTEMPTS", "stage": "live-browser-error"}
        return {
            "status": 0,
            "message": last.get("message") or "XUT_LIVE_BROWSER_FAILED",
            "stage": last.get("stage") or "live-browser-error",
            "facts": {"live_attempts": attempts},
            "blockers": ["helper live browser gagal mencapai final oracle setelah retry"],
        }

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
        for match in re.finditer(r"aHR0[A-Za-z0-9+/=]{20,}", token):
            blob = match.group(0)
            for end in range(len(blob), 19, -1):
                fragment = blob[:end]
                for padded in {fragment, fragment + "=", fragment + "=="}:
                    try:
                        text = base64.b64decode(padded).decode("utf-8", errors="ignore")
                    except Exception:
                        continue
                    candidates.extend(URL_RE.findall(text))
        for candidate in candidates:
            if any(marker in candidate for marker in ["/links/back/", "/member/shortlinks/verify/", "/shortlink.php?"]):
                return self._clean_url(candidate)
        return None

    def _extract_sfl_ready_target(self, html: str) -> str | None:
        patterns = [
            r"window\.location\.href\s*=\s*['\"]([^'\"]+)['\"]",
            r"location\.href\s*=\s*['\"]([^'\"]+)['\"]",
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if not match:
                continue
            value = match.group(1).replace("\\/", "/")
            if value.startswith("http://") or value.startswith("https://"):
                return self._clean_url(value)
        return None

    def _safe_json(self, response: Any) -> dict[str, Any]:
        try:
            payload = response.json()
        except Exception:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _decode_gplinks_power_query(self, url: str) -> dict[str, str | None]:
        query = parse_qs(urlparse(url).query)
        return {
            "lid": self._base64_url_decode_first(query.get("lid", [None])[0]),
            "pid": self._base64_url_decode_first(query.get("pid", [None])[0]),
            "pages": self._base64_url_decode_first(query.get("pages", [None])[0]),
            "vid": query.get("vid", [None])[0],
        }

    def _base64_url_decode_first(self, value: str | None) -> str | None:
        if not value:
            return None
        normalized = value.replace("-", "+").replace("_", "/")
        normalized += "=" * ((4 - len(normalized) % 4) % 4)
        try:
            return base64.b64decode(normalized).decode("utf-8", errors="ignore")
        except Exception:
            return None

    def _extract_numeric_timer(self, html: str, default: float) -> float:
        patterns = [
            r'id=["\']timer["\'][^>]*>\s*(\d+(?:\.\d+)?)',
            r'class=["\'][^"\']*timer[^"\']*["\'][^>]*>\s*(\d+(?:\.\d+)?)',
            r'count\d*\s*=\s*(\d+(?:\.\d+)?)',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if not match:
                continue
            try:
                return float(match.group(1))
            except Exception:
                continue
        return default

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



    def _sfl_proxy_candidates(self) -> list[dict[str, str]]:
        candidates: list[dict[str, str]] = []
        env_proxy = os.getenv("SHORTLINK_BYPASS_SFL_PROXY", "").strip()
        if env_proxy:
            candidates.append({"http": env_proxy, "https": env_proxy})
        warp_proxy = os.getenv("SHORTLINK_BYPASS_WARP_PROXY", "http://127.0.0.1:40000").strip()
        if warp_proxy:
            candidates.append({"http": warp_proxy, "https": warp_proxy})
        deduped: list[dict[str, str]] = []
        seen: set[tuple[tuple[str, str], ...]] = set()
        for item in candidates:
            key = tuple(sorted(item.items()))
            if key not in seen:
                seen.add(key)
                deduped.append(item)
        return deduped

    def _is_cloudflare_block(self, response: Any, soup: BeautifulSoup | None = None) -> bool:
        title = ""
        if soup and soup.title and soup.title.string:
            title = soup.title.string.strip().lower()
        server = str(getattr(response, "headers", {}).get("server", "")).lower()
        text = str(getattr(response, "text", ""))[:2000].lower()
        if getattr(response, "status_code", None) in {403, 429} and "cloudflare" in (server + title + text):
            return True
        return "access denied" in title and "cloudflare" in title

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
