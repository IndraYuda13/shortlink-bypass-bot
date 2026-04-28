import unittest

from pathlib import Path

from cuty_http_fast import extract_form_payload, is_downstream_url, turnstile_sitekey


class CutyHttpFastTests(unittest.TestCase):
    def test_extract_free_form_payload(self):
        html = '<form id="free-submit-form" action="/AfaX6jx" method="post"><input name="_token" value="csrf"></form>'
        form = extract_form_payload(html, 'form#free-submit-form')
        self.assertTrue(form['found'])
        self.assertEqual(form['action'], '/AfaX6jx')
        self.assertEqual(form['data']['_token'], 'csrf')

    def test_turnstile_sitekey(self):
        html = '<div class="cf-turnstile" data-sitekey="0x4AAA"></div>'
        self.assertEqual(turnstile_sitekey(html), '0x4AAA')

    def test_downstream_oracle_rejects_cuty_hosts(self):
        self.assertFalse(is_downstream_url('https://cuttlinks.com/AfaX6jx'))
        self.assertFalse(is_downstream_url('https://cuty.io/AfaX6jx'))
        self.assertTrue(is_downstream_url('https://www.google.com/'))

    def test_vhit_lifecycle_is_opt_in_after_ablation(self):
        source = Path('cuty_http_fast.py').read_text()
        self.assertIn('SHORTLINK_BYPASS_CUTY_HTTP_VHIT', source)
        self.assertIn('vhit-skipped', source)


if __name__ == '__main__':
    unittest.main()
