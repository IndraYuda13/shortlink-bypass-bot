import unittest

from final_url_validator import choose_downstream_final_url, is_downstream_url


class FinalUrlValidatorTests(unittest.TestCase):
    def test_prefers_downstream_location_before_redirect_homepage(self):
        chosen = choose_downstream_final_url(
            response_url="https://satoshifaucet.io/",
            location="https://satoshifaucet.io/links/back/0IXOFkwis5HjxoZ6CbL1/XRP",
            action_url="https://exeygo.com/links/go",
            internal_hosts={"exe.io", "exeygo.com"},
        )
        self.assertEqual(chosen, "https://satoshifaucet.io/links/back/0IXOFkwis5HjxoZ6CbL1/XRP")

    def test_falls_back_to_response_url_when_location_missing(self):
        chosen = choose_downstream_final_url(
            response_url="https://www.google.com/?gws_rd=ssl",
            location=None,
            action_url="https://exeygo.com/links/go",
            internal_hosts={"exe.io", "exeygo.com"},
        )
        self.assertEqual(chosen, "https://www.google.com/?gws_rd=ssl")

    def test_rejects_internal_location_and_response(self):
        chosen = choose_downstream_final_url(
            response_url="https://exeygo.com/links/go",
            location="/labNYA",
            action_url="https://exeygo.com/links/go",
            internal_hosts={"exe.io", "exeygo.com"},
        )
        self.assertIsNone(chosen)

    def test_downstream_host_matching_includes_www_variants(self):
        self.assertFalse(is_downstream_url("https://www.cuttlinks.com/AfaX6jx", {"cuty.io", "cuttlinks.com"}))
        self.assertTrue(is_downstream_url("https://satoshifaucet.io/links/back/id/XRP", {"exe.io", "exeygo.com"}))


if __name__ == "__main__":
    unittest.main()
