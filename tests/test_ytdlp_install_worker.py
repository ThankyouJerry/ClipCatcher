import unittest
from unittest.mock import patch

from core.dependency_check import ToolStatus
from ui.main_window import YtDlpInstallWorker, YtDlpStatusWorker


class YtDlpStatusWorkerTests(unittest.TestCase):
    def test_returns_available_and_missing_status_without_installing(self):
        for available in (True, False):
            status = ToolStatus('yt-dlp', '/tmp/yt-dlp', available, '2026.09.23')
            results = []
            worker = YtDlpStatusWorker()
            worker.completed.connect(results.append)
            with patch('ui.main_window.check_yt_dlp', return_value=status), patch(
                'ui.main_window.install_or_update_yt_dlp'
            ) as install:
                worker.run()
            self.assertEqual(results, [status])
            install.assert_not_called()

    def test_probe_exception_becomes_unavailable_status(self):
        results = []
        worker = YtDlpStatusWorker()
        worker.completed.connect(results.append)
        with patch('ui.main_window.check_yt_dlp', side_effect=RuntimeError('probe failed')):
            worker.run()
        self.assertFalse(results[0].available)
        self.assertEqual(results[0].error, 'probe failed')


class YtDlpInstallWorkerTests(unittest.TestCase):
    def test_emits_completed_path(self):
        completed = []
        failed = []
        worker = YtDlpInstallWorker()
        worker.completed.connect(completed.append)
        worker.failed.connect(failed.append)

        with patch(
            'ui.main_window.install_or_update_yt_dlp',
            return_value='/tmp/yt-dlp',
        ):
            worker.run()

        self.assertEqual(completed, ['/tmp/yt-dlp'])
        self.assertEqual(failed, [])

    def test_emits_failure_without_raising_on_worker_thread(self):
        completed = []
        failed = []
        worker = YtDlpInstallWorker()
        worker.completed.connect(completed.append)
        worker.failed.connect(failed.append)

        with patch(
            'ui.main_window.install_or_update_yt_dlp',
            side_effect=RuntimeError('network failure'),
        ):
            worker.run()

        self.assertEqual(completed, [])
        self.assertEqual(failed, ['network failure'])


if __name__ == '__main__':
    unittest.main()
