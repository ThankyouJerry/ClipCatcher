import json
import unittest

from core.chzzk_api import ChzzkAPI


class ChzzkPlaylistUrlTests(unittest.TestCase):
    def test_preserves_signed_query_when_building_variant_url(self):
        metadata = {
            'liveRewindPlaybackJson': json.dumps({
                'media': [{
                    'path': (
                        'https://example.com/live/vod_playlist.m3u8'
                        '?hdnts=st%3D1~exp%3D2~hmac%3Dabc'
                    )
                }]
            })
        }

        self.assertEqual(
            ChzzkAPI.get_m3u8_url(metadata, '1080p'),
            (
                'https://example.com/live/1080p/vod_chunklist.m3u8'
                '?hdnts=st%3D1~exp%3D2~hmac%3Dabc'
            ),
        )


if __name__ == '__main__':
    unittest.main()
