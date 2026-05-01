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

    def test_tpi_token_landing_prefers_bitcotasks_result_from_noisy_token(self):
        engine = ShortlinkBypassEngine()
        expected = 'https://bitcotasks.com//shortlink/result/a4sbiirc1jcip4r9yncggus5nw8u1xwz-.-.-620efc44d2206adb53c603a787ee9770f78400d74b14a49bc0c1980fefd77678/843/194'
        html = f'''
        <html><head><title>ShrinkEarn</title></head><body>
        <form action="https://vpzserver.com/what-is-disk-space-and-bandwidth-limits-in-web-hosting/" method="POST">
          <input type="hidden" name="url" value="https://fithelptipz.com/OWgbl0wy35w">
          <input type="hidden" name="token" value="8eb07d3b4deeb0bd34a191d8dfdf2de19be452ce2026OWgbl0wy35w2804aHR0cHM6Ly9iaXRjb3Rhc2tzLmNvbS8vc2hvcnRsaW5rL3Jlc3VsdC9hNHNiaWlyYzFqY2lwNHI5eW5jZ2d1czVudzh1MXh3ei0uLS4tNjIwZWZjNDRkMjIwNmFkYjUzYzYwM2E3ODdlZTk3NzBmNzg0MDBkNzRiMTRhNDliYzBjMTk4MGZlZmQ3NzY3OC84NDMvMTk0shrinkbixby.com">
          <input type="hidden" name="mysite" value="shrinkbixby.com">
          <input type="hidden" name="alias" value="OWgbl0wy35w">
          <a href="https://shrinkearn.com/">home</a>
        </form>
        </body></html>
        '''
        with patch.object(engine, '_get') as mock_get:
            mock_get.return_value = type('Resp', (), {
                'text': html,
                'url': 'https://tpi.li/OWgbl0wy35w',
                'status_code': 200,
                'headers': {},
            })()

            result = engine.analyze('https://tpi.li/OWgbl0wy35w')

        self.assertEqual(result.family, 'tpi.li')
        self.assertEqual(result.status, 1)
        self.assertEqual(result.message, 'TOKEN_TARGET_EXTRACTED')
        self.assertEqual(result.stage, 'token-target')
        self.assertEqual(result.bypass_url, expected)

    def test_tpi_token_landing_prefers_cutw_st_target_from_noisy_token(self):
        engine = ShortlinkBypassEngine()
        expected = 'https://cutw.in/st?api=dea80667e642a633b7048c643f0e80e062d729ea&url=https://dlgamingvn.com/an-denique-dissentiet-suscipiantur-eos-41?fbclid2=X%2BTJgwmYuvPVS1jCpXnHupCKQMd3aXHyiIAzgpJxge8WDh7ppiMtOOURXT88fkhUdpr60zC5qWdh9O6kbX9H3aG67qddAT2U287QQdeyVbevtW9SJ5oiUhPhAw%2BVXLb5svdNVelqqrwo1qsR03lcXzo6yNgbW9uUeXHT4LS55Cvhqjo6FiFLAc7rSlHM64LoerPR8uFTvEwTAMYPbwkraw9gV3Q%3D'
        html = f'''
        <html><head><title>ShrinkEarn</title></head><body>
        <form action="https://vpzserver.com/how-to-choose-a-web-hosting-plan-for-high-traffic-websites/" method="POST">
          <input type="hidden" name="url" value="https://fithelptipz.com/xP8OTKz">
          <input type="hidden" name="token" value="cb62eca841cd318d99b6da204c056fffdcf0e29d2026xP8OTKz0105aHR0cHM6Ly9jdXR3LmluL3N0P2FwaT1kZWE4MDY2N2U2NDJhNjMzYjcwNDhjNjQzZjBlODBlMDYyZDcyOWVhJnVybD1odHRwczovL2RsZ2FtaW5ndm4uY29tL2FuLWRlbmlxdWUtZGlzc2VudGlldC1zdXNjaXBpYW50dXItZW9zLTQxP2ZiY2xpZDI9WCUyQlRKZ3dtWXV2UFZTMWpDcFhuSHVwQ0tRTWQzYVhIeWlJQXpncEp4Z2U4V0RoN3BwaU10T09VUlhUODhma2hVZHByNjB6QzVxV2RoOU82a2JYOUgzYUc2N3FkZEFUMlUyODdRUWRleVZiZXZ0VzlTSjVvaVVoUGhBdyUyQlZYTGI1c3ZkTlZlbHFxcndvMXFzUjAzbGNYem82eU5nYlc5dVVlWEhUNExTNTVDdmhxam82RmlGTEFjN3JTbEhNNjRMb2VyUFI4dUZUdkV3VEFNWVBid2tyYXc5Z1YzUSUzRA==shrinkbixby.com">
          <input type="hidden" name="mysite" value="shrinkbixby.com">
          <input type="hidden" name="alias" value="xP8OTKz">
          <a href="https://shrinkearn.com/">home</a>
        </form>
        </body></html>
        '''
        with patch.object(engine, '_get') as mock_get:
            mock_get.return_value = type('Resp', (), {
                'text': html,
                'url': 'https://tpi.li/xP8OTKz',
                'status_code': 200,
                'headers': {},
            })()

            result = engine.analyze('https://tpi.li/xP8OTKz')

        self.assertEqual(result.family, 'tpi.li')
        self.assertEqual(result.status, 1)
        self.assertEqual(result.message, 'TOKEN_TARGET_EXTRACTED')
        self.assertEqual(result.stage, 'token-target')
        self.assertEqual(result.bypass_url, expected)

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
