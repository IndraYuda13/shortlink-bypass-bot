import unittest
from unittest.mock import Mock, patch

from gplinks_http_fast import TurnstilePrewarmer, _post_final_gate, build_powergam_step_payloads, decoded_power_query, extract_final_gate, is_final_url, run


class GplinksHttpFastTests(unittest.TestCase):
    def test_decoded_power_query(self):
        url = 'https://powergam.online?lid=WVZUQw&pid=MTIyNDYyMg&vid=MTAxOTM2NTI2OQ&pages=Mw'
        self.assertEqual(decoded_power_query(url), {
            'lid': 'YVTC',
            'pid': '1224622',
            'vid': '1019365269',
            'pages': '3',
        })

    def test_final_url_oracle_rejects_internal_hosts(self):
        self.assertFalse(is_final_url('https://gplinks.co/YVTC?pid=1&vid=2'))
        self.assertFalse(is_final_url('https://powergam.online/'))
        self.assertFalse(is_final_url('chrome-error://chromewebdata/'))
        self.assertTrue(is_final_url('http://tesskibidixxx.com/'))

    def test_extract_final_gate_reads_form_payload_and_turnstile_sitekey(self):
        html = '''<form id="go-link" action="/links/go" method="post">
            <input type="hidden" name="_method" value="POST">
            <input type="hidden" name="_csrfToken" value="abc123">
            <div class="cf-turnstile" data-sitekey="0xSITE"></div>
        </form>'''
        gate = extract_final_gate(html, 'https://gplinks.co/YVTC?pid=1&vid=2')
        self.assertEqual(gate['action'], 'https://gplinks.co/links/go')
        self.assertEqual(gate['payload']['_csrfToken'], 'abc123')
        self.assertEqual(gate['sitekey'], '0xSITE')

    def test_build_powergam_step_payloads_uses_final_target_on_last_step(self):
        payloads = build_powergam_step_payloads(
            pages=3,
            visitor_id='1019365269',
            target_final='https://gplinks.co/YVTC?pid=1224622&vid=MTAxOTM2NTI2OQ',
            fallback_target='https://powergam.online',
            imps=5,
        )
        self.assertEqual([item['step_id'] for item in payloads], ['1', '2', '3'])
        self.assertEqual(payloads[0]['next_target'], 'https://powergam.online')
        self.assertEqual(payloads[2]['next_target'], 'https://gplinks.co/YVTC?pid=1224622&vid=MTAxOTM2NTI2OQ')
        self.assertEqual(payloads[2]['ad_impressions'], '5')

    def test_turnstile_prewarm_reuses_ready_matching_token(self):
        with patch('gplinks_http_fast.solve_turnstile', return_value='ready-token') as solver:
            prewarmer = TurnstilePrewarmer(
                solver_url='http://127.0.0.1:5000',
                page_url='https://gplinks.co/',
                sitekey='0xSITE',
                timeout=30,
                ttl_seconds=90,
            )
            prewarmer.start()
            token = prewarmer.token_for('0xSITE', wait_seconds=1)

        self.assertEqual(token, 'ready-token')
        solver.assert_called_once_with('http://127.0.0.1:5000', 'https://gplinks.co/', '0xSITE', 30)

    def test_turnstile_prewarm_rejects_different_sitekey(self):
        with patch('gplinks_http_fast.solve_turnstile', return_value='ready-token'):
            prewarmer = TurnstilePrewarmer(
                solver_url='http://127.0.0.1:5000',
                page_url='https://gplinks.co/',
                sitekey='0xSITE',
                timeout=30,
                ttl_seconds=90,
            )
            prewarmer.start()
            self.assertIsNone(prewarmer.token_for('0xOTHER', wait_seconds=1))

    def test_turnstile_prewarm_rejects_expired_token(self):
        with patch('gplinks_http_fast.solve_turnstile', return_value='ready-token'):
            prewarmer = TurnstilePrewarmer(
                solver_url='http://127.0.0.1:5000',
                page_url='https://gplinks.co/',
                sitekey='0xSITE',
                timeout=30,
                ttl_seconds=0,
            )
            prewarmer.start()
            self.assertIsNone(prewarmer.token_for('0xSITE', wait_seconds=1))

    def test_post_final_gate_uses_prewarmed_token_before_sync_solver(self):
        html = '''<form id="go-link" action="/links/go" method="post">
            <input type="hidden" name="_csrfToken" value="abc123">
            <div class="cf-turnstile" data-sitekey="0xSITE"></div>
        </form>'''
        response = Mock(status_code=200, url='https://gplinks.co/links/go', text='{"url":"https://target.example/final"}')
        response.json.return_value = {'url': 'https://target.example/final'}
        session = Mock()
        session.post.return_value = response
        with patch('gplinks_http_fast.solve_turnstile', return_value='ready-token') as solver:
            prewarmer = TurnstilePrewarmer('http://127.0.0.1:5000', 'https://gplinks.co/', '0xSITE', 30, ttl_seconds=90)
            prewarmer.start()
            timeline = []
            result = _post_final_gate(session, 'https://gplinks.co/YVTC', html, 'http://127.0.0.1:5000', 30, timeline, prewarmer=prewarmer)

        self.assertEqual(result['status'], 1)
        self.assertEqual(result['bypass_url'], 'https://target.example/final')
        self.assertIn(('cf-turnstile-response', 'ready-token'), session.post.call_args.kwargs['data'].items())
        self.assertEqual([event['source'] for event in timeline if event.get('stage') == 'turnstile-token'], ['prewarm'])
        solver.assert_called_once()

    def test_run_builds_candidate_from_entry_redirect(self):
        entry = Mock(status_code=302, headers={'location': 'https://powergam.online?lid=WVZUQw&pid=MTIyNDYyMg&vid=MTAxOTM2NTI2OQ&pages=Mw'}, text='', url='https://gplinks.co/YVTC')
        power = Mock(status_code=200, headers={}, text='<html><body>PowerGam</body></html>', url='https://powergam.online/')
        final = Mock(status_code=302, headers={'location': 'https://gplinks.co/link-error?alias=YVTC&error_code=not_enough_steps'}, text='', url='https://gplinks.co/link-error?alias=YVTC&error_code=not_enough_steps')
        session = Mock()
        session.get.side_effect = [entry, power, final]

        with patch('gplinks_http_fast.curl_requests.Session', return_value=session), patch('gplinks_http_fast.solve_turnstile', return_value='prewarmed-token'):
            result = run('https://gplinks.co/YVTC', timeout=30, solver_url='http://127.0.0.1:5000')

        self.assertEqual(result['status'], 0)
        self.assertEqual(result['stage'], 'powergam-ledger')
        self.assertEqual(result['decoded_query']['lid'], 'YVTC')
        self.assertEqual(result['target_final_candidate'], 'https://gplinks.co/YVTC?pid=1224622&vid=MTAxOTM2NTI2OQ')


if __name__ == '__main__':
    unittest.main()
