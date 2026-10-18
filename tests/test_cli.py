"""Offline CLI behavior and absence of desktop dependencies."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest

import cli
from core.dependency_check import ToolStatus


@pytest.mark.parametrize("text,expected", [("0", 0), ("12.5", 12.5), ("02:03", 123), ("1:02:03.5", 3723.5)])
def test_time_formats(text, expected):
    assert cli.parse_time(text) == expected


@pytest.mark.parametrize("text", ["-1", "nan", "inf", "1:60", "1.5:02", "1::2", "1:2:3:4", "nope"])
def test_invalid_times(text):
    with pytest.raises(argparse.ArgumentTypeError):
        cli.parse_time(text)


def test_invalid_range_never_fetches():
    with patch.object(cli, "fetch_metadata") as fetch, pytest.raises(SystemExit) as exc:
        cli.main(["download", "https://youtu.be/abcdefghijk", "--start", "20", "--end", "10"])
    assert exc.value.code == 2
    fetch.assert_not_called()


@pytest.mark.parametrize("url", ["http://youtu.be/abcdefghijk", "https://youtube.com.evil.test/watch?v=abcdefghijk", "file:///tmp/video"])
def test_rejects_untrusted_urls(url):
    with pytest.raises(argparse.ArgumentTypeError):
        cli.supported_url(url)


def test_info_stdout_is_json_and_excludes_signed_urls(capsys):
    def metadata(url):
        print("metadata warning")
        return {"id": "1", "title": "한글", "url": "https://secret/?token=private", "resolutions": [{"label": "720p", "url": "secret"}]}
    with patch.object(cli, "fetch_metadata", side_effect=metadata):
        assert cli.main(["info", "https://chzzk.naver.com/video/1"]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["title"] == "한글"
    assert "secret" not in captured.out
    assert "metadata warning" in captured.err


def test_missing_dependencies_report_failure_without_fetch(capsys):
    with patch("core.dependency_check.check_yt_dlp", return_value=ToolStatus("yt-dlp", None, False)), patch.object(cli, "fetch_metadata") as fetch:
        assert cli.main(["download", "https://chzzk.naver.com/video/1"]) == 1
    fetch.assert_not_called()
    assert "Missing dependencies" in capsys.readouterr().err


def test_quality_limit_and_unavailable_quality():
    metadata = {"resolutions": [{"height": 1080}, {"height": 360}, {"height": 720}]}
    assert cli.select_resolution(metadata, 800)["height"] == 720
    with pytest.raises(ValueError):
        cli.select_resolution(metadata, 100)


def test_output_stem_is_unique_safe_and_bounded(tmp_path):
    metadata = {"title": "../한글:" * 100}
    first = Path(cli.output_stem(tmp_path, metadata, {}))
    assert first.parent == tmp_path
    assert len(first.name.encode()) < 200
    assert first != Path(cli.output_stem(tmp_path, metadata, {}))


def test_download_validates_actual_output(tmp_path, capsys):
    from core.download_job import DownloadJob
    args = cli.build_parser().parse_args(["download", "https://chzzk.naver.com/video/1", "-o", str(tmp_path)])
    metadata = {"id": "1", "type": "vod", "vod_status": "ABR_HLS", "resolutions": [{"height": 720, "label": "720p"}]}
    def fake_run(job):
        output = Path(job.output_path + ".mp4")
        output.write_bytes(b"offline test fixture, not video")
        job.download_completed.emit(str(output))
    with patch.object(DownloadJob, "run", fake_run):
        assert cli.run_download(args, metadata) == 0
    assert Path(capsys.readouterr().out.strip()).is_file()
    with patch.object(DownloadJob, "run", lambda job: job.download_completed.emit(str(tmp_path / "missing"))):
        with pytest.raises(RuntimeError, match="nonempty"):
            cli.run_download(args, metadata)


def test_sigterm_cancels_and_restores_handlers(tmp_path):
    import signal
    from core.download_job import DownloadJob
    previous = signal.getsignal(signal.SIGTERM)
    args = cli.build_parser().parse_args(["download", "https://chzzk.naver.com/video/1", "-o", str(tmp_path)])
    metadata = {"id": "1", "resolutions": [{"label": "720p", "height": 720}]}
    def cancel(job):
        signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
        assert job.should_stop
    with patch.object(DownloadJob, "run", cancel):
        assert cli.run_download(args, metadata) == 130
    assert signal.getsignal(signal.SIGTERM) == previous


def test_headless_import_and_entrypoint_never_import_qt():
    # A separate interpreter blocks Qt/qasync imports even in the GUI test environment.
    src = Path(__file__).resolve().parents[1] / "src"
    code = '''
import importlib.abc, sys
class BlockQt(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, *args):
        if fullname.startswith(('PyQt6', 'qasync', 'ui.')):
            raise AssertionError('Desktop import: ' + fullname)
sys.meta_path.insert(0, BlockQt())
import core.download_job
import main
sys.argv = ['main.py', '--cli', '--help']
main.main()
'''
    result = subprocess.run([sys.executable, "-c", code], env={**os.environ, "PYTHONPATH": str(src)}, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "download" in result.stdout


def test_cli_package_fallback_is_cancellable_subprocess():
    from core.download_job import DownloadJob
    job = DownloadJob("https://youtu.be/abcdefghijk", "/tmp/unused", use_subprocess=True)
    with patch("core.download_job.resolve_yt_dlp_binary", return_value=None), patch.object(job, "_run_ytdlp_binary_download") as subprocess_download, patch.object(job, "_run_ytdlp_package_download") as package_download:
        job._run_ytdlp_download()
    subprocess_download.assert_called_once_with([sys.executable, "-m", "yt_dlp"])
    package_download.assert_not_called()


def test_linux_tool_paths_honor_absolute_xdg_only(monkeypatch, tmp_path):
    from core import app_tools
    monkeypatch.setattr(app_tools.sys, "platform", "linux")
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    assert app_tools.get_app_support_dir() == tmp_path / "data" / "ClipCatcher"
    monkeypatch.setenv("XDG_DATA_HOME", "relative-is-invalid")
    assert app_tools.get_app_support_dir() == tmp_path / "home" / ".local" / "share" / "ClipCatcher"
