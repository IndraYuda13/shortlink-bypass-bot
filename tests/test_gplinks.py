import unittest
from unittest.mock import Mock, patch

from engine import ShortlinkBypassEngine
from gplinks_live_browser import import_driver_cookies_to_session, try_http_final_gate_from_browser


class GplinksTests(unittest.TestCase):
    def test_gplinks_maps_powergam_query_and_target_candidate(self):
        engine = ShortlinkBypassEngine()

        def response(url, text='', status_code=200, headers=None):
            item = Mock()
            item.url = url
            item.text = text
            item.status_code = status_code
            item.headers = headers or {}
            return item

        entry = response(
            'https://gplinks.co/YVTC',
            '',
            302,
            {'location': 'https://powergam.online?lid=WVZUQw&pid=MTIyNDYyMg&vid=MTAxNzc2MzQ1Mw&pages=Mw'},
        )
        power = response(
            'https://powergam.online?lid=WVZUQw&pid=MTIyNDYyMg&vid=MTAxNzc2MzQ1Mw&pages=Mw',
            '<html><head><title>Please Wait... | PowerGam</title></head><body>'
            '<form id="adsForm" method="POST">'
            '<input name="form_name" value="ads-track-data">'
            '<input name="step_id" value="">'
            '<input name="ad_impressions" value="">'
            '<input name="visitor_id" value="">'
            '<input name="next_target" value="">'
            '</form></body></html>',
        )
        fake_session = Mock()
        fake_session.get.side_effect = [entry, power]
        fake_session.cookies.jar = []

        with patch.object(engine, '_resolve_gplinks_http_fast', return_value={'status': 0, 'stage': 'powergam-ledger', 'message': 'HTTP_FAST_POWERGAM_LEDGER_REJECTED'}), \
             patch.object(engine, '_resolve_gplinks_live', return_value={}), \
             patch.object(engine, '_new_impersonated_session', return_value=fake_session):
            result = engine.analyze('https://gplinks.co/YVTC')

        self.assertEqual(result.family, 'gplinks.co')
        self.assertEqual(result.status, 0)
        self.assertEqual(result.message, 'POWERGAM_STEPS_MAPPED')
        self.assertEqual(result.stage, 'powergam-mapped')
        self.assertEqual(result.facts['decoded_query']['lid'], 'YVTC')
        self.assertEqual(result.facts['decoded_query']['pid'], '1224622')
        self.assertEqual(result.facts['decoded_query']['pages'], '3')
        self.assertEqual(result.facts['target_final_candidate'], 'https://gplinks.co/YVTC?pid=1224622&vid=MTAxNzc2MzQ1Mw')
        self.assertTrue(result.blockers)

    @patch('engine.GPLINKS_HTTP_FAST_ENABLED', True)
    def test_gplinks_promotes_http_fast_helper_final_url_when_enabled(self):
        engine = ShortlinkBypassEngine()
        with patch.object(engine, '_resolve_gplinks_http_fast', return_value={
            'status': 1,
            'stage': 'http-fast',
            'bypass_url': 'http://tesskibidixxx.com/',
            'decoded_query': {'lid': 'YVTC', 'pid': '1224622', 'vid': '1019365269'},
            'sitekey': '0x4AAAAAAAynCEcs0RV-UleY',
            'token_used': True,
            'token_source': 'prewarm',
            'waited_seconds': 31.2,
        }), patch.object(engine, '_resolve_gplinks_live') as live:
            result = engine.analyze('https://gplinks.co/YVTC')

        live.assert_not_called()
        self.assertEqual(result.family, 'gplinks.co')
        self.assertEqual(result.status, 1)
        self.assertEqual(result.message, 'GPLINKS_FINAL_OK')
        self.assertEqual(result.stage, 'http-fast')
        self.assertEqual(result.bypass_url, 'http://tesskibidixxx.com/')
        self.assertTrue(result.facts['token_used'])
        self.assertEqual(result.facts['token_source'], 'prewarm')

    def test_gplinks_helper_keeps_direct_powergam_flag(self):
        source = __import__('pathlib').Path('gplinks_live_browser.py').read_text()
        self.assertIn('SHORTLINK_BYPASS_GPLINKS_DIRECT_POWERGAM', source)
        self.assertIn('SHORTLINK_BYPASS_GPLINKS_NAVIGATE_FINAL', source)
        self.assertIn('--disable-background-timer-throttling', source)
        self.assertIn('import_session_cookies', source)

    def test_gplinks_helper_installs_gpt_lifecycle_probe(self):
        source = __import__('pathlib').Path('gplinks_live_browser.py').read_text()
        self.assertIn('install_gpt_lifecycle_probe', source)
        self.assertIn('collect_gpt_lifecycle_events', source)
        self.assertIn('impressionViewable', source)
        self.assertIn('rewardedSlotReady', source)
        self.assertIn('rewardedSlotGranted', source)
        self.assertIn('gpt_lifecycle', source)
        self.assertIn('gpt_resource_hints', source)
        self.assertIn('securepubads.g.doubleclick.net', source)

    def test_gplinks_live_helper_has_http_final_handoff(self):
        source = __import__('pathlib').Path('gplinks_live_browser.py').read_text()
        self.assertIn('try_http_final_gate_from_browser', source)
        self.assertIn('http-final-gate', source)
        self.assertIn('import_driver_cookies_to_session', source)

    def test_import_driver_cookies_to_session_filters_gplinks_cookies(self):
        driver = Mock()
        driver.get_cookies.return_value = [
            {'name': 'AppSession', 'value': 'sess', 'domain': '.gplinks.co', 'path': '/'},
            {'name': 'csrfToken', 'value': 'csrf', 'domain': 'gplinks.co', 'path': '/'},
            {'name': 'lid', 'value': 'YVTC', 'domain': 'powergam.online', 'path': '/'},
        ]
        session = Mock()
        session.cookies.set = Mock()

        imported = import_driver_cookies_to_session(driver, session, allowed_hosts={'gplinks.co'})

        self.assertEqual([item['name'] for item in imported], ['AppSession', 'csrfToken'])
        self.assertEqual(session.cookies.set.call_count, 2)

    def test_try_http_final_gate_from_browser_posts_with_imported_cookies(self):
        driver = Mock()
        driver.current_url = 'https://gplinks.co/YVTC?pid=1&vid=2'
        driver.page_source = '<form id="go-link" action="/links/go"><input name="_csrfToken" value="abc"></form>'
        driver.get_cookies.return_value = [{'name': 'AppSession', 'value': 'sess', 'domain': 'gplinks.co', 'path': '/'}]
        timeline = []
        fake_session = Mock()

        with patch('gplinks_live_browser.curl_requests.Session', return_value=fake_session), \
             patch('gplinks_live_browser.post_gplinks_final_gate_http', return_value={'status': 1, 'bypass_url': 'https://target.example/final'}):
            result = try_http_final_gate_from_browser(driver, 'http://127.0.0.1:5000', 60, timeline)

        self.assertEqual(result['status'], 1)
        self.assertEqual(result['bypass_url'], 'https://target.example/final')
        self.assertEqual(result['stage'], 'http-final-gate')
        self.assertEqual(timeline[0]['stage'], 'http-final-gate-start')
        self.assertEqual(timeline[-1]['stage'], 'http-final-gate-result')

    def test_gplinks_helper_installs_network_ledger_recorder(self):
        source = __import__('pathlib').Path('gplinks_live_browser.py').read_text()
        self.assertIn('install_network_ledger_recorder', source)
        self.assertIn('collect_network_ledger_events', source)
        self.assertIn('navigator.sendBeacon', source)
        self.assertIn('XMLHttpRequest.prototype.open', source)
        self.assertIn('window.fetch', source)
        self.assertIn('HTMLFormElement.prototype.submit', source)
        self.assertIn('network_ledger', source)
        self.assertIn('cookie_snapshot', source)

    def test_gplinks_promotes_live_helper_final_url(self):
        engine = ShortlinkBypassEngine()
        with patch.object(engine, '_resolve_gplinks_http_fast', return_value={'status': 0, 'stage': 'powergam-ledger', 'message': 'HTTP_FAST_POWERGAM_LEDGER_REJECTED'}) as http_fast, \
             patch.object(engine, '_resolve_gplinks_live', return_value={
            'status': 1,
            'stage': 'live-browser-final-gate',
            'bypass_url': 'http://tesskibidixxx.com/',
            'decoded_query': {'lid': 'YVTC', 'pid': '1224622', 'vid': 'MTAxOTM1MjU4Mg'},
            'sitekey': '0x4AAAAAAAynCEcs0RV-UleY',
            'token_used': True,
            'waited_seconds': 122.5,
        }):
            result = engine.analyze('https://gplinks.co/YVTC')

        http_fast.assert_called_once()
        self.assertEqual(result.family, 'gplinks.co')
        self.assertEqual(result.status, 1)
        self.assertEqual(result.message, 'GPLINKS_FINAL_OK')
        self.assertEqual(result.stage, 'live-browser')
        self.assertEqual(result.bypass_url, 'http://tesskibidixxx.com/')
        self.assertTrue(result.facts['token_used'])


if __name__ == '__main__':
    unittest.main()
