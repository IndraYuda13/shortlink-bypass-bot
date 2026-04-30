import unittest
from unittest.mock import patch

from engine import ShortlinkBypassEngine
from supported_sites import SUPPORTED_SITES


class ShortanoShortinoTests(unittest.TestCase):
    def test_shortano_cloudflare_block_is_classified_as_partial_not_unknown(self):
        engine = ShortlinkBypassEngine()
        html = '<html><head><title>Just a moment...</title></head><body>Cloudflare</body></html>'
        with patch.object(engine, '_get') as mock_get:
            mock_get.return_value = type('Resp', (), {
                'text': html,
                'url': 'https://shortano.link/sOxx',
                'status_code': 403,
                'headers': {'server': 'cloudflare'},
            })()
            result = engine.analyze('https://shortano.link/sOxx')
        self.assertEqual(result.family, 'shortano.link')
        self.assertEqual(result.message, 'CLOUDFLARE_BLOCKED')
        self.assertEqual(result.status, 0)
        self.assertEqual(result.stage, 'entry-cloudflare')
        self.assertIn('cloudflare', ' '.join(result.blockers).lower())

    def test_shortino_uses_same_handler_family(self):
        engine = ShortlinkBypassEngine()
        html = '<html><head><title>Just a moment...</title></head><body>Cloudflare</body></html>'
        with patch.object(engine, '_get') as mock_get:
            mock_get.return_value = type('Resp', (), {
                'text': html,
                'url': 'https://shortino.link/abc',
                'status_code': 403,
                'headers': {'server': 'cloudflare'},
            })()
            result = engine.analyze('https://shortino.link/abc')
        self.assertEqual(result.family, 'shortino.link')
        self.assertEqual(result.message, 'CLOUDFLARE_BLOCKED')

    def test_supported_site_registry_has_shortano_and_shortino_partial_entries(self):
        sites = {site.host: site for site in SUPPORTED_SITES}
        shortano = sites.get('shortano.link')
        shortino = sites.get('shortino.link')
        self.assertIsNotNone(shortano)
        self.assertIsNotNone(shortino)
        self.assertEqual(shortano.status, 'partial')
        self.assertEqual(shortino.status, 'partial')
        self.assertEqual(shortano.handler, '_handle_shortano_family')
        self.assertEqual(shortino.handler, '_handle_shortano_family')


if __name__ == '__main__':
    unittest.main()
