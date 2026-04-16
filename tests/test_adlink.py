import unittest
from unittest.mock import patch

from engine import ShortlinkBypassEngine


class AdlinkTests(unittest.TestCase):
    def _cf_response(self):
        return type('Resp', (), {
            'text': '<html><title>Just a moment...</title><body>cloudflare challenge</body></html>',
            'url': 'https://link.adlink.click/CBr27fn4of3',
            'status_code': 403,
            'headers': {'server': 'cloudflare', 'cf-ray': 'abc123'},
        })()

    def test_http_impersonation_success_beats_browser_fallback(self):
        engine = ShortlinkBypassEngine()

        with (
            patch.object(engine, '_get', return_value=self._cf_response()),
            patch.object(engine, '_resolve_adlink_http', return_value={
                'status': 1,
                'stage': 'blog-http-fast',
                'bypass_url': 'https://bitcointricks.com/shortlink.php?short_key=fu8dbowmwyx1q1f9et8qmao3o9r5wfu4',
            }) as mock_http,
            patch.object(engine, '_resolve_adlink_live') as mock_live,
        ):
            result = engine.analyze('https://link.adlink.click/CBr27fn4of3')

        self.assertEqual(result.status, 1)
        self.assertEqual(result.message, 'HTTP_IMPERSONATION_BYPASS_OK')
        self.assertEqual(result.stage, 'blog-http-fast')
        self.assertEqual(result.bypass_url, 'https://bitcointricks.com/shortlink.php?short_key=fu8dbowmwyx1q1f9et8qmao3o9r5wfu4')
        mock_http.assert_called_once()
        mock_live.assert_not_called()

    def test_browser_fallback_still_runs_if_http_impersonation_fails(self):
        engine = ShortlinkBypassEngine()

        with (
            patch.object(engine, '_get', return_value=self._cf_response()),
            patch.object(engine, '_resolve_adlink_http', return_value={
                'status': 0,
                'message': 'curl_cffi gagal',
            }) as mock_http,
            patch.object(engine, '_resolve_adlink_live', return_value={
                'status': 1,
                'stage': 'blog-form-submit',
                'bypass_url': 'https://bitcointricks.com/shortlink.php?short_key=fu8dbowmwyx1q1f9et8qmao3o9r5wfu4',
                'final_title': 'adlink',
                'cookie_names': ['cf_clearance'],
                'timeline': [],
                'maqal360_steps': [],
            }) as mock_live,
        ):
            result = engine.analyze('https://link.adlink.click/CBr27fn4of3')

        self.assertEqual(result.status, 1)
        self.assertEqual(result.message, 'LIVE_BROWSER_CHAIN_BYPASS_OK')
        self.assertEqual(result.stage, 'blog-form-submit')
        mock_http.assert_called_once()
        mock_live.assert_called_once()


if __name__ == '__main__':
    unittest.main()
