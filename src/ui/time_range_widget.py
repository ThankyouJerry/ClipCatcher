from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QRadioButton, QLabel, QLineEdit, QButtonGroup, QFrame)
from PyQt6.QtCore import Qt
import re


class TimeRangeWidget(QWidget):
    """Widget for selecting download time range (full or custom range)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.duration = 0
        self._init_ui()
        
    def _init_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 8, 0, 0)
        outer_layout.setSpacing(8)

        # Section title
        title = QLabel("다운로드 범위")
        title.setStyleSheet("font-size: 13px; font-weight: bold; color: #ccc;")
        outer_layout.addWidget(title)

        # Container frame
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #2a2a3e;
                border: 1px solid #3a3a4e;
                border-radius: 8px;
            }
        """)
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(14, 12, 14, 12)
        frame_layout.setSpacing(10)

        # Radio buttons group
        self.btn_group = QButtonGroup(self)

        self.radio_full = QRadioButton("전체 다운로드")
        self.radio_full.setChecked(True)
        self.radio_full.setStyleSheet("font-size: 13px;")
        self.btn_group.addButton(self.radio_full, 0)
        frame_layout.addWidget(self.radio_full)

        self.radio_partial = QRadioButton("시간 범위 지정 다운로드")
        self.radio_partial.setStyleSheet("font-size: 13px;")
        self.btn_group.addButton(self.radio_partial, 1)
        frame_layout.addWidget(self.radio_partial)

        # ── Time input area ──────────────────────────────────
        self.input_area = QWidget()
        input_layout = QHBoxLayout(self.input_area)
        input_layout.setContentsMargins(20, 0, 0, 0)
        input_layout.setSpacing(12)

        # Start time
        self.start_label = QLabel("시작:")
        self.start_label.setFixedWidth(36)
        self.start_label.setStyleSheet("color: #aaa; font-size: 12px;")
        self.start_input = QLineEdit()
        self.start_input.setPlaceholderText("0 또는 00:00:00")
        self.start_input.setToolTip("초 단위(예: 90), HH:MM:SS, 또는 45분00초 형식")
        self.start_input.setMinimumWidth(120)

        # End time
        self.end_label = QLabel("종료:")
        self.end_label.setFixedWidth(36)
        self.end_label.setStyleSheet("color: #aaa; font-size: 12px;")
        self.end_input = QLineEdit()
        self.end_input.setPlaceholderText("영상 끝까지")
        self.end_input.setToolTip("비워두면 영상 끝까지 다운로드됩니다.")
        self.end_input.setMinimumWidth(120)

        input_layout.addWidget(self.start_label)
        input_layout.addWidget(self.start_input)
        input_layout.addSpacing(8)
        input_layout.addWidget(self.end_label)
        input_layout.addWidget(self.end_input)
        input_layout.addStretch()

        frame_layout.addWidget(self.input_area)

        # Hint
        self.hint_label = QLabel("※ 초 단위(예: 90), HH:MM:SS(예: 01:30:00), 한글 단위(예: 45분00초) 모두 입력 가능합니다.")
        self.hint_label.setStyleSheet("color: #666; font-size: 11px; padding-left: 20px;")
        frame_layout.addWidget(self.hint_label)

        outer_layout.addWidget(frame)

        # Connect signals AFTER all widgets created
        self.radio_full.toggled.connect(self._on_radio_toggled)
        self.radio_partial.toggled.connect(self._on_radio_toggled)

        # Initial state: inputs disabled (full download selected)
        self._set_inputs_enabled(False)

    def _on_radio_toggled(self):
        """Called whenever either radio button is toggled"""
        self._set_inputs_enabled(self.radio_partial.isChecked())

    def _set_inputs_enabled(self, enabled: bool):
        """Enable or disable the time input fields"""
        self.input_area.setEnabled(enabled)
        self.hint_label.setEnabled(enabled)
        
        # Visual dimming
        opacity = "color: #ccc;" if enabled else "color: #555;"
        self.start_label.setStyleSheet(f"{opacity} font-size: 12px;")
        self.end_label.setStyleSheet(f"{opacity} font-size: 12px;")

    def set_duration(self, duration_sec: float):
        """Called after video info is fetched. Resets inputs with video duration."""
        self.duration = duration_sec
        
        # Reset to full download
        self.radio_full.setChecked(True)
        self.start_input.clear()
        self.end_input.clear()
        
        if duration_sec > 0:
            self.end_input.setPlaceholderText(
                f"영상 끝 ({self._format_time(duration_sec)})"
            )
        else:
            self.end_input.setPlaceholderText("영상 끝까지")

    # ── Helpers ──────────────────────────────────────────────

    def _parse_time(self, time_str: str) -> float:
        """Parse seconds, HH:MM:SS/MM:SS, or Korean unit text like '45분00초'."""
        if not time_str or not time_str.strip():
            return -1
        
        s = time_str.strip()

        # Pure number
        if s.replace('.', '', 1).lstrip('-').isdigit():
            return float(s)

        korean_match = re.fullmatch(
            r"(?:(?P<hour>\d+(?:\.\d+)?)\s*시간)?\s*"
            r"(?:(?P<minute>\d+(?:\.\d+)?)\s*분)?\s*"
            r"(?:(?P<second>\d+(?:\.\d+)?)\s*초)?",
            s,
        )
        if korean_match and any(korean_match.groupdict().values()):
            hour = float(korean_match.group("hour") or 0)
            minute = float(korean_match.group("minute") or 0)
            second = float(korean_match.group("second") or 0)
            return hour * 3600 + minute * 60 + second

        # Colon-separated
        parts = s.split(':')
        try:
            if len(parts) == 3:
                h, m, sec = int(parts[0]), int(parts[1]), float(parts[2])
                return h * 3600 + m * 60 + sec
            elif len(parts) == 2:
                m, sec = int(parts[0]), float(parts[1])
                return m * 60 + sec
        except (ValueError, IndexError):
            pass

        raise ValueError(f"올바르지 않은 시간 형식입니다: '{time_str}'\n예) 90  또는  01:30:00")

    def _format_time(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    # ── Public API ───────────────────────────────────────────

    def get_time_range(self):
        """
        Returns None  → full download
        Returns dict  → {'start': float seconds, 'end': float|None seconds}
        Raises ValueError on bad input.
        """
        if self.radio_full.isChecked():
            return None

        start_str = self.start_input.text().strip()
        end_str   = self.end_input.text().strip()

        start_time = self._parse_time(start_str) if start_str else 0.0
        end_time   = self._parse_time(end_str)   if end_str   else None

        if start_time < 0:
            start_time = 0.0

        if end_time is not None and start_time >= end_time:
            raise ValueError("시작 시간이 종료 시간보다 크거나 같을 수 없습니다.")

        # Validate against current video duration when available.
        if self.duration and self.duration > 0:
            video_len = float(self.duration)
            if start_time >= video_len:
                raise ValueError(
                    f"시작 시간이 영상 길이를 초과했습니다.\n"
                    f"영상 길이: {self._format_time(video_len)}"
                )
            if end_time is not None and end_time > video_len:
                raise ValueError(
                    f"종료 시간이 영상 길이를 초과했습니다.\n"
                    f"영상 길이: {self._format_time(video_len)}"
                )

        return {'start': start_time, 'end': end_time}
