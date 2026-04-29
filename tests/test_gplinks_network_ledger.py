import pathlib
import unittest

from gplinks_live_browser import is_final_url


SOURCE = pathlib.Path("gplinks_live_browser.py").read_text()


class GplinksNetworkLedgerTests(unittest.TestCase):
    def test_gplinks_network_ledger_recorder_functions_exist(self):
        self.assertIn("def install_network_ledger_recorder", SOURCE)
        self.assertIn("def collect_network_ledger_events", SOURCE)

    def test_gplinks_network_ledger_recorder_hooks_safe_browser_boundaries(self):
        self.assertIn("window.fetch", SOURCE)
        self.assertIn("XMLHttpRequest.prototype.open", SOURCE)
        self.assertIn("XMLHttpRequest.prototype.send", SOURCE)
        self.assertIn("navigator.sendBeacon", SOURCE)
        self.assertIn("HTMLFormElement.prototype.submit", SOURCE)

    def test_gplinks_network_ledger_collects_resource_hints_and_cookie_snapshot(self):
        self.assertIn("performance.getEntriesByType('resource')", SOURCE)
        self.assertIn("cookie_snapshot", SOURCE)
        self.assertIn("document.cookie", SOURCE)
        self.assertIn("network_ledger", SOURCE)

    def test_gplinks_timeline_includes_network_ledger_snapshots(self):
        self.assertIn("install_network_ledger_recorder(driver)", SOURCE)
        self.assertIn("install_pre_navigation_recorders(driver)", SOURCE)
        self.assertIn("Page.addScriptToEvaluateOnNewDocument", SOURCE)
        self.assertIn('collect_network_ledger_events(driver, "powergam-network-ledger")', SOURCE)
        self.assertIn('collect_network_ledger_events(driver, "final-network-ledger")', SOURCE)
        self.assertIn("timeline.append(collect_network_ledger_events", SOURCE)

    def test_gplinks_live_final_url_oracle_stays_strict(self):
        self.assertFalse(is_final_url(None))
        self.assertFalse(is_final_url(""))
        self.assertFalse(is_final_url("javascript:alert(1)"))
        self.assertFalse(is_final_url("chrome-error://chromewebdata/"))
        self.assertFalse(is_final_url("https://gplinks.co/YVTC?pid=1&vid=2"))
        self.assertFalse(is_final_url("https://www.gplinks.co/link-error?alias=YVTC"))
        self.assertFalse(is_final_url("https://powergam.online/?lid=x"))
        self.assertFalse(is_final_url("https://www.powergam.online/path"))
        self.assertTrue(is_final_url("http://tesskibidixxx.com/"))
        self.assertTrue(is_final_url("https://satoshifaucet.io/links/back/id/XRP"))


if __name__ == "__main__":
    unittest.main()
