import unittest

from bot import TelegramShortlinkBot
from supported_sites import (
    LIVE_BYPASS_HOSTS,
    SUPPORTED_SITES,
    display_groups_as_dicts,
    registry_as_dicts,
    status_lines,
)


class SupportedSitesRegistryTests(unittest.TestCase):
    def test_registry_marks_only_proven_live_hosts_as_live_bypass(self):
        live_hosts = {site.host for site in SUPPORTED_SITES if site.status == "live_bypass"}
        self.assertEqual(live_hosts, {
            "link.adlink.click",
            "shrinkme.click",
            "ez4short.com",
            "lnbz.la",
            "sfl.gl",
            "xut.io",
            "cuty.io",
            "exe.io",
            "gplinks.co",
        })
        self.assertEqual(LIVE_BYPASS_HOSTS, live_hosts)

    def test_registry_keeps_partial_and_analysis_hosts_separate(self):
        statuses = {site.host: site.status for site in SUPPORTED_SITES}
        self.assertEqual(statuses["oii.la"], "token_bypass")
        self.assertEqual(statuses["tpi.li"], "token_bypass")
        self.assertEqual(statuses["aii.sh"], "token_bypass")
        self.assertEqual(statuses["xut.io"], "live_bypass")
        self.assertEqual(statuses["cuty.io"], "live_bypass")
        self.assertEqual(statuses["gplinks.co"], "live_bypass")
        self.assertEqual(statuses["sfl.gl"], "live_bypass")
        self.assertEqual(statuses["exe.io"], "live_bypass")

    def test_registry_exports_api_ready_dicts(self):
        data = registry_as_dicts()
        first = data[0]
        self.assertEqual(set(first), {
            "host",
            "family",
            "status",
            "handler",
            "command_alias",
            "sample_url",
            "method_summary",
            "solve_time_label",
            "solve_time_seconds_min",
            "solve_time_seconds_max",
            "expected_final",
            "proof",
            "blockers",
            "notes",
        })
        self.assertTrue(any(
            item["host"] == "exe.io"
            and item["handler"] == "_handle_exe"
            and item["solve_time_label"] == "±61-72s"
            and "Turnstile" in item["method_summary"]
            for item in data
        ))

    def test_display_groups_are_api_ready_and_ranked_by_speed(self):
        data = display_groups_as_dicts()
        self.assertEqual(data[0], {
            "rank": 1,
            "hosts": ["aii.sh"],
            "solve_time_label": "±0.9s",
            "method_summary": "token-tail extraction",
        })
        self.assertEqual(data[1]["hosts"], ["oii.la", "tpi.li"])
        self.assertEqual(data[-1]["hosts"], ["gplinks.co"])
        self.assertEqual(data[-1]["solve_time_label"], "±149-150s")

    def test_status_lines_are_grouped_for_bot_and_api_docs(self):
        rendered = "\n".join(status_lines())
        self.assertIn("Supported sites + estimasi waktu:", rendered)
        self.assertIn("1. aii.sh ±0.9s", rendered)
        self.assertIn("2. oii.la / tpi.li ±1.8s", rendered)
        self.assertIn("8. cuty.io ±54-76s", rendered)
        self.assertIn("9. exe.io ±61-72s", rendered)
        self.assertIn("10. xut.io ±97-109s", rendered)
        self.assertIn("11. gplinks.co ±149-150s", rendered)

    def test_bot_status_uses_registry_not_hardcoded_old_list(self):
        bot = TelegramShortlinkBot("123:ABC")
        text = bot.status_text()
        self.assertIn("ez4short.com", text)
        self.assertIn("lnbz.la", text)
        self.assertIn("sfl.gl", text)
        self.assertIn("exe.io", text)
        self.assertNotIn("Belum ada handler", text)


if __name__ == "__main__":
    unittest.main()
