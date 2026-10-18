"""Offline checks for readable status, theme contrast, and preserved controls."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from ui.download_item import DownloadItemWidget
from ui.styles import COLORS, get_stylesheet

_app = QApplication.instance() or QApplication([])

class Config:
    def __init__(self, path): self.path = path
    def get(self, key, default=None): return self.path if key == 'download_path' else default

def luminance(hex_color):
    values = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    values = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
    return sum(v * weight for v, weight in zip(values, (.2126, .7152, .0722)))

def contrast(a, b):
    light, dark = sorted((luminance(a), luminance(b)), reverse=True)
    return (light + .05) / (dark + .05)

def test_theme_text_contrast():
    for key in ('text', 'text_secondary', 'success', 'error', 'warning'):
        assert contrast(COLORS[key], COLORS['surface']) >= 4.5
    assert contrast('#FFFFFF', COLORS['primary']) >= 4.5

def test_empty_guidance_and_input_modes_preserve_values():
    _app.setStyleSheet(get_stylesheet())
    with tempfile.TemporaryDirectory() as folder, patch('ui.main_window.QTimer.singleShot'):
        window = MainWindow(Config(folder))
        assert '링크' in window.status_indicator.text()
        assert not window.download_empty_label.isHidden()
        window.url_input.setText('https://youtu.be/example')
        for _ in range(3):
            window.batch_mode_radio.setChecked(True)
            window.single_mode_radio.setChecked(True)
        assert window.url_input.text() == 'https://youtu.be/example'
        window.active_list.addItem('test')
        window._refresh_download_center()
        assert window.download_empty_label.isHidden()
        window.active_list.clear()
        window._refresh_download_center()
        assert not window.download_empty_label.isHidden()
        window.close()

def test_download_status_and_cancel_signal():
    item = DownloadItemWidget('example', '영상')
    cancelled = []
    item.cancel_requested.connect(cancelled.append)
    assert item.status_label.wordWrap()
    item.set_error('연결을 확인해 주세요')
    assert '실패' in item.status_label.text()
    assert item.cancel_button.text() == '제거'
    item.cancel_button.click()
    assert cancelled == ['example']
    item.set_completed('/tmp/example.mp4')
    assert '저장 완료' in item.status_label.text()
    assert item.cancel_button.isHidden()
    assert not item.open_button.isHidden()
    item.close()
