"""Offline regression coverage for the shared headless download engine."""
import os
import signal
from unittest.mock import MagicMock, patch

import pytest

from core.download_job import DownloadJob


def test_binary_escapes_literal_percent_and_reports_after_move_path():
    job = DownloadJob("https://example.com/video", "/tmp/100% %(title)s")
    completed = []
    job.download_completed.connect(completed.append)
    process = MagicMock()
    process.stdout = iter([
        '[download] Destination: /tmp/intermediate.webm\n',
        'CLIPCATCHER_OUTPUT:/tmp/100% %(title)s.mp4\n',
    ])
    process.returncode = 0
    with patch("core.download_job.resolve_yt_dlp_binary", return_value="/tools/yt-dlp"), \
         patch("core.download_job.get_ffmpeg_binary", return_value="/tools/ffmpeg"), \
         patch("core.download_job.subprocess.Popen", return_value=process) as spawn:
        job._run_ytdlp_binary_download()
    command = spawn.call_args.args[0]
    assert command[command.index("-o") + 1] == "/tmp/100%% %%(title)s.%(ext)s"
    assert completed == ["/tmp/100% %(title)s.mp4"]


def test_package_reports_postprocessed_filename_and_escapes_template():
    job = DownloadJob("https://example.com/video", "/tmp/100% %(title)s")
    completed = []
    job.download_completed.connect(completed.append)
    options = {}

    def create_ydl(opts):
        options.update(opts)
        ydl = MagicMock()
        ydl.__enter__.return_value = ydl

        def extract(*args, **kwargs):
            for callback in opts["postprocessor_hooks"]:
                callback({"status": "finished", "info_dict": {"filepath": "/tmp/final.mp4"}})
            return {"id": "video", "ext": "webm"}

        ydl.extract_info.side_effect = extract
        ydl.prepare_filename.return_value = "/tmp/before-conversion.webm"
        return ydl

    with patch("core.download_job.yt_dlp.YoutubeDL", side_effect=create_ydl), \
         patch("core.download_job.get_ffmpeg_binary", return_value="/tools/ffmpeg"):
        job._run_ytdlp_package_download()
    assert options["outtmpl"] == "/tmp/100%% %%(title)s.%(ext)s"
    assert completed == ["/tmp/final.mp4"]


@pytest.mark.skipif(os.name == "nt", reason="POSIX process-group cancellation")
def test_cancel_force_kills_captured_group_after_leader_exits():
    job = DownloadJob("https://example.com/video", "/tmp/unused")
    process = MagicMock()
    process.pid = 24680
    process.poll.return_value = None
    job.process = process
    with patch("core.download_job.os.getpgid", return_value=process.pid), \
         patch("core.download_job.os.killpg") as kill_group, \
         patch("core.download_job.threading.Thread") as thread, \
         patch("core.download_job.threading.Event"):
        job.stop()
        kill_group.assert_called_once_with(process.pid, signal.SIGTERM)
        process.poll.return_value = -signal.SIGTERM
        thread.call_args.kwargs["target"]()
        assert kill_group.call_args.args == (process.pid, signal.SIGKILL)
        assert thread.call_args.kwargs["daemon"] is False
        process.wait.assert_called_once_with(timeout=3)


def test_windows_cancel_defers_force_tree_kill_to_cleanup_thread():
    from types import SimpleNamespace
    job = DownloadJob("https://example.com/video", "unused")
    process = MagicMock()
    process.pid = 24680
    process.poll.return_value = None
    job.process = process
    with patch("core.download_job.os", SimpleNamespace(name="nt")), \
         patch("core.download_job.threading.Thread") as thread, \
         patch("core.download_job.subprocess.run") as run:
        job.stop()
        assert job.should_stop
        run.assert_not_called()
        assert thread.call_args.kwargs["daemon"] is False
        thread.return_value.start.assert_called_once()
        thread.call_args.kwargs["target"]()
        assert run.call_args.args[0] == ["taskkill", "/PID", "24680", "/T", "/F"]
        assert run.call_args.kwargs["timeout"] > 0
        process.wait.assert_called_once_with(timeout=3)


def test_windows_cancel_falls_back_if_taskkill_unavailable():
    from types import SimpleNamespace
    job = DownloadJob("https://example.com/video", "unused")
    process = MagicMock()
    process.poll.return_value = None
    job.process = process
    with patch("core.download_job.os", SimpleNamespace(name="nt")), \
         patch("core.download_job.threading.Thread") as thread, \
         patch("core.download_job.subprocess.run", side_effect=FileNotFoundError("taskkill unavailable")):
        job.stop()
        thread.call_args.kwargs["target"]()
    process.kill.assert_called_once()


def test_repeated_stop_schedules_only_one_cleanup():
    from types import SimpleNamespace
    job = DownloadJob("https://example.com/video", "unused")
    process = MagicMock()
    process.poll.return_value = None
    job.process = process
    with patch("core.download_job.os", SimpleNamespace(name="nt")), \
         patch("core.download_job.threading.Thread") as thread:
        job.stop()
        job.stop()
    thread.assert_called_once()


def test_cancel_before_spawn_still_cleans_up_new_process():
    job = DownloadJob("https://example.com/video", "unused")
    job.stop()
    process = MagicMock()
    process.poll.return_value = None
    with patch("core.download_job.subprocess.Popen", return_value=process), \
         patch("core.download_job.get_ffmpeg_binary", return_value="ffmpeg"), \
         patch.object(job, "stop") as stop:
        job._run_ytdlp_binary_download(["mock-yt-dlp"])
    stop.assert_called_once()
    assert job.process is process
    process.stdout.__iter__.assert_not_called()


def test_unexpected_worker_failure_requests_cleanup_before_clearing_process():
    job = DownloadJob("https://example.com/video", "unused")
    process = MagicMock()
    process.poll.return_value = None
    errors = []
    job.download_error.connect(errors.append)

    def fail():
        job.process = process
        raise RuntimeError("stream failed")

    with patch.object(job, "_run_ytdlp_download", side_effect=fail), \
         patch.object(job, "stop") as stop:
        job.run()
    stop.assert_called_once()
    assert job.process is None
    assert errors == ["stream failed"]


def test_reap_process_kills_after_bounded_wait():
    import subprocess
    process = MagicMock()
    process.wait.side_effect = [subprocess.TimeoutExpired("child", 3), 0]
    DownloadJob._reap_process(process)
    process.kill.assert_called_once()
    assert process.wait.call_count == 2
    assert all(call.kwargs == {"timeout": 3} for call in process.wait.call_args_list)
