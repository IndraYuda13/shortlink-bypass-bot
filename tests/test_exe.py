import unittest
from unittest.mock import Mock, patch

from engine import ShortlinkBypassEngine


class ExeTests(unittest.TestCase):
    def test_exe_maps_two_stage_gate_without_claiming_final(self):
        engine = ShortlinkBypassEngine()

        def response(url, text='', status_code=200, headers=None):
            item = Mock()
            item.url = url
            item.text = text
            item.status_code = status_code
            item.headers = headers or {}
            return item

        entry = response('https://exe.io/vkRI1', '', 302, {'location': 'https://exeygo.com/vkRI1'})
        first_page = response(
            'https://exeygo.com/vkRI1',
            '''<html><head><title>exe.io</title><script>
            var app_vars = {captcha_type: "turnstile", counter_value: "6", counter_start: "DOMContentLoaded", turnstile_site_key: "0x4AAAAAACPCPhXQQr5wP1VW"};
            </script></head><body>
            <form id="before-captcha" method="post" action="/vkRI1">
              <input type="hidden" name="_method" value="POST">
              <input type="hidden" name="_csrfToken" value="csrf1">
              <input type="hidden" name="f_n" value="sle">
              <input type="hidden" name="_Token[fields]" value="tok1">
              <input type="hidden" name="_Token[unlocked]" value="cf-turnstile-response|g-recaptcha-response">
            </form></body></html>''',
        )
        second_page = response(
            'https://exeygo.com/vkRI1',
            '''<html><head><title>exe.io</title><script>
            var app_vars = {captcha_type: "turnstile", counter_value: "6", counter_start: "DOMContentLoaded", turnstile_site_key: "0x4AAAAAACPCPhXQQr5wP1VW"};
            </script></head><body>
            <form id="link-view" method="post" action="/vkRI1">
              <input type="hidden" name="_method" value="POST">
              <input type="hidden" name="_csrfToken" value="csrf1">
              <input type="hidden" name="ref" value="https://exeygo.com/vkri1">
              <input type="hidden" name="f_n" value="slc">
              <input type="hidden" name="_Token[fields]" value="tok2">
              <input type="hidden" name="_Token[unlocked]" value="cf-turnstile-response|g-recaptcha-response">
            </form></body></html>''',
        )

        fake_session = Mock()
        fake_session.get.side_effect = [entry, first_page]
        fake_session.post.return_value = second_page
        fake_session.cookies.jar = []

        with patch.object(engine, '_resolve_exe_http_fast', return_value={}), \
             patch.object(engine, '_new_impersonated_session', return_value=fake_session), \
             patch.object(engine, '_resolve_exe_live', return_value={}):
            result = engine.analyze('https://exe.io/vkRI1')

        self.assertEqual(result.family, 'exe.io')
        self.assertEqual(result.status, 0)
        self.assertEqual(result.message, 'EXE_GATE_MAPPED')
        self.assertEqual(result.stage, 'captcha-gate')
        self.assertEqual(result.facts['entry_redirect'], 'https://exeygo.com/vkRI1')
        self.assertEqual(result.facts['captcha_type'], 'turnstile')
        self.assertEqual(result.facts['sitekey'], '0x4AAAAAACPCPhXQQr5wP1VW')
        self.assertIn('valid Turnstile/reCAPTCHA token', result.blockers[0])

    def test_exe_http_fast_result_returns_final_google(self):
        engine = ShortlinkBypassEngine()
        http_fast = {"status": 1, "stage": "http-final", "bypass_url": "https://www.google.com/?gws_rd=ssl", "final_url": "https://www.google.com/?gws_rd=ssl", "waited_seconds": 71.3}
        with patch.object(engine, '_resolve_exe_http_fast', return_value=http_fast), \
             patch.object(engine, '_new_impersonated_session') as new_session, \
             patch.object(engine, '_resolve_exe_live') as live:
            result = engine.analyze('https://exe.io/vkRI1')

        new_session.assert_not_called()
        live.assert_not_called()
        self.assertEqual(result.status, 1)
        self.assertEqual(result.message, 'EXE_HTTP_FAST_OK')
        self.assertEqual(result.bypass_url, 'https://www.google.com/?gws_rd=ssl')
        self.assertEqual(result.stage, 'http-final')

    def test_exe_live_helper_result_returns_final_google(self):
        engine = ShortlinkBypassEngine()

        def response(url, text='', status_code=200, headers=None):
            item = Mock()
            item.url = url
            item.text = text
            item.status_code = status_code
            item.headers = headers or {}
            return item

        entry = response('https://exe.io/vkRI1', '', 302, {'location': 'https://exeygo.com/vkRI1'})
        first_page = response('https://exeygo.com/vkRI1', '<form id="before-captcha" action="/vkRI1"><input name="f_n" value="sle"></form>')
        second_page = response(
            'https://exeygo.com/vkRI1',
            '<script>var app_vars = {captcha_type: "turnstile", turnstile_site_key: "0x4AAAAAACPCPhXQQr5wP1VW"};</script><form id="link-view" action="/vkRI1"><input name="f_n" value="slc"></form>',
        )

        fake_session = Mock()
        fake_session.get.side_effect = [entry, first_page]
        fake_session.post.return_value = second_page
        fake_session.cookies.jar = []

        live = {"status": 1, "stage": "live-browser-turnstile-go", "bypass_url": "https://www.google.com/", "final_url": "https://www.google.com/"}
        with patch.object(engine, '_resolve_exe_http_fast', return_value={}), \
             patch.object(engine, '_new_impersonated_session', return_value=fake_session), \
             patch.object(engine, '_resolve_exe_live', return_value=live):
            result = engine.analyze('https://exe.io/vkRI1')

        self.assertEqual(result.status, 1)
        self.assertEqual(result.message, 'EXE_LIVE_TURNSTILE_CHAIN_OK')
        self.assertEqual(result.bypass_url, 'https://www.google.com/')
        self.assertEqual(result.stage, 'live-browser-turnstile-go')


if __name__ == '__main__':
    unittest.main()
