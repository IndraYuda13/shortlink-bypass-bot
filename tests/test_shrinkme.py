import unittest
from unittest.mock import patch

from engine import BypassResult, ShortlinkBypassEngine


class ShrinkmeTests(unittest.TestCase):
    def test_themezon_article_is_not_reported_as_final_bypass(self):
        engine = ShortlinkBypassEngine()

        html = '<html><head><title>ShrinkMe.io</title></head><body>https://themezon.net/link.php?link=ZTvkQYPJ</body></html>'

        with (
            patch.object(engine, '_get') as mock_get,
            patch.object(engine, '_resolve_shrinkme_themezon') as mock_themezon,
            patch.object(engine, '_resolve_shrinkme_mrproblogger') as mock_mrproblogger,
        ):
            mock_get.return_value = type('Resp', (), {
                'text': html,
                'url': 'https://shrinkme.click/ZTvkQYPJ',
                'status_code': 200,
                'headers': {},
            })()
            mock_themezon.return_value = {
                'status': 200,
                'article_url': 'https://themezon.net/managed-cloud-hosting-service-providers/',
            }
            mock_mrproblogger.return_value = {
                'message': 'still intermediate',
            }

            result = engine.analyze('https://shrinkme.click/ZTvkQYPJ')

        self.assertEqual(result.family, 'shrinkme.click')
        self.assertEqual(result.message, 'THEMEZON_ARTICLE_EXTRACTED')
        self.assertEqual(result.bypass_url, 'https://themezon.net/managed-cloud-hosting-service-providers/')
        self.assertEqual(result.status, 0)
        self.assertIn('intermediate', ' '.join(result.notes).lower())
        self.assertTrue(result.blockers)

    def test_shrinkme_final_claimcoin_is_reported_as_success(self):
        engine = ShortlinkBypassEngine()

        html = '<html><head><title>ShrinkMe.io</title></head><body>https://themezon.net/link.php?link=ZTvkQYPJ</body></html>'

        with (
            patch.object(engine, '_get') as mock_get,
            patch.object(engine, '_resolve_shrinkme_themezon') as mock_themezon,
            patch.object(engine, '_resolve_shrinkme_mrproblogger') as mock_mrproblogger,
        ):
            mock_get.return_value = type('Resp', (), {
                'text': html,
                'url': 'https://shrinkme.click/ZTvkQYPJ',
                'status_code': 200,
                'headers': {},
            })()
            mock_themezon.return_value = {
                'status': 200,
                'article_url': 'https://themezon.net/managed-cloud-hosting-service-providers/',
            }
            mock_mrproblogger.return_value = {
                'status': 1,
                'waited_seconds': 13,
                'bypass_url': 'https://claimcoin.in/links/back/kPw2COhFxD0pfQuGrXUz',
            }

            result = engine.analyze('https://shrinkme.click/ZTvkQYPJ')

        self.assertEqual(result.family, 'shrinkme.click')
        self.assertEqual(result.message, 'THEMEZON_MRPROBLOGGER_CHAIN_OK')
        self.assertEqual(result.bypass_url, 'https://claimcoin.in/links/back/kPw2COhFxD0pfQuGrXUz')
        self.assertEqual(result.status, 1)
        self.assertEqual(result.stage, 'themezon-mrproblogger')

    def test_bot_success_condition_is_reserved_for_final_bypass(self):
        intermediate = BypassResult(
            status=0,
            input_url='https://shrinkme.click/ZTvkQYPJ',
            family='shrinkme.click',
            message='THEMEZON_ARTICLE_EXTRACTED',
            bypass_url='https://themezon.net/managed-cloud-hosting-service-providers/',
        )
        self.assertFalse(intermediate.status == 1 and intermediate.bypass_url)


if __name__ == '__main__':
    unittest.main()
