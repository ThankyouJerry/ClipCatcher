import gc
import os
import threading
import time
import unittest
import weakref
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from core.downloader import DownloadManager, DownloadWorker
from ui.download_item import DownloadItemWidget, ThumbnailLoader


class ThreadLifetimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def process_until(self, predicate, timeout=2):
        deadline = time.monotonic() + timeout
        while not predicate() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(0.01)
        self.assertTrue(predicate())

    def test_completed_worker_is_retained_until_thread_exits(self):
        started = threading.Event()
        release = threading.Event()

        def slow_run(worker):
            started.set()
            worker.download_completed.emit("/tmp/example.mp4")
            release.wait(3)

        manager = DownloadManager()
        with patch.object(DownloadWorker, "run", slow_run):
            download_id = manager.start_download(
                "video", "https://example.com", "example", "1080p", Path("/tmp")
            )
            worker = manager.get_worker(download_id)
            worker.download_completed.connect(
                lambda _: manager.remove_download(download_id)
            )
            worker_ref = weakref.ref(worker)
            worker.start()
            try:
                self.assertTrue(started.wait(2))
                self.process_until(lambda: download_id in manager._retired_downloads)
                del worker
                gc.collect()
                self.assertIsNotNone(worker_ref())
                self.assertTrue(worker_ref().isRunning())
            finally:
                release.set()
                if worker_ref() is not None:
                    worker_ref().wait(2000)
            self.process_until(lambda: download_id not in manager._retired_downloads)

    def test_cancelled_worker_is_retained_until_thread_exits(self):
        started = threading.Event()
        release = threading.Event()

        def slow_run(_worker):
            started.set()
            release.wait(3)

        manager = DownloadManager()
        with patch.object(DownloadWorker, "run", slow_run):
            download_id = manager.start_download(
                "video", "https://example.com", "example", "1080p", Path("/tmp")
            )
            worker = manager.get_worker(download_id)
            worker_ref = weakref.ref(worker)
            worker.start()
            try:
                self.assertTrue(started.wait(2))
                manager.cancel_download(download_id)
                del worker
                gc.collect()
                self.assertIsNone(manager.get_worker(download_id))
                self.assertIsNotNone(worker_ref())
                self.assertTrue(worker_ref().isRunning())
            finally:
                release.set()
                if worker_ref() is not None:
                    worker_ref().wait(2000)
            self.process_until(lambda: download_id not in manager._retired_downloads)

    def test_thumbnail_loader_outlives_deleted_widget(self):
        started = threading.Event()
        release = threading.Event()

        def slow_run(_loader):
            started.set()
            release.wait(3)

        with patch.object(ThumbnailLoader, "run", slow_run):
            widget = DownloadItemWidget("id", "title", "https://example.com/image.jpg")
            loader = widget.thumbnail_loader
            loader_ref = weakref.ref(loader)
            try:
                self.assertTrue(started.wait(2))
                widget.deleteLater()
                del widget, loader
                gc.collect()
                self.assertIsNotNone(loader_ref())
                self.assertIn(loader_ref(), ThumbnailLoader._running_loaders)
            finally:
                release.set()
                if loader_ref() is not None:
                    loader_ref().wait(2000)
            self.process_until(
                lambda: loader_ref() not in ThumbnailLoader._running_loaders
            )


if __name__ == "__main__":
    unittest.main()
