import unittest

from core.segment_downloader import SegmentDownloader


class SegmentRangeTests(unittest.TestCase):
    def setUp(self):
        self.segments = [
            {'url': 'segment-1.m4s', 'duration': 4.0},
            {'url': 'segment-2.m4s', 'duration': 4.0},
            {'url': 'segment-3.m4s', 'duration': 4.0},
        ]

    def test_playlist_duration_uses_segment_durations(self):
        self.assertEqual(
            SegmentDownloader._playlist_duration(self.segments),
            12.0,
        )

    def test_selects_segments_overlapping_requested_range(self):
        selected = SegmentDownloader._select_media_segments(
            self.segments,
            start_time=3.0,
            end_time=8.0,
        )

        self.assertEqual(selected, ['segment-1.m4s', 'segment-2.m4s'])

    def test_rejects_start_beyond_hls_duration(self):
        with self.assertRaisesRegex(ValueError, '시작 시간'):
            SegmentDownloader._select_media_segments(
                self.segments,
                start_time=12.0,
                end_time=None,
            )

    def test_rejects_end_beyond_hls_duration(self):
        with self.assertRaisesRegex(ValueError, '종료 시간'):
            SegmentDownloader._select_media_segments(
                self.segments,
                start_time=0.0,
                end_time=13.0,
            )


if __name__ == '__main__':
    unittest.main()
