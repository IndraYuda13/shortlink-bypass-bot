from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import requests
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_TIMEOUT = 30
ADLINK_BROWSER_TIMEOUT = int(os.getenv("SHORTLINK_BYPASS_ADLINK_BROWSER_TIMEOUT", "240"))
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

        themezon = self._resolve_shrinkme_themezon(url, continue_hint)
        if themezon:
            facts["themezon"] = themezon
            article_url = themezon.get("article_url")
            if article_url and article_url not in embedded_urls:
                embedded_urls.append(article_url)
                facts["embedded_urls"] = embedded_urls
            if article_url:
                return BypassResult(
                    status=1,
                    input_url=url,
                    family="shrinkme.click",
                    message="THEMEZON_ARTICLE_EXTRACTED",
                    bypass_url=article_url,
                    stage="themezon-hop",
                    facts=facts,
                    notes=[
                        "themezon hop berhasil direplay via HTTP dengan referer shrinkme yang benar",
                        "hasil ini masih article/interstitial target, bukan downstream reward-site final oracle",
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

    def _extract_runtime_config(self, html: str) -> dict[str, Any]:
        facts: dict[str, Any] = {}
        patterns = {
            "captcha_type": r"[\"']?captcha_type[\"']?\s*[:=]\s*[\"']([^\"']+)",
            "counter_value": r"[\"']?counter_value[\"']?\s*[:=]\s*[\"']?(\d+)",
            "counter_start": r"[\"']?counter_start[\"']?\s*[:=]\s*[\"']([^\"']+)",
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
        sitekeys = [value for value in dict.fromkeys(sitekeys) if value]
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

    def _is_cloudflare_challenge(self, response: requests.Response) -> bool:
        text = response.text.lower()
        return (
            response.status_code == 403
            and "cloudflare" in (response.headers.get("server", "").lower() + text)
            and "just a moment" in text
        )

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
