from __future__ import annotations

from typing import Any


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def summarize_timeline(timeline: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    previous_ts: float | None = None
    for index, item in enumerate(timeline or []):
        stage = str(item.get("stage") or f"step-{index + 1}")
        row: dict[str, Any] = {"index": index, "stage": stage}
        for key in ("status", "url", "location", "downstream", "message", "sitekey"):
            if key in item and item.get(key) is not None:
                row[key] = item.get(key)
        current_ts = _safe_float(item.get("ts") or item.get("timestamp") or item.get("elapsed"))
        if current_ts is not None:
            if previous_ts is None:
                row["elapsed_from_previous"] = 0.0
            else:
                row["elapsed_from_previous"] = round(max(0.0, current_ts - previous_ts), 3)
            previous_ts = current_ts
        summary.append(row)
    return summary


def _timeline_from_payload(payload: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    facts = payload.get("facts") if isinstance(payload.get("facts"), dict) else {}
    if isinstance(facts.get("http_fast_timeline"), list):
        return "facts.http_fast_timeline", facts["http_fast_timeline"]
    if isinstance(facts.get("timeline"), list):
        return "facts.timeline", facts["timeline"]
    if isinstance(payload.get("timeline"), list):
        return "timeline", payload["timeline"]
    return "none", []


def profile_result(payload: dict[str, Any]) -> dict[str, Any]:
    source, timeline = _timeline_from_payload(payload)
    facts = payload.get("facts") if isinstance(payload.get("facts"), dict) else {}
    waited = payload.get("waited_seconds")
    if waited is None:
        waited = facts.get("http_fast_waited_seconds") or facts.get("waited_seconds")
    if waited is None and isinstance(facts.get("http_fast_helper"), dict):
        waited = facts["http_fast_helper"].get("waited_seconds")
    return {
        "status": payload.get("status"),
        "family": payload.get("family"),
        "stage": payload.get("stage"),
        "bypass_url": payload.get("bypass_url"),
        "waited_seconds": waited,
        "timeline_source": source,
        "timeline": summarize_timeline(timeline),
    }
