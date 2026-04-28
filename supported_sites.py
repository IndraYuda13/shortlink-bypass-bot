from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

SupportStatus = Literal["live_bypass", "token_bypass", "analysis_only", "partial", "unsupported"]


@dataclass(frozen=True)
class SupportedSite:
    host: str
    family: str
    status: SupportStatus
    handler: str | None
    command_alias: str
    sample_url: str
    expected_final: str | None = None
    proof: str | None = None
    blockers: tuple[str, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)


SUPPORTED_SITES: tuple[SupportedSite, ...] = (
    SupportedSite(
        host="link.adlink.click",
        family="link.adlink.click",
        status="live_bypass",
        handler="_handle_adlink_click",
        command_alias="adlink",
        sample_url="https://link.adlink.click/SfRi",
        expected_final="https://earn-pepe.com/member/shortlinks/verify/ca7c179027eb04abfb79",
        proof="Live engine recheck on 2026-04-28 returned the earn-pepe verify URL via blog-http-fast.",
        notes=("Uses curl_cffi browser impersonation against blog.adlink.click, with live browser fallback retained.",),
    ),
    SupportedSite(
        host="shrinkme.click",
        family="shrinkme.click",
        status="live_bypass",
        handler="_handle_shrinkme",
        command_alias="shrinkme",
        sample_url="https://shrinkme.click/ZTvkQYPJ",
        expected_final="https://claimcoin.in/links/back/kPw2COhFxD0pfQuGrXUz",
        proof="Live engine recheck on 2026-04-28 returned the claimcoin links/back URL via mrproblogger-direct.",
        notes=("Uses the ThemeZon/MrProBlogger shortcut and waits the downstream timer before /links/go.",),
    ),
    SupportedSite(
        host="ez4short.com",
        family="ez4short.com",
        status="live_bypass",
        handler="_handle_ez4short",
        command_alias="ez4short",
        sample_url="https://ez4short.com/qSyPzeo",
        expected_final="https://tesskibidixxx.com",
        proof="User live bot run returned the expected tesskibidixxx target for qSyPzeo.",
        notes=("Fast game5s.com referer lane unlocks the final go-link form for the captured sample.",),
    ),
    SupportedSite(
        host="lnbz.la",
        family="lnbz.la",
        status="live_bypass",
        handler="_handle_lnbz",
        command_alias="lnbz",
        sample_url="https://lnbz.la/Hmvp6",
        expected_final="https://cryptoearns.com/links/back/AaDZLgKQsnhy423EIS9c",
        proof="Prior live sample reached the cryptoearns links/back oracle through the browserless article chain.",
        notes=("Same-session avnsgames article/survey chain reaches /links/go for the captured sample.",),
    ),
    SupportedSite(
        host="oii.la",
        family="oii.la",
        status="token_bypass",
        handler="_handle_token_landing",
        command_alias="oii",
        sample_url="https://oii.la/BW8ntz",
        expected_final="https://onlyfaucet.com/links/back/vYal1NZ2dtDFTr5cXqUi/LTC/208faecab92bd6cc094014e046df165d",
        proof="User live bot run returned the onlyfaucet links/back URL from token extraction.",
        notes=("Token-tail extraction works, but the live Turnstile/timer completion lane is not yet proven.",),
    ),
    SupportedSite(
        host="tpi.li",
        family="tpi.li",
        status="token_bypass",
        handler="_handle_token_landing",
        command_alias="tpi",
        sample_url="https://tpi.li/Dd5xka",
        expected_final="https://99faucet.com/links/back/haBKjYrugRxDIVCpGqMo",
        proof="User live bot run returned the 99faucet links/back URL from token extraction.",
        notes=("Shares the token-tail family with oii.la; final captcha completion is not yet proven.",),
    ),
    SupportedSite(
        host="aii.sh",
        family="aii.sh",
        status="token_bypass",
        handler="_handle_token_landing",
        command_alias="aii",
        sample_url="https://aii.sh/CBygg8fn2s3",
        expected_final="https://coinadster.com/shortlink.php?short_key=1cnd9h...h9a",
        proof="Static ShrinkBixby token extraction exposed the coinadster final candidate.",
        notes=("Expected final is intentionally truncated in public status text until a fresh full oracle is captured.",),
    ),
    SupportedSite(
        host="xut.io",
        family="autodime.cwsafelinkphp",
        status="live_bypass",
        handler="_handle_autodime_cwsafelink",
        command_alias="xut",
        sample_url="https://xut.io/hd7AOJ",
        expected_final="http://tesskibidixxx.com",
        proof="Live helper verified xut -> autodime/IconCaptcha -> gamescrate Step 5 -> xut Step 6 -> Get Link -> http://tesskibidixxx.com/.",
        notes=(
            "IconCaptcha can still be flaky, so the helper keeps retries and structured failure facts.",
            "The final host currently resolves to browser NXDOMAIN, but the shortlink final href is live-proven.",
        ),
    ),
    SupportedSite(
        host="cuty.io",
        family="cuty.io",
        status="live_bypass",
        handler="_handle_cuty",
        command_alias="cuty",
        sample_url="https://cuty.io/AfaX6jx",
        expected_final="https://google.com",
        proof="Live engine recheck on 2026-04-28 returned google.com through the HTTP fast helper after Turnstile solve and /go submit.",
        notes=("HTTP helper is primary; VHit replay is opt-in; CDP browser helper remains fallback if the HTTP lane does not return a downstream final URL.",),
    ),
    SupportedSite(
        host="gplinks.co",
        family="gplinks.co",
        status="live_bypass",
        handler="_handle_gplinks",
        command_alias="gplinks",
        sample_url="https://gplinks.co/YVTC",
        expected_final="http://tesskibidixxx.com",
        proof="Live engine recheck on 2026-04-28 returned http://tesskibidixxx.com/ through the browser PowerGam + final Turnstile callback lane.",
        notes=("Uses live browser PowerGam steps, scroll/verify handling, local Turnstile solver, and the page's own final Get Link href oracle.",),
    ),
    SupportedSite(
        host="sfl.gl",
        family="sfl.gl",
        status="live_bypass",
        handler="_handle_sfl",
        command_alias="sfl",
        sample_url="https://sfl.gl/18PZXXI9",
        expected_final="https://google.com",
        proof="Live engine recheck on 2026-04-28 returned google.com through WARP proxy fallback and SafelinkU API flow.",
        notes=("Direct VPS egress is Cloudflare-blocked, so this handler falls back to the local WARP proxy at 127.0.0.1:40000.",),
    ),
    SupportedSite(
        host="exe.io",
        family="exe.io",
        status="live_bypass",
        handler="_handle_exe",
        command_alias="exe",
        sample_url="https://exe.io/vkRI1",
        expected_final="https://google.com",
        proof="Live engine recheck on 2026-04-28 followed exe.io -> exeygo.com, solved Turnstile, submitted go-link, and returned google.com.",
        notes=("Uses the same local Turnstile solver API as cuty, then submits the exeygo go-link form in the same browser context.",),
    ),
)

