import unittest
from unittest.mock import Mock, patch

from engine import ShortlinkBypassEngine


class SflTests(unittest.TestCase):
    def test_extracts_google_from_ready_page_window_location(self):
        engine = ShortlinkBypassEngine()
        html = '<script>window.location.href = "https:\\/\\/google.com";</script>'

        self.assertEqual(engine._extract_sfl_ready_target(html), 'https://google.com')

    def test_sfl_api_flow_returns_ready_page_target(self):
        engine = ShortlinkBypassEngine()

        def response(url, text='', status_code=200, headers=None):
            item = Mock()
            item.url = url
            item.text = text
            item.status_code = status_code
            item.headers = headers or {}
            item.json = Mock(return_value={})
            return item

        entry = response(
            'https://sfl.gl/18PZXXI9',
            '<form action="https://app.khaddavi.net/redirect.php" method="GET">'
            '<input name="ray_id" value="ray123"><input name="alias" value="18PZXXI9"></form>',
        )
        redirect = response(
            'https://app.khaddavi.net/redirect.php?ray_id=ray123&alias=18PZXXI9',
            '',
            302,
            {'location': '/article/'},
        )
        article = response('https://app.khaddavi.net/article/', '<title>Article</title>')
        session_resp = response('https://app.khaddavi.net/api/session', '{}')
        session_resp.json.return_value = {'step': 1, 'fb': False, 'captcha': None, 'passcode': False}
        verify_resp = response('https://app.khaddavi.net/api/verify', '{}')
        verify_resp.json.return_value = {'message': 'OK', 'target': 'https://app.khaddavi.net/redirect.php?ray_id=ray456'}
        go_resp = response('https://app.khaddavi.net/api/go', '{}')
        go_resp.json.return_value = {'url': 'https://sfl.gl/ready/go?t=abc&a=MThQWlhYSTk%3D'}
        ready = response('https://sfl.gl/ready/go?t=abc&a=MThQWlhYSTk%3D', '<script>window.location.href = "https:\\/\\/google.com";</script>')

        fake_session = Mock()
        fake_session.get.side_effect = [entry, redirect, article, ready]
        fake_session.post.side_effect = [session_resp, verify_resp, go_resp]
        fake_session.cookies.jar = []

        with patch.object(engine, '_new_impersonated_session', return_value=fake_session), patch('engine.time.sleep') as sleep:
            result = engine.analyze('https://sfl.gl/18PZXXI9')

        self.assertEqual(result.family, 'sfl.gl')
        self.assertEqual(result.status, 1)
        self.assertEqual(result.message, 'SFL_API_FLOW_OK')
        self.assertEqual(result.stage, 'ready-page')
        self.assertEqual(result.bypass_url, 'https://google.com')
        sleep.assert_called_once_with(10)


if __name__ == '__main__':
    unittest.main()
