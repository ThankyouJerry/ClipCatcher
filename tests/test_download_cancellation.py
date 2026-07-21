import subprocess
import sys
import time
import unittest

from core.downloader import DownloadWorker


class DownloadCancellationTests(unittest.TestCase):
    def test_stop_returns_immediately_and_terminates_process(self):
        worker = DownloadWorker("https://example.com", "/tmp/clipcatcher-test")
        process = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        worker.process = process

        started = time.monotonic()
        worker.stop()
        elapsed = time.monotonic() - started

        self.assertLess(elapsed, 0.25)
        process.wait(timeout=4)
        self.assertIsNotNone(process.returncode)


if __name__ == "__main__":
    unittest.main()
