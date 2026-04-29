import unittest
from unittest.mock import Mock, patch

from exe_http_fast import extract_app_vars, extract_form_payload, is_downstream_url, run


class ExeHttpFastTests(unittest.TestCase):
    def test_extract_app_vars_from_script(self):
        html = '<script>var app_vars = {captcha_type: "turnstile", counter_value: "6", turnstile_site_key: "0xSITE"};</script>'
        self.assertEqual(extract_app_vars(html)['turnstile_site_key'], '0xSITE')
        self.assertEqual(extract_app_vars(html)['counter_value'], '6')

    def test_extract_form_payload(self):
        html = '''<form id="go-link" action="/links/go" method="post">
            <input name="_csrfToken" value="csrf">
            <input name="ad_form_data" value="payload">
            <textarea name="cf-turnstile-response"></textarea>
        </form>'''
        payload = extract_form_payload(html, form_selector='form#go-link')
        self.assertEqual(payload['action'], '/links/go')
        self.assertEqual(payload['data']['_csrfToken'], 'csrf')
        self.assertEqual(payload['data']['ad_form_data'], 'payload')
        self.assertIn('cf-turnstile-response', payload['data'])

    def test_downstream_url_oracle(self):
        self.assertFalse(is_downstream_url('https://exe.io/vkRI1'))
        self.assertFalse(is_downstream_url('https://exeygo.com/vkRI1'))
        self.assertTrue(is_downstream_url('https://www.google.com/?gws_rd=ssl'))

    def test_run_returns_final_from_http_chain(self):
        entry = Mock(status_code=302, url='https://exe.io/vkRI1', headers={'location': 'https://exeygo.com/vkRI1'}, text='')
        first = Mock(status_code=200, url='https://exeygo.com/vkRI1', headers={}, text='''<script>var app_vars = {captcha_type:"turnstile", counter_value:"0", turnstile_site_key:"0xSITE"};</script><form id="before-captcha" action="/vkRI1" method="post"><input name="_csrfToken" value="csrf"><input name="f_n" value="sle"></form>''')
        second = Mock(status_code=200, url='https://exeygo.com/vkRI1', headers={}, text='''<script>var app_vars = {captcha_type:"turnstile", counter_value:"0", turnstile_site_key:"0xSITE"};</script><form id="link-view" action="/vkRI1" method="post"><input name="_csrfToken" value="csrf"><input name="f_n" value="slc"><input name="ref" value="https://exeygo.com/vkri1"></form>''')
        go_page = Mock(status_code=200, url='https://exeygo.com/vkRI1', headers={}, text='''<form id="go-link" action="/links/go" method="post"><input name="_csrfToken" value="csrf"><input name="ad_form_data" value="encrypted"></form>''')
        final = Mock(status_code=200, url='https://www.google.com/?gws_rd=ssl', headers={}, text='<title>Google</title>')
        session = Mock()
        session.get.side_effect = [entry, first]
        session.post.side_effect = [second, go_page, final]
        session.cookies.jar = []
        with patch('exe_http_fast.curl_requests.Session', return_value=session), patch('exe_http_fast.solve_turnstile', return_value='TOKEN'), patch('exe_http_fast.time.sleep'):
            result = run('https://exe.io/vkRI1', timeout=30, solver_url='http://127.0.0.1:5000')
        self.assertEqual(result['status'], 1)
        self.assertEqual(result['bypass_url'], 'https://www.google.com/?gws_rd=ssl')
        self.assertEqual(result['stage'], 'http-final')

    def test_run_prefers_full_redirect_location_before_following_to_homepage(self):
        entry = Mock(status_code=302, url='https://exe.io/labNYA', headers={'location': 'https://exeygo.com/labNYA'}, text='')
        first = Mock(status_code=200, url='https://exeygo.com/labNYA', headers={}, text='''<script>var app_vars = {captcha_type:"turnstile", counter_value:"0", turnstile_site_key:"0xSITE"};</script><form id="before-captcha" action="/labNYA" method="post"><input name="_csrfToken" value="csrf"><input name="f_n" value="sle"></form>''')
        second = Mock(status_code=200, url='https://exeygo.com/labNYA', headers={}, text='''<script>var app_vars = {captcha_type:"turnstile", counter_value:"0", turnstile_site_key:"0xSITE"};</script><form id="link-view" action="/labNYA" method="post"><input name="_csrfToken" value="csrf"><input name="f_n" value="slc"><input name="ref" value="https://exeygo.com/labNYA"></form>''')
        go_page = Mock(status_code=200, url='https://exeygo.com/labNYA', headers={}, text='''<form id="go-link" action="/links/go" method="post"><input name="_csrfToken" value="csrf"><input name="ad_form_data" value="encrypted"></form>''')
        final = Mock(status_code=302, url='https://exeygo.com/links/go', headers={'location': 'https://satoshifaucet.io/links/back/0IXOFkwis5HjxoZ6CbL1/XRP'}, text='')
        session = Mock()
        session.get.side_effect = [entry, first]
        session.post.side_effect = [second, go_page, final]
        session.cookies.jar = []
        with patch('exe_http_fast.curl_requests.Session', return_value=session), patch('exe_http_fast.solve_turnstile', return_value='TOKEN'), patch('exe_http_fast.time.sleep'):
            result = run('https://exe.io/labNYA', timeout=30, solver_url='http://127.0.0.1:5000')
        self.assertEqual(result['status'], 1)
        self.assertEqual(result['bypass_url'], 'https://satoshifaucet.io/links/back/0IXOFkwis5HjxoZ6CbL1/XRP')
        self.assertEqual(result['timeline'][-1]['downstream'], 'https://satoshifaucet.io/links/back/0IXOFkwis5HjxoZ6CbL1/XRP')


if __name__ == '__main__':
    unittest.main()
