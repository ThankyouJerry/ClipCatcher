import tempfile
import unittest
from pathlib import Path

from core.downloader import DownloadManager


class DownloadPathTests(unittest.TestCase):
    def test_same_title_and_repeated_requests_have_distinct_paths(self):
        manager = DownloadManager()
        with tempfile.TemporaryDirectory() as folder:
            paths = []
            for video_id in ("first", "second", "first"):
                task = manager.start_download(
                    video_id, "https://example.com/video", "Same title",
                    "1080p", Path(folder),
                )
                paths.append(manager.get_worker(task).output_path)
            self.assertEqual(len(set(paths)), 3)

    def test_korean_title_and_quality_fit_filename_limit(self):
        manager = DownloadManager()
        with tempfile.TemporaryDirectory() as folder:
            task = manager.start_download(
                "YkjWgmxYGGo", "https://example.com/video", "긴 영상 제목 " * 100,
                "960p (1920×960)/test", Path(folder),
            )
            path = Path(manager.get_worker(task).output_path)
            self.assertEqual(path.parent, Path(folder))
            self.assertIn("YkjWgmxYGGo", path.name)
            self.assertLessEqual(len((path.name + ".f12345.mp4.part").encode('utf-8')), 255)
            self.assertNotIn("/", path.name)


if __name__ == "__main__":
    unittest.main()
