import unittest
from unittest.mock import Mock, patch

from engine import ShortlinkBypassEngine


class Ez4shortTests(unittest.TestCase):
    def test_ez4short_fast_game5s_referer_flow_returns_final_target(self):
        engine = ShortlinkBypassEngine()

        def response(url, text='', status_code=200, headers=None, payload=None):
            item = Mock()
            item.url = url
            item.text = text
            item.status_code = status_code
            item.headers = headers or {}
            item.json = Mock(return_value=payload or {})
            return item

        final_page = response(
            'https://ez4short.com/qSyPzeo',
            '<html><span id="timer" class="timer">3</span>'
            '<form id="go-link" action="/links/go" method="post">'
            '<input name="_method" value="POST">'
            '<input name="_csrfToken" value="csrf123">'
            '<input name="ad_form_data" value="blob123">'
            '<input name="_Token[fields]" value="fields123">'
            '<input name="_Token[unlocked]" value="unlocked123">'
            '</form></html>',
        )
        submit = response(
            'https://ez4short.com/links/go',
            '{"status":"success","url":"https://tesskibidixxx.com"}',
            payload={'status': 'success', 'message': 'Go without Earn because Adblock', 'url': 'https://tesskibidixxx.com'},
        )
        fake_session = Mock()
        fake_session.get.return_value = final_page
        fake_session.post.return_value = submit
        fake_session.cookies.jar = []

        with patch.object(engine, '_new_impersonated_session', return_value=fake_session), patch('engine.time.sleep') as sleep:
            result = engine.analyze('https://ez4short.com/qSyPzeo')

        self.assertEqual(result.family, 'ez4short.com')
        self.assertEqual(result.status, 1)
        self.assertEqual(result.message, 'EZ4SHORT_FAST_CHAIN_OK')
        self.assertEqual(result.stage, 'game5s-referer-go-link')
        self.assertEqual(result.bypass_url, 'https://tesskibidixxx.com')
        sleep.assert_called_once_with(3.2)
        fake_session.get.assert_called_once_with(
            'https://ez4short.com/qSyPzeo',
            timeout=engine.timeout,
            allow_redirects=True,
            headers={'Referer': 'https://game5s.com/'},
        )


if __name__ == '__main__':
    unittest.main()
