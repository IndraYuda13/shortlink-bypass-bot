import unittest

from bot import TelegramShortlinkBot
from supported_sites import LIVE_BYPASS_HOSTS, SUPPORTED_SITES, registry_as_dicts, status_lines


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
        })
        self.assertEqual(LIVE_BYPASS_HOSTS, live_hosts)

    def test_registry_keeps_partial_and_analysis_hosts_separate(self):
        statuses = {site.host: site.status for site in SUPPORTED_SITES}
        self.assertEqual(statuses["oii.la"], "token_bypass")
        self.assertEqual(statuses["tpi.li"], "token_bypass")
        self.assertEqual(statuses["aii.sh"], "token_bypass")
        self.assertEqual(statuses["xut.io"], "live_bypass")
        self.assertEqual(statuses["cuty.io"], "live_bypass")
        self.assertEqual(statuses["gplinks.co"], "partial")
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
            "expected_final",
            "proof",
            "blockers",
            "notes",
        })
        self.assertTrue(any(item["host"] == "exe.io" and item["handler"] == "_handle_exe" for item in data))

    def test_status_lines_are_grouped_for_bot_and_api_docs(self):
        rendered = "\n".join(status_lines())
        self.assertIn("Live bypass:", rendered)
        self.assertIn("link.adlink.click", rendered)
        self.assertIn("shrinkme.click", rendered)
        self.assertIn("Token bypass:", rendered)
        self.assertIn("oii.la", rendered)
        self.assertIn("Partial / needs more work:", rendered)
        self.assertIn("gplinks.co", rendered)
        self.assertIn("xut.io", rendered)
        self.assertIn("exe.io", rendered)

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
