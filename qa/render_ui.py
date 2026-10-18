"""Offline UI captures with synthetic metadata and no startup/network work."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
from pathlib import Path
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication, QMessageBox
from ui.main_window import MainWindow
from ui.settings_dialog import SettingsDialog
from ui.download_item import DownloadItemWidget
from ui.styles import get_stylesheet

class Config:
    def __init__(self, path): self.path = path
    def get(self, key, default=None): return self.path if key == 'download_path' else default

app = QApplication([])
app.setStyleSheet(get_stylesheet())
output = Path(__file__).parent
with tempfile.TemporaryDirectory() as folder, patch('ui.main_window.QTimer.singleShot'):
    window = MainWindow(Config(folder))
    window.show()
    app.processEvents()
    window.grab().save(str(output / 'empty.png'))
    window.batch_mode_radio.setChecked(True)
    app.processEvents()
    window.grab().save(str(output / 'batch.png'))
    window.single_mode_radio.setChecked(True)
    window._display_metadata({'id': '123', 'title': '주말 방송 하이라이트', 'channel_name': 'ClipCatcher', 'duration': 3600, 'is_downloadable': True, 'resolutions': [{'label': '1080p', 'url': 'https://example.com/video'}]})
    app.processEvents()
    window.grab().save(str(output / 'video.png'))
    for name in ['active', 'completed', 'error']:
        item = DownloadItemWidget('preview', '주말 방송 하이라이트 · 테스트 영상')
        item.resize(370, 190)
        if name == 'active': item.update_progress(42, 2100000, 130)
        elif name == 'completed': item.set_completed('/tmp/example.mp4')
        else: item.set_error('연결이 끊겼습니다. 네트워크 상태를 확인해 주세요.')
        item.show()
        app.processEvents()
        item.grab().save(str(output / f'{name}.png'))
        item.close()
    dialog = SettingsDialog(Config(folder), window)
    dialog.show()
    app.processEvents()
    dialog.grab().save(str(output / 'settings.png'))
    dialog.reject()
    error = QMessageBox(QMessageBox.Icon.Warning, "다운로드 오류", "연결이 끊겼습니다. 네트워크 상태를 확인해 주세요.", parent=window)
    error.show()
    app.processEvents()
    error.grab().save(str(output / 'error-dialog.png'))
    error.accept()
    menu = window.menuBar().actions()[0].menu()
    menu.popup(window.mapToGlobal(window.rect().topLeft()))
    app.processEvents()
    menu.grab().save(str(output / 'menu.png'))
    menu.close()
    window.fetch_button.setFocus()
    app.processEvents()
    window.grab().save(str(output / 'keyboard-focus.png'))
    window.resize(1000, 750)
    window.time_range_widget.radio_partial.setChecked(True)
    app.processEvents()
    window.grab().save(str(output / 'minimum-range.png'))
    window.close()
