#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from supported_sites import SUPPORTED_SITES


def run_one(sample_url: str, timeout: int) -> dict:
    started = time.time()
    proc = subprocess.run(
        [sys.executable, str(ROOT / "engine.py"), sample_url, "--pretty"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    elapsed = round(time.time() - started, 1)
    payload = None
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        payload = {"status": 0, "message": (proc.stderr or proc.stdout)[-500:], "stage": "invalid-output"}
    payload["wall_seconds"] = elapsed
    payload["returncode"] = proc.returncode
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=420)
    parser.add_argument("--hosts", default="", help="comma-separated hosts to measure")
    args = parser.parse_args()
    wanted = {x.strip() for x in args.hosts.split(",") if x.strip()}
    rows = []
    for site in SUPPORTED_SITES:
        if wanted and site.host not in wanted:
            continue
        row = {
            "host": site.host,
            "family": site.family,
            "status_label": site.status,
            "sample_url": site.sample_url,
            "expected_final": site.expected_final,
        }
        try:
            result = run_one(site.sample_url, args.timeout)
        except subprocess.TimeoutExpired:
            result = {"status": 0, "stage": "timeout", "message": f"timeout after {args.timeout}s", "wall_seconds": args.timeout}
        row.update({
            "status": result.get("status"),
            "message": result.get("message"),
            "stage": result.get("stage"),
            "bypass_url": result.get("bypass_url"),
            "wall_seconds": result.get("wall_seconds"),
            "engine_waited_seconds": (result.get("facts") or {}).get("http_fast_waited_seconds") or (result.get("facts") or {}).get("waited_seconds"),
        })
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
