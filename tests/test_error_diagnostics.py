from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import os
import sys
from core import dependency_check as dc
from core.error_diagnostics import sanitize_error, save_error_report


def test_older_external_does_not_shadow_bundled():
    package=SimpleNamespace(version=SimpleNamespace(__version__='2026.10.26'))
    with patch.dict(sys.modules, {'yt_dlp':package}), patch.object(dc,'get_yt_dlp_binary_candidates',return_value=['/fake/yt-dlp']), patch.object(dc.os.path,'isfile',return_value=True), patch.object(dc.os,'access',return_value=True), patch.object(dc,'_run_version',return_value=dc.ToolStatus('yt-dlp','/fake/yt-dlp',True,'2026.08.19')):
        assert dc.resolve_yt_dlp_binary() is None


def test_newer_external_still_usable():
    package=SimpleNamespace(version=SimpleNamespace(__version__='2026.10.26'))
    with patch.dict(sys.modules, {'yt_dlp':package}), patch.object(dc,'get_yt_dlp_binary_candidates',return_value=['/fake/yt-dlp']), patch.object(dc.os.path,'isfile',return_value=True), patch.object(dc.os,'access',return_value=True), patch.object(dc,'_run_version',return_value=dc.ToolStatus('yt-dlp','/fake/yt-dlp',True,'2026.11.01')):
        assert dc.resolve_yt_dlp_binary()=='/fake/yt-dlp'


def test_error_report_preserves_cause_redacts_credentials(tmp_path):
    raw="KeyError: 'sourceURL'\nHTTP 403\nhttps://user:SECRET@site.invalid/video?key=SECRET\nCookie: NID_AUT=SECRET; NID_SES=SECRET\nAuthorization: Bearer SECRET\nNID_AUT=SECRET"
    with patch('core.error_diagnostics.get_app_support_dir',return_value=tmp_path):
        first=save_error_report(raw);second=save_error_report(raw)
    assert first!=second
    text=Path(first).read_text()
    assert 'SECRET' not in text
    assert "KeyError: 'sourceURL'" in text
    assert 'HTTP 403' in text
    if os.name!='nt': assert Path(first).stat().st_mode & 0o777==0o600


def test_error_details_remain_available(qtbot=None):
    # Existing suite supplies a Qt application through conftest or individual tests.
    from PyQt6.QtWidgets import QApplication
    from ui.download_item import DownloadItemWidget
    app=QApplication.instance() or QApplication([])
    with patch('ui.download_item.save_error_report',return_value=None):
        widget=DownloadItemWidget('test','test')
        widget.set_error("KeyError: 'sourceURL' " + 'detail '*1000)
        assert not widget.error_button.isHidden()
        assert "sourceURL" in widget.error_text
        assert len(widget.status_label.text())<100
        widget.close()


def test_full_error_dialog_contains_complete_text():
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QApplication, QDialog, QPlainTextEdit
    from ui.download_item import DownloadItemWidget
    app=QApplication.instance() or QApplication([])
    with patch('ui.download_item.save_error_report',return_value=None):
        widget=DownloadItemWidget('dialog-test','test')
        message='An extractor error: ' + 'detail '*1000 + "KeyError: 'sourceURL'"
        widget.set_error(message)
        observed=[]
        def inspect_and_close():
            dialog=next(w for w in app.topLevelWidgets() if isinstance(w,QDialog))
            observed.append(dialog.findChild(QPlainTextEdit).toPlainText())
            dialog.reject()
        QTimer.singleShot(0,inspect_and_close)
        widget.error_button.click()
        assert observed==[message]
        widget.close()


def test_frozen_download_uses_bundled_subprocess_when_external_is_old():
    from core.download_job import DownloadJob
    job=DownloadJob('https://offline.invalid/test','/tmp/offline-output')
    with patch('core.download_job.resolve_yt_dlp_binary',return_value=None),patch('core.download_job.sys.frozen',True,create=True),patch.object(job,'_refresh_clip_stream_url'),patch.object(job,'_run_ytdlp_binary_download') as run:
        job._run_ytdlp_download()
    assert run.call_args.args[0]==[sys.executable,'--run-yt-dlp']
