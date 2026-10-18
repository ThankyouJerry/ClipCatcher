"""Keep packaged subprocess fallback independent of Qt and Python's -m flag."""
import sys
import builtins
from unittest.mock import patch
import main
from core.download_job import DownloadJob


def test_helper_dispatches_before_gui_imports(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['clipcatcher', '--run-yt-dlp', '--version'])
    original_import = builtins.__import__
    def no_gui(name, *args, **kwargs):
        assert not name.startswith(('PyQt6', 'qasync', 'ui')), name
        return original_import(name, *args, **kwargs)
    with patch('yt_dlp.main') as run, patch('builtins.__import__', side_effect=no_gui):
        assert main.main() == 0
    run.assert_called_once_with(['--version'])


def test_frozen_download_uses_helper(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    job = DownloadJob('https://youtu.be/abcdefghijk', str(tmp_path / 'result'),
                      use_subprocess=True)
    with patch('core.download_job.resolve_yt_dlp_binary', return_value=None), \
         patch.object(job, '_run_ytdlp_binary_download') as run:
        job._run_ytdlp_download()
    run.assert_called_once_with([sys.executable, '--run-yt-dlp'])
