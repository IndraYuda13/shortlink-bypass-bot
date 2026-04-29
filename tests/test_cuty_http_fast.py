import unittest
from unittest.mock import Mock, patch

from pathlib import Path

from cuty_http_fast import extract_form_payload, is_downstream_url, run, turnstile_sitekey


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

    def test_run_prefers_full_redirect_location_before_following_to_homepage(self):
        entry = Mock(status_code=302, url='https://cuty.io/AfaX6jx', headers={'location': 'https://cuttlinks.com/auth/AfaX6jx'}, text='')
        auth = Mock(status_code=302, url='https://cuttlinks.com/auth/AfaX6jx', headers={'location': 'https://cuttlinks.com/AfaX6jx'}, text='')
        first = Mock(status_code=200, url='https://cuttlinks.com/AfaX6jx', headers={}, text='<form id="free-submit-form" action="/AfaX6jx" method="post"><input name="_token" value="csrf"></form>')
        captcha = Mock(status_code=200, url='https://cuttlinks.com/AfaX6jx', headers={}, text='<div class="cf-turnstile" data-sitekey="0xSITE"></div><form id="free-submit-form" action="/AfaX6jx" method="post"><input name="_token" value="csrf"></form>')
        last = Mock(status_code=200, url='https://cuttlinks.com/AfaX6jx', headers={}, text='<form id="submit-form" action="/links/go" method="post"><input name="ad_form_data" value="encrypted"></form>')
        final = Mock(status_code=302, url='https://cuttlinks.com/links/go', headers={'location': 'https://satoshifaucet.io/links/back/full/CUTY'}, text='')
        session = Mock()
        session.get.side_effect = [entry, auth, first]
        session.post.side_effect = [captcha, last, final]
        session.cookies.jar = []
        with patch('cuty_http_fast.curl_requests.Session', return_value=session), patch('cuty_http_fast.solve_turnstile', return_value='TOKEN'), patch('cuty_http_fast.time.sleep'):
            result = run('https://cuty.io/AfaX6jx', timeout=30, solver_url='http://127.0.0.1:5000')
        self.assertEqual(result['status'], 1)
        self.assertEqual(result['bypass_url'], 'https://satoshifaucet.io/links/back/full/CUTY')
        self.assertEqual(result['timeline'][-1]['downstream'], 'https://satoshifaucet.io/links/back/full/CUTY')


if __name__ == '__main__':
    unittest.main()
