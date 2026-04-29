import unittest

from timeline_profiler import profile_result, summarize_timeline


class TimelineProfilerTests(unittest.TestCase):
    def test_summarize_timeline_preserves_stage_order_and_status(self):
        timeline = [
            {"stage": "entry", "status": 302, "url": "https://cuty.io/AfaX6jx"},
            {"stage": "captcha", "status": 200, "sitekey": "0xSITE"},
            {"stage": "final", "status": 302, "location": "https://google.com"},
        ]
        summary = summarize_timeline(timeline)
        self.assertEqual(summary[0]["stage"], "entry")
        self.assertEqual(summary[0]["status"], 302)
        self.assertEqual(summary[1]["stage"], "captcha")
        self.assertEqual(summary[2]["location"], "https://google.com")

    def test_summarize_timeline_computes_duration_between_ts_fields(self):
        timeline = [
            {"stage": "entry", "ts": 10.0},
            {"stage": "captcha", "ts": 13.25},
            {"stage": "final", "ts": 20.0},
        ]
        summary = summarize_timeline(timeline)
        self.assertEqual(summary[0]["elapsed_from_previous"], 0.0)
        self.assertEqual(summary[1]["elapsed_from_previous"], 3.25)
        self.assertEqual(summary[2]["elapsed_from_previous"], 6.75)

    def test_profile_result_extracts_nested_http_fast_timeline(self):
        payload = {
            "status": 1,
            "family": "cuty.io",
            "stage": "http-final",
            "bypass_url": "https://google.com",
            "facts": {
                "http_fast_waited_seconds": 53.8,
                "http_fast_timeline": [{"stage": "entry"}, {"stage": "final", "location": "https://google.com"}],
            },
        }
        profile = profile_result(payload)
        self.assertEqual(profile["family"], "cuty.io")
        self.assertEqual(profile["waited_seconds"], 53.8)
        self.assertEqual(profile["timeline_source"], "facts.http_fast_timeline")
        self.assertEqual([item["stage"] for item in profile["timeline"]], ["entry", "final"])

    def test_profile_result_extracts_compact_http_fast_helper_wait(self):
        payload = {
            "status": 1,
            "family": "exe.io",
            "stage": "http-final",
            "bypass_url": "http://google.com",
            "facts": {
                "http_fast_helper": {"status": 1, "stage": "http-final", "waited_seconds": 56.8}
            },
        }
        profile = profile_result(payload)
        self.assertEqual(profile["waited_seconds"], 56.8)
        self.assertEqual(profile["timeline_source"], "none")


if __name__ == "__main__":
    unittest.main()
