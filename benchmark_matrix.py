#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engine import ShortlinkBypassEngine
from supported_sites import SUPPORTED_SITES
from timeline_profiler import profile_result


def build_sample_jobs(family: str | None = None, limit: int | None = None) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    needle = (family or "").strip().lower()
    for site in SUPPORTED_SITES:
        if needle and needle not in {site.host.lower(), site.family.lower(), site.command_alias.lower()}:
            continue
        selected.append({
            "host": site.host,
            "family": site.family,
            "status": site.status,
            "url": site.sample_url,
            "expected_final": site.expected_final,
            "method_summary": site.method_summary,
        })
        if limit and len(selected) >= limit:
            break
    return selected


def write_jsonl_record(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def run_job(job: dict[str, Any], timeout: int) -> dict[str, Any]:
    started = time.time()
    engine = ShortlinkBypassEngine(timeout=timeout)
    try:
        result = engine.analyze(str(job["url"])).to_dict()
    except Exception as exc:
        result = {"status": 0, "family": job.get("family"), "stage": "exception", "blockers": [str(exc)]}
    elapsed = round(time.time() - started, 3)
    return {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "host": job.get("host"),
        "family": job.get("family"),
        "input_url": job.get("url"),
        "expected_final": job.get("expected_final"),
        "elapsed_wall_seconds": elapsed,
        "result": result,
        "profile": profile_result(result),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run shortlink bypass benchmark matrix and write JSONL records.")
    parser.add_argument("--family", help="Filter by host/family/command alias, for example exe.io or cuty")
    parser.add_argument("--limit", type=int, help="Maximum number of sample jobs to run")
    parser.add_argument("--timeout", type=int, default=30, help="Engine request timeout, not helper timeout")
    parser.add_argument("--output", default="artifacts/active/benchmark-matrix/latest.jsonl", help="JSONL output path")
    parser.add_argument("--print", action="store_true", help="Print each record as compact JSON after writing it")
    args = parser.parse_args()

    jobs = build_sample_jobs(args.family, args.limit)
    if not jobs:
        print(json.dumps({"status": 0, "message": "NO_JOBS_MATCH_FILTER", "family": args.family}, ensure_ascii=False))
        return 1
    output = Path(args.output)
    for job in jobs:
        record = run_job(job, args.timeout)
        write_jsonl_record(output, record)
        if args.print:
            print(json.dumps(record, ensure_ascii=False, sort_keys=True))
    print(json.dumps({"status": 1, "jobs": len(jobs), "output": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
