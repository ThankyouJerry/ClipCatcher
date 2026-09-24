import json
import subprocess
import unittest
from unittest.mock import patch

from core.youtube_api import YouTubeAPI


class YouTubeApiTests(unittest.TestCase):
    def test_metadata_command_is_single_video_bounded_and_config_independent(self):
        info = {
            "id": "dQw4w9WgXcQ",
            "title": "테스트 영상",
            "webpage_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "formats": [],
        }
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(info),
            stderr="",
        )

        with patch(
            "core.youtube_api.resolve_yt_dlp_binary",
            return_value="/tmp/yt-dlp",
        ), patch("core.youtube_api.subprocess.run", return_value=completed) as run:
            metadata = YouTubeAPI().fetch_metadata(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PL123"
            )

        command = run.call_args.args[0]
        self.assertIn("--ignore-config", command)
        self.assertIn("--dump-single-json", command)
        self.assertIn("--no-playlist", command)
        self.assertEqual(
            run.call_args.kwargs["timeout"],
            YouTubeAPI.METADATA_TIMEOUT_SECONDS,
        )
        self.assertEqual(metadata["id"], "dQw4w9WgXcQ")
        self.assertEqual(metadata["resolutions"][0]["quality"], "best")
        self.assertEqual(metadata["resolutions"][0]["label"],
                         "자동 선택 (다운로드 시 화질 결정)")
        self.assertNotIn("bitrate", metadata["resolutions"][0])

    def test_resolution_bitrate_is_only_present_when_positive_and_numeric(self):
        resolutions = YouTubeAPI._extract_resolutions({
            "webpage_url": "https://www.youtube.com/watch?v=abc",
            "formats": [
                {"vcodec": "avc1", "ext": "mp4", "height": 1080,
                 "tbr": 2500.5},
                {"vcodec": "vp9", "ext": "webm", "height": 1080,
                 "tbr": None},
                {"vcodec": "avc1", "ext": "mp4", "height": 720,
                 "tbr": 0},
                {"vcodec": "avc1", "ext": "mp4", "height": 480,
                 "tbr": "unknown"},
            ],
        })

        self.assertEqual([r["quality"] for r in resolutions],
                         ["1080p", "720p", "480p"])
        self.assertEqual(resolutions[0]["bitrate"], 2_500_500)
        self.assertNotIn("bitrate", resolutions[1])
        self.assertNotIn("bitrate", resolutions[2])

    def test_nonstandard_aspect_ratio_keeps_downloadable_resolutions(self):
        resolutions = YouTubeAPI._extract_resolutions({
            "webpage_url": "https://www.youtube.com/watch?v=YkjWgmxYGGo",
            "formats": [
                {"vcodec": "av01.0.12M.08", "ext": "mp4",
                 "width": 2560, "height": 1280, "tbr": 2059},
                {"vcodec": "vp9", "ext": "webm",
                 "width": 1920, "height": 960, "tbr": 5694},
                {"vcodec": "avc1.64002a", "ext": "mp4",
                 "width": 1920, "height": 960, "tbr": 1768},
                {"vcodec": "avc1.640020", "ext": "mp4",
                 "width": 1280, "height": 640, "tbr": 1041},
            ],
        })
        self.assertEqual([r["height"] for r in resolutions], [960, 640])
        self.assertEqual(resolutions[0]["label"], "960p (1920×960)")
        self.assertEqual(resolutions[0]["bitrate"], 1_768_000)

    def test_portrait_and_nonstandard_heights_do_not_fall_back_to_best(self):
        resolutions = YouTubeAPI._extract_resolutions({
            "formats": [{"vcodec": "avc1", "ext": "mp4",
                         "width": 1080, "height": 1920}],
        })
        self.assertEqual(resolutions[0]["label"], "1920p (1080×1920)")

    def test_incompatible_formats_report_actionable_error(self):
        with self.assertRaisesRegex(RuntimeError, "H.264"):
            YouTubeAPI._extract_resolutions({
                "formats": [{"vcodec": "vp9", "ext": "webm", "height": 1080}],
            })

    def test_metadata_timeout_has_user_facing_error(self):
        with patch(
            "core.youtube_api.resolve_yt_dlp_binary",
            return_value="/tmp/yt-dlp",
        ), patch(
            "core.youtube_api.subprocess.run",
            side_effect=subprocess.TimeoutExpired("yt-dlp", 90),
        ):
            with self.assertRaisesRegex(RuntimeError, "시간이 초과"):
                YouTubeAPI().fetch_metadata(
                    "https://youtu.be/dQw4w9WgXcQ"
                )


if __name__ == "__main__":
    unittest.main()
