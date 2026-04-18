import base64
import json
import unittest
from unittest.mock import patch

from engine import ShortlinkBypassEngine


class XutAutodimeTests(unittest.TestCase):
    def _response(self, url, status_code=200, text='', headers=None):
        return type('Resp', (), {
            'text': text,
            'url': url,
            'status_code': status_code,
            'headers': headers or {},
        })()

    def _signed_cookie(self, data):
        head = base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip('=')
        return f'{head}.sig'

    def _step1_html(self):
        return """
        <html>
          <head><title>Step 1/6</title></head>
          <body>
            <form id="sl-form" action="#" method="post">
              <input type="hidden" name="_iconcaptcha-token" value="abc123" />
            </form>
            <script>
              window.SL_CFG = {
                step: 1,
                countdown: 10,
                captchaProvider: 'iconcaptcha',
                iconcaptchaEndpoint: '/cwsafelinkphp/sl-iconcaptcha-request.php',
                verifyUrl: '/cwsafelinkphp/sl-iconcaptcha-verify.php'
              };
            </script>
          </body>
        </html>
        """

    def test_xut_wrapper_maps_into_autodime_step1(self):
        engine = ShortlinkBypassEngine()
        engine.session.cookies.set('fexkomin', self._signed_cookie({'step': 1, 'sid': '/3lid'}))

        entry = self._response(
            'https://xut.io/3lid',
            status_code=302,
            headers={'location': 'https://autodime.com/cwsafelinkphp/go.php?link=snpurl%2F3lid'},
        )
        go = self._response(
            'https://autodime.com/cwsafelinkphp/go.php?link=snpurl%2F3lid',
            status_code=302,
            headers={'location': 'https://www.google.com/url?url=https%3A%2F%2Fautodime.com%2F'},
        )
        home = self._response('https://autodime.com/', text=self._step1_html())

        with patch.object(engine.session, 'get', side_effect=[entry, go, home]):
            result = engine.analyze('https://xut.io/3lid')

        self.assertEqual(result.family, 'autodime.cwsafelinkphp')
        self.assertEqual(result.message, 'ICONCAPTCHA_STEP1_MAPPED')
        self.assertEqual(result.stage, 'step1-iconcaptcha')
        self.assertEqual(result.status, 0)
        self.assertEqual(result.facts['entry_mode'], 'xut-wrapper')
        self.assertEqual(result.facts['google_target'], 'https://autodime.com/')
        self.assertEqual(result.facts['captchaProvider'], 'iconcaptcha')
        self.assertEqual(result.facts['countdown'], '10')
        self.assertTrue(result.facts['iconcaptcha_token_present'])
        self.assertEqual(result.facts['fexkomin_claims']['sid'], '/3lid')

    def test_direct_autodime_go_url_uses_same_family_handler(self):
        engine = ShortlinkBypassEngine()
        go = self._response(
            'https://autodime.com/cwsafelinkphp/go.php?link=snpurl%2F3lid',
            status_code=302,
            headers={'location': 'https://www.google.com/url?url=https%3A%2F%2Fautodime.com%2F'},
        )
        home = self._response('https://autodime.com/', text=self._step1_html())

        with patch.object(engine.session, 'get', side_effect=[go, home]):
            result = engine.analyze('https://autodime.com/cwsafelinkphp/go.php?link=snpurl%2F3lid')

        self.assertEqual(result.family, 'autodime.cwsafelinkphp')
        self.assertEqual(result.message, 'ICONCAPTCHA_STEP1_MAPPED')
        self.assertEqual(result.facts['entry_mode'], 'direct-go-url')
        self.assertEqual(result.facts['go_status'], 302)
        self.assertEqual(result.facts['title'], 'Step 1/6')


if __name__ == '__main__':
    unittest.main()
