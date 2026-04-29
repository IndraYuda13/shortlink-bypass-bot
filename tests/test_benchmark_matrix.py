import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from benchmark_matrix import build_sample_jobs, write_jsonl_record, run_job


class BenchmarkMatrixTests(unittest.TestCase):
    def test_build_sample_jobs_filters_by_family_or_host(self):
        jobs = build_sample_jobs(family="exe.io", limit=5)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["host"], "exe.io")
        self.assertEqual(jobs[0]["url"], "https://exe.io/vkRI1")

    def test_write_jsonl_record_appends_one_json_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bench.jsonl"
            write_jsonl_record(path, {"host": "cuty.io", "status": 1})
            write_jsonl_record(path, {"host": "exe.io", "status": 1})
            rows = [json.loads(line) for line in path.read_text().splitlines()]
        self.assertEqual([row["host"] for row in rows], ["cuty.io", "exe.io"])

    def test_run_job_shapes_engine_result_with_profile(self):
        fake_result = Mock()
        fake_result.to_dict.return_value = {
            "status": 1,
            "family": "exe.io",
            "stage": "http-final",
            "bypass_url": "https://google.com",
            "facts": {"http_fast_waited_seconds": 61.0, "http_fast_timeline": [{"stage": "entry"}]},
        }
        with patch("benchmark_matrix.ShortlinkBypassEngine") as engine_cls:
            engine_cls.return_value.analyze.return_value = fake_result
            record = run_job({"host": "exe.io", "url": "https://exe.io/vkRI1", "status": "live_bypass"}, timeout=123)
        self.assertEqual(record["host"], "exe.io")
        self.assertEqual(record["result"]["status"], 1)
        self.assertEqual(record["profile"]["waited_seconds"], 61.0)
        engine_cls.assert_called_once_with(timeout=123)


if __name__ == "__main__":
    unittest.main()