STATUS_LABELS: dict[SupportStatus, str] = {
    "live_bypass": "Live bypass",
    "token_bypass": "Token bypass",
    "analysis_only": "Analysis/token extraction",
    "partial": "Partial / needs more work",
    "unsupported": "Unsupported / not implemented yet",
}

LIVE_BYPASS_HOSTS = {site.host for site in SUPPORTED_SITES if site.status == "live_bypass"}


def sites_by_status(status: SupportStatus) -> list[SupportedSite]:
    return [site for site in SUPPORTED_SITES if site.status == status]


def registry_as_dicts() -> list[dict[str, object]]:
    data: list[dict[str, object]] = []
    for site in SUPPORTED_SITES:
        item = asdict(site)
        item["blockers"] = list(site.blockers)
        item["notes"] = list(site.notes)
        data.append(item)
    return data


def status_lines() -> list[str]:
    lines: list[str] = []
    for status in ("live_bypass", "token_bypass", "analysis_only", "partial", "unsupported"):
        sites = sites_by_status(status)  # type: ignore[arg-type]
        if not sites:
            continue
        if lines:
            lines.append("")
        lines.append(f"{STATUS_LABELS[status]}:")  # type: ignore[index]
        for site in sites:
            suffix = f" -> {site.expected_final}" if site.expected_final else ""
            lines.append(f"- {site.host} ({site.command_alias}){suffix}")
    return lines
