import unittest
from unittest.mock import patch

from engine import ShortlinkBypassEngine


class TokenLandingTests(unittest.TestCase):
    def test_tpi_token_landing_extracts_links_back_oracle(self):
        engine = ShortlinkBypassEngine()
        html = '''
        <html><head><title>Health Shield</title></head><body>
        <form action="https://advertisingcamps.com/taboola1/landing/" method="POST">
          <input type="hidden" name="url" value="https://fithelptipz.com/Dd5xka">
          <input type="hidden" name="token" value="cead005de3f8b218340b624bc6d04482f1d785a52026Dd5xka2404aHR0cHM6Ly85OWZhdWNldC5jb20vbGlua3MvYmFjay9oYUJLallydWdSeERJVkNwR3FNbw==">
          <input type="hidden" name="mysite" value="shrinkearn.com">
          <input type="hidden" name="alias" value="Dd5xka">
        </form>
        </body></html>
        '''
        with patch.object(engine, '_get') as mock_get:
            mock_get.return_value = type('Resp', (), {
                'text': html,
                'url': 'https://tpi.li/Dd5xka',
                'status_code': 200,
                'headers': {},
            })()

            result = engine.analyze('https://tpi.li/Dd5xka')

        self.assertEqual(result.family, 'tpi.li')
        self.assertEqual(result.status, 1)
        self.assertEqual(result.message, 'TOKEN_TARGET_EXTRACTED')
        self.assertEqual(result.stage, 'token-target')
        self.assertEqual(result.bypass_url, 'https://99faucet.com/links/back/haBKjYrugRxDIVCpGqMo')

    def test_aii_token_landing_extracts_base64_url_with_suffix_noise(self):
        engine = ShortlinkBypassEngine()
        html = '''
        <html><head><title>ShrinkBixby</title></head><body>
        <form action="https://techbixby.com/article/" method="POST">
          <input type="hidden" name="token" value="4b1ab5b6e45b836656e80083f5f41c65795fb14b2026CBygg8fn2s32404aHR0cHM6Ly9jb2luYWRzdGVyLmNvbS9zaG9ydGxpbmsucGhwP3Nob3J0X2tleT0xY25kOWhxMG5mYmVtNWRyOHZybWF6MTdmNDRwdmg5YQ==shrinkbixby.c">
          <input type="hidden" name="mysite" value="shrinkbixby.com">
          <input type="hidden" name="alias" value="CBygg8fn2s3">
        </form>
        </body></html>
        '''
        with patch.object(engine, '_get') as mock_get:
            mock_get.return_value = type('Resp', (), {
                'text': html,
                'url': 'https://aii.sh/CBygg8fn2s3',
                'status_code': 200,
                'headers': {},
            })()

            result = engine.analyze('https://aii.sh/CBygg8fn2s3')

        self.assertEqual(result.family, 'aii.sh')
        self.assertEqual(result.status, 1)
        self.assertEqual(result.message, 'TOKEN_TARGET_EXTRACTED')
        self.assertEqual(
            result.bypass_url,
            'https://coinadster.com/shortlink.php?short_key=1cnd9hq0nfbem5dr8vrmaz17f44pvh9a',
        )


if __name__ == '__main__':
    unittest.main()
