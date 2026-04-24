import unittest
from unittest.mock import Mock, patch

from engine import ShortlinkBypassEngine


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

        with patch.object(engine, '_new_impersonated_session', return_value=fake_session):
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


if __name__ == '__main__':
    unittest.main()
