"""Headless checks for batch input and truthful quality display."""
import asyncio
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6 import sip
from PyQt6.QtCore import QCoreApplication, QEvent, QObject, pyqtSignal
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QApplication, QMessageBox

from ui.main_window import MainWindow


class FakeConfig:
    def __init__(self, download_path):
        self.values = {"download_path": download_path, "concurrent_downloads": 1}

    def get(self, key, default=None):
        return self.values.get(key, default)

    def get_cookie_header(self):
        return ""

    def get_cookies_netscape(self):
        return ""


class FakeWorker(QObject):
    progress_updated = pyqtSignal(int, float, float)
    status_changed = pyqtSignal(str)
    download_completed = pyqtSignal(str)
    download_error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.started = False

    def start(self):
        self.started = True


class FakeDownloadManager:
    def __init__(self):
        self.workers = {}
        self.active_downloads = self.workers
        self._retired_downloads = {}

    def start_download(self, **_kwargs):
        download_id = str(len(self.workers) + 1)
        self.workers[download_id] = FakeWorker()
        return download_id

    def get_worker(self, download_id):
        return self.workers.get(download_id)

    def remove_download(self, download_id):
        self.workers.pop(download_id, None)


class MainWindowBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        with patch("ui.main_window.QTimer.singleShot"):
            self.window = MainWindow(FakeConfig(self.temp_dir.name))

    def tearDown(self):
        self.window.close()
        self.temp_dir.cleanup()

    def test_batch_input_keeps_order_and_removes_exact_duplicates(self):
        self.assertEqual(
            self.window._batch_urls(" a \n\nb\na\n c "),
            ["a", "b", "c"],
        )

    def test_status_check_menu_starts_only_one_worker(self):
        self.assertEqual(self.window.ytdlp_status_action.text(), "yt-dlp 상태 확인")
        with patch("ui.main_window.YtDlpStatusWorker") as worker_class:
            self.window.ytdlp_status_action.trigger()
            self.window._check_ytdlp_status()
            worker_class.assert_called_once_with(self.window)
            worker_class.return_value.start.assert_called_once()
            self.assertFalse(self.window.ytdlp_status_action.isEnabled())
        self.window._on_ytdlp_status_finished()
        self.assertTrue(self.window.ytdlp_status_action.isEnabled())

    def test_close_is_blocked_during_status_check(self):
        self.window.ytdlp_status_worker = object()
        event = QCloseEvent()
        with patch("ui.main_window.QMessageBox.information"):
            self.window.closeEvent(event)
        self.assertFalse(event.isAccepted())
        self.window.ytdlp_status_worker = None

    def test_input_modes_keep_each_field_and_hide_single_file_details(self):
        self.window.url_input.setText("https://chzzk.naver.com/video/100")
        self.window.batch_mode_radio.setChecked(True)
        self.window.batch_input.setPlainText("https://chzzk.naver.com/video/200\nhttps://chzzk.naver.com/video/300")
        self.assertTrue(self.window.single_input_widget.isHidden())
        self.assertFalse(self.window.batch_input_widget.isHidden())

        self.window._display_metadata({
            "id": "100", "title": "Test", "duration": 10,
            "is_downloadable": True,
            "resolutions": [{"label": "1080p", "url": "https://example.com/video"}],
        })
        self.assertTrue(self.window.info_group.isHidden())
        self.assertTrue(self.window.time_range_widget.isHidden())

        self.window.single_mode_radio.setChecked(True)
        self.assertFalse(self.window.single_input_widget.isHidden())
        self.assertTrue(self.window.batch_input_widget.isHidden())
        self.assertFalse(self.window.info_group.isHidden())
        self.assertEqual(self.window.url_input.text(), "https://chzzk.naver.com/video/100")
        self.assertEqual(self.window.batch_input.toPlainText().count("\n"), 1)

    def test_batch_cancel_stops_before_the_next_link(self):
        self.window._batch_cancel_requested = True
        with patch.object(self.window, "_load_metadata", new=AsyncMock()) as fetch:
            queued, failures = asyncio.run(self.window._enqueue_batch_urls([
                "https://chzzk.naver.com/video/100",
            ]))
        self.assertEqual((queued, failures), (0, []))
        fetch.assert_not_called()

    def test_batch_enqueues_valid_urls_in_order_without_changing_single_metadata(self):
        original = {"title": "Already selected"}
        self.window.current_metadata = original
        urls = [
            "https://chzzk.naver.com/video/100",
            "https://invalid.example/video/1",
            "https://chzzk.naver.com/video/200",
        ]
        def metadata(url, *_args):
            return {
                "id": url.rsplit("/", 1)[-1],
                "type": "vod",
                "title": url,
                "resolutions": [{"label": "best", "url": url}],
            }

        with patch.object(self.window, "_load_metadata", new=AsyncMock(side_effect=metadata)), patch.object(
            self.window, "_queue_metadata_download"
        ) as enqueue:
            queued, failures = asyncio.run(self.window._enqueue_batch_urls(urls))

        self.assertEqual(queued, 2)
        self.assertEqual(len(failures), 1)
        self.assertEqual(
            [call.args[0]["id"] for call in enqueue.call_args_list],
            ["100", "200"],
        )
        self.assertIs(self.window.current_metadata, original)

    def test_best_with_unknown_bitrate_never_displays_zero_kbps(self):
        self.window._display_metadata({
            "id": "100",
            "type": "vod",
            "title": "Test",
            "duration": 10,
            "is_downloadable": True,
            "resolutions": [{"label": "best", "url": "https://example.com", "bitrate": 0}],
        })
        self.assertEqual(self.window.quality_combo.itemText(0), "best")

    def test_batch_uses_page_url_and_first_quality_without_single_selection(self):
        metadata = {
            "id": "100", "type": "vod", "vod_status": "ABR_HLS",
            "title": "Test", "url": "https://chzzk.naver.com/video/100",
            "thumbnail": "https://example.com/100.jpg",
        }
        selected = {"label": "1080p", "url": "https://example.com/playlist", "height": 1080}
        with patch.object(self.window, "_initiate_download") as start:
            self.window._queue_metadata_download(metadata, selected)
        self.assertEqual(start.call_args.args[:4], (
            "100", "https://chzzk.naver.com/video/100", "Test", "1080p",
        ))
        self.assertEqual(start.call_args.kwargs["thumbnail_url"], metadata["thumbnail"])

    def test_installed_ytdlp_does_not_prompt_even_without_app_owned_copy(self):
        with patch("ui.main_window.check_yt_dlp", return_value=SimpleNamespace(available=True)), patch(
            "ui.main_window.QMessageBox.question"
        ) as question:
            self.window._show_ytdlp_install_prompt_if_needed()
        question.assert_not_called()

    def test_two_batch_items_run_sequentially_and_first_moves_to_completed_tab(self):
        manager = FakeDownloadManager()
        self.window.download_manager = manager
        for video_id in ("100", "200"):
            metadata = {
                "id": video_id, "type": "vod", "vod_status": "ABR_HLS",
                "title": f"Video {video_id}",
                "url": f"https://chzzk.naver.com/video/{video_id}",
            }
            self.window._queue_metadata_download(
                metadata, {"label": "1080p", "url": metadata["url"], "height": 1080}
            )

        self.assertTrue(manager.workers["1"].started)
        self.assertFalse(manager.workers["2"].started)
        self.assertEqual(self.window.pending_download_ids, ["2"])

        manager.workers["1"].download_completed.emit("/tmp/video-100.mp4")
        self.app.processEvents()
        self.assertTrue(manager.workers["2"].started)
        self.assertEqual(self.window.completed_list.count(), 1)
        self.assertEqual(self.window.active_list.count(), 1)
        manager.workers["2"].download_completed.emit("/tmp/video-200.mp4")
        self.app.processEvents()
        self.assertEqual(self.window.completed_list.count(), 2)
        self.assertEqual(self.window.active_list.count(), 0)

    def test_declining_close_preserves_an_active_download(self):
        self.window.running_download_ids.add("still-running")
        event = QCloseEvent()
        with patch(
            "ui.main_window.QMessageBox.question",
            return_value=QMessageBox.StandardButton.No,
        ):
            self.window.closeEvent(event)
        self.assertFalse(event.isAccepted())
        self.assertIn("still-running", self.window.running_download_ids)
        self.window.running_download_ids.clear()

    def test_repeated_completion_and_tab_switching_survives_deferred_deletion(self):
        manager = FakeDownloadManager()
        self.window.download_manager = manager
        self.window.show()
        for index in range(40):
            url = f"https://chzzk.naver.com/video/{index + 100}"
            self.window._queue_metadata_download(
                {"id": str(index), "type": "vod", "vod_status": "ABR_HLS",
                 "title": f"Video {index}", "url": url},
                {"label": "1080p", "url": url, "height": 1080},
            )
        for index in range(40):
            task = str(index + 1)
            self.assertTrue(manager.workers[task].started)
            manager.workers[task].download_completed.emit(f"/tmp/{task}.mp4")
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            for list_widget in (self.window.completed_list, self.window.active_list):
                self.window.download_tabs.setCurrentWidget(list_widget)
                list_widget.doItemsLayout()
                self.app.processEvents()
            for row in range(self.window.completed_list.count()):
                widget = self.window.completed_list.itemWidget(self.window.completed_list.item(row))
                self.assertIsNotNone(widget)
                self.assertFalse(sip.isdeleted(widget))
        self.assertEqual(self.window.completed_list.count(), 40)
        self.assertFalse(self.window.running_download_ids)


if __name__ == "__main__":
    unittest.main()
