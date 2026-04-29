import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from engine import ShortlinkBypassEngine


class CutyTests(unittest.TestCase):
    def test_cuty_http_fast_result_returns_final_google(self):
        engine = ShortlinkBypassEngine()
        helper_result = {
            'status': 1,
            'stage': 'http-final',
            'bypass_url': 'https://www.google.com/',
            'final_url': 'https://www.google.com/',
            'sitekey': '0x4AAAAAAABnHbN4cNchLhd_',
            'waited_seconds': 70.2,
            'timeline': [{'stage': 'final', 'url': 'https://www.google.com/'}],
        }

        with patch.object(engine, '_resolve_cuty_http_fast', return_value=helper_result), patch.object(engine, '_resolve_cuty_live') as live:
            result = engine.analyze('https://cuty.io/AfaX6jx')

        self.assertEqual(result.family, 'cuty.io')
        self.assertEqual(result.status, 1)
        self.assertEqual(result.message, 'CUTY_HTTP_FAST_OK')
        self.assertEqual(result.stage, 'http-final')
        self.assertEqual(result.bypass_url, 'https://www.google.com/')
        self.assertEqual(result.facts['http_fast_waited_seconds'], 70.2)
        live.assert_not_called()

    def test_cuty_live_helper_result_returns_final_google(self):
        engine = ShortlinkBypassEngine()
        http_result = {'status': 0, 'stage': 'http-final', 'message': 'FINAL_DID_NOT_LEAVE_CUTTLINKS'}
        helper_result = {
            'status': 1,
            'stage': 'live-browser-turnstile-go',
            'bypass_url': 'https://www.google.com/',
            'final_url': 'https://www.google.com/',
            'final_title': 'Google',
            'sitekey': '0x4AAAAAAABnHbN4cNchLhd_',
            'waited_seconds': 62.5,
            'timeline': [{'stage': 'final', 'href': 'https://www.google.com/'}],
        }

        with patch.object(engine, '_resolve_cuty_http_fast', return_value=http_result), patch.object(engine, '_resolve_cuty_live', return_value=helper_result), patch('engine.CUTY_BROWSER_FALLBACK_ENABLED', True):
            result = engine.analyze('https://cuty.io/AfaX6jx')

        self.assertEqual(result.family, 'cuty.io')
        self.assertEqual(result.status, 1)
        self.assertEqual(result.message, 'CUTY_LIVE_TURNSTILE_CHAIN_OK')
        self.assertEqual(result.stage, 'live-browser-turnstile-go')
        self.assertEqual(result.bypass_url, 'https://www.google.com/')
        self.assertEqual(result.facts['sitekey'], '0x4AAAAAAABnHbN4cNchLhd_')

    def test_cuty_can_disable_browser_fallback_for_http_only_deployments(self):
        engine = ShortlinkBypassEngine()
        http_result = {'status': 0, 'stage': 'http-final', 'message': 'FINAL_DID_NOT_LEAVE_CUTTLINKS'}

        with patch.object(engine, '_resolve_cuty_http_fast', return_value=http_result), patch.object(engine, '_resolve_cuty_live') as live, patch('engine.CUTY_BROWSER_FALLBACK_ENABLED', False):
            result = engine.analyze('https://cuty.io/AfaX6jx')

        self.assertEqual(result.family, 'cuty.io')
        self.assertEqual(result.status, 0)
        self.assertEqual(result.message, 'CUTY_HTTP_FAST_FAILED')
        self.assertEqual(result.stage, 'http-final')
        self.assertIn('browser fallback disabled', result.blockers[0])
        live.assert_not_called()


class LnbzTests(unittest.TestCase):
    def test_lnbz_article_chain_posts_final_links_go(self):
        engine = ShortlinkBypassEngine()

        def response(url, text='', status_code=200, headers=None, payload=None):
            item = Mock()
            item.url = url
            item.text = text
            item.status_code = status_code
            item.headers = headers or {}
            item.json = Mock(return_value=payload or {})
            return item

        entry = response(
            'https://lnbz.la/Hmvp6',
            '<form action="https://avnsgames.com/article-one" method="post">'
            '<input name="url" value="https://lnbz.la/Hmvp6">'
            '<input name="token" value="tok1">'
            '<input name="alias" value="Hmvp6">'
            '</form>',
        )
        article_one = response(
            'https://avnsgames.com/article-one',
            '<form id="go_d2" action="https://avnsgames.com/article-two" method="post">'
            '<input name="a" value="1">'
            '</form>',
        )
        article_two = response(
            'https://avnsgames.com/article-two',
            '<form id="go_d2" action="https://lnbz.la/Hmvp6" method="post">'
            '<input name="b" value="2">'
            '</form>',
        )
        final_page = response(
            'https://lnbz.la/Hmvp6',
            '<span id="timer" class="timer">15</span>'
            '<form id="go-link" action="/links/go" method="post">'
            '<input name="_method" value="POST">'
            '<input name="ad_form_data" value="blob123">'
            '</form>',
        )
        submit = response(
            'https://lnbz.la/links/go',
            '{"status":"success","url":"https://cryptoearns.com/links/back/AaDZLgKQsnhy423EIS9c"}',
            payload={'status': 'success', 'message': '', 'url': 'https://cryptoearns.com/links/back/AaDZLgKQsnhy423EIS9c'},
        )
        fake_session = Mock()
        fake_session.get.return_value = entry
        fake_session.post.side_effect = [article_one, article_two, final_page, submit]
        fake_session.cookies.jar = []

        with patch.object(engine, '_new_impersonated_session', return_value=fake_session), patch('engine.time.sleep') as sleep:
            result = engine.analyze('https://lnbz.la/Hmvp6')

        self.assertEqual(result.family, 'lnbz.la')
        self.assertEqual(result.status, 1)
        self.assertEqual(result.message, 'LNBZ_ARTICLE_CHAIN_OK')
        self.assertEqual(result.stage, 'links-go')
        self.assertEqual(result.bypass_url, 'https://cryptoearns.com/links/back/AaDZLgKQsnhy423EIS9c')
        sleep.assert_called_once_with(16.0)
        self.assertEqual(fake_session.post.call_count, 4)
        final_call = fake_session.post.call_args_list[-1]
        self.assertEqual(final_call.args[0], 'https://lnbz.la/links/go')
        self.assertEqual(final_call.kwargs['data']['ad_form_data'], 'blob123')


class CutyHelperBehaviorTests(unittest.TestCase):
    def test_cuty_helper_uses_dynamic_port_and_returns_solver_error_timeline(self):
        source = Path('cuty_live_browser.py').read_text()
        self.assertIn('find_free_port', source)
        self.assertNotIn('self.port = 9240', source)
        self.assertIn('solver_error', source)
        self.assertIn('timeline', source)
        self.assertIn('SHORTLINK_BYPASS_TURNSTILE_POLL_INTERVAL', source)


if __name__ == '__main__':
    unittest.main()
