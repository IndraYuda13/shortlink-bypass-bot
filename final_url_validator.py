from __future__ import annotations

from urllib.parse import urljoin, urlparse


def _host_variants(hosts: set[str] | frozenset[str]) -> set[str]:
    out: set[str] = set()
    for host in hosts:
        clean = (host or "").strip().lower()
        if not clean:
            continue
        out.add(clean)
        if clean.startswith("www."):
            out.add(clean[4:])
        else:
            out.add(f"www.{clean}")
    return out


def is_downstream_url(url: str | None, internal_hosts: set[str] | frozenset[str]) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = parsed.netloc.lower()
    return bool(host and host not in _host_variants(internal_hosts))


def choose_downstream_final_url(
    *,
    response_url: str | None,
    location: str | None,
    action_url: str,
    internal_hosts: set[str] | frozenset[str],
) -> str | None:
    """Pick the first trustworthy downstream target from a final submit response.

    Shortlink targets sometimes redirect a reward URL like /links/back/... to a
    plain homepage. The first downstream Location header is the stronger oracle
    than the post-redirect response URL, so callers should submit final forms
    with redirects disabled and pass both values here.
    """
    redirect_target = urljoin(action_url, location) if location else None
    if is_downstream_url(redirect_target, internal_hosts):
        return redirect_target
    if is_downstream_url(response_url, internal_hosts):
        return response_url
    return None
